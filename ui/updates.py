"""
Real-time Update Manager Module

Manages UI state, progress tracking, and live updates across the terminal interface.
Coordinates updates between different UI components and provides centralized state management.
"""

import asyncio
import time
import threading
from typing import Dict, List, Any, Optional, Callable, Union, Set
from enum import Enum
from dataclasses import dataclass, field
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.progress import Progress, TaskID
from rich.spinner import Spinner
from rich.layout import Layout

# Assuming logger is available
try:
    from ..utils.logging import get_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
else:
    logger = get_logger(__name__)


class UpdatePriority(Enum):
    """Priority levels for UI updates."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class UIState(Enum):
    """Possible UI states."""
    IDLE = "idle"
    PROCESSING = "processing"
    STREAMING = "streaming"
    ERROR = "error"
    WAITING = "waiting"


@dataclass
class UIComponent:
    """Represents a UI component that can be updated."""
    name: str
    renderable: Any
    priority: UpdatePriority = UpdatePriority.MEDIUM
    last_updated: float = 0.0
    update_count: int = 0


@dataclass
class ProgressTracker:
    """Tracks progress for long-running operations."""
    id: str
    description: str
    total: Optional[float] = None
    completed: float = 0.0
    status: str = "running"
    start_time: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RealTimeUpdateManager:
    """
    Manages real-time updates across the terminal UI.

    Provides centralized state management, progress tracking, and live updates
    for all UI components with proper prioritization and throttling.
    """

    def __init__(
        self,
        console: Console,
        live_display: Optional[Live] = None,
        update_interval: float = 0.1,
        max_fps: int = 30
    ):
        """
        Initialize the update manager.

        Args:
            console: Rich console for display
            live_display: Optional Rich Live display
            update_interval: Minimum time between updates
            max_fps: Maximum frames per second
        """
        self.console = console
        self.live_display = live_display
        self.update_interval = update_interval
        self.max_fps = max_fps

        self.components: Dict[str, UIComponent] = {}
        self.progress_trackers: Dict[str, ProgressTracker] = {}
        self.current_state = UIState.IDLE
        self.state_listeners: Set[Callable[[UIState, UIState], None]] = set()

        # Update control
        self._last_update = 0.0
        self._update_lock = threading.Lock()
        self._running = True
        self._update_thread: Optional[threading.Thread] = None

        # Performance tracking
        self.update_count = 0
        self.dropped_updates = 0

        # Initialize default components
        self._init_default_components()

    def _init_default_components(self) -> None:
        """Initialize default UI components."""
        # Status bar
        self.register_component("status", Text("Ready", style="green"), UpdatePriority.HIGH)

        # Progress area
        self.register_component("progress", Text(""), UpdatePriority.MEDIUM)

        # Main content area
        self.register_component("content", Text(""), UpdatePriority.MEDIUM)

    def register_component(
        self,
        name: str,
        renderable: Any,
        priority: UpdatePriority = UpdatePriority.MEDIUM
    ) -> None:
        """
        Register a UI component for management.

        Args:
            name: Component name
            renderable: Rich renderable object
            priority: Update priority
        """
        self.components[name] = UIComponent(
            name=name,
            renderable=renderable,
            priority=priority
        )
        logger.debug(f"Registered UI component: {name}")

    def update_component(
        self,
        name: str,
        renderable: Any,
        priority: Optional[UpdatePriority] = None,
        force: bool = False
    ) -> None:
        """
        Update a UI component.

        Args:
            name: Component name
            renderable: New renderable content
            priority: Override priority (optional)
            force: Force immediate update
        """
        if name not in self.components:
            logger.warning(f"Component not registered: {name}")
            return

        component = self.components[name]
        component.renderable = renderable
        component.last_updated = time.time()
        component.update_count += 1

        if priority:
            component.priority = priority

        if force or self._should_update():
            self._trigger_update()

    def start_progress(
        self,
        id: str,
        description: str,
        total: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start tracking progress for an operation.

        Args:
            id: Progress ID
            description: Progress description
            total: Total progress units (None for indeterminate)
            metadata: Additional metadata

        Returns:
            Progress ID
        """
        tracker = ProgressTracker(
            id=id,
            description=description,
            total=total,
            metadata=metadata or {}
        )

        self.progress_trackers[id] = tracker

        # Update progress component
        self._update_progress_display()

        logger.info(f"Started progress tracking: {id}")
        return id

    def update_progress(
        self,
        id: str,
        completed: Optional[float] = None,
        status: Optional[str] = None,
        increment: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update progress for a tracked operation.

        Args:
            id: Progress ID
            completed: Absolute completion value
            status: New status string
            increment: Increment completion by this amount
            metadata: Additional metadata to merge
        """
        if id not in self.progress_trackers:
            logger.warning(f"Progress tracker not found: {id}")
            return

        tracker = self.progress_trackers[id]

        if increment is not None:
            tracker.completed += increment
        elif completed is not None:
            tracker.completed = completed

        if status:
            tracker.status = status

        if metadata:
            tracker.metadata.update(metadata)

        # Ensure bounds
        if tracker.total and tracker.completed > tracker.total:
            tracker.completed = tracker.total

        self._update_progress_display()

    def complete_progress(self, id: str, success: bool = True) -> None:
        """
        Mark progress as completed.

        Args:
            id: Progress ID
            success: Whether operation succeeded
        """
        if id not in self.progress_trackers:
            logger.warning(f"Progress tracker not found: {id}")
            return

        tracker = self.progress_trackers[id]
        tracker.status = "completed" if success else "failed"

        if tracker.total:
            tracker.completed = tracker.total

        elapsed = time.time() - tracker.start_time
        logger.info(f"Completed progress {id} in {elapsed:.2f}s")

        # Update display
        self._update_progress_display()

        # Auto-remove after a delay
        asyncio.create_task(self._delayed_remove_progress(id, 2.0))

    async def _delayed_remove_progress(self, id: str, delay: float) -> None:
        """Remove progress tracker after delay."""
        await asyncio.sleep(delay)
        self.progress_trackers.pop(id, None)
        self._update_progress_display()

    def set_ui_state(self, state: UIState) -> None:
        """
        Set the current UI state.

        Args:
            state: New UI state
        """
        old_state = self.current_state
        self.current_state = state

        # Notify listeners
        for listener in self.state_listeners:
            try:
                listener(old_state, state)
            except Exception as e:
                logger.error(f"Error in state listener: {e}")

        # Update status component
        self._update_status_display()

        logger.info(f"UI state changed: {old_state.value} -> {state.value}")

    def add_state_listener(self, listener: Callable[[UIState, UIState], None]) -> None:
        """
        Add a state change listener.

        Args:
            listener: Function called on state changes (old_state, new_state)
        """
        self.state_listeners.add(listener)

    def remove_state_listener(self, listener: Callable[[UIState, UIState], None]) -> None:
        """
        Remove a state change listener.

        Args:
            listener: Listener to remove
        """
        self.state_listeners.discard(listener)

    def _update_progress_display(self) -> None:
        """Update the progress display component."""
        if not self.progress_trackers:
            self.update_component("progress", Text(""))
            return

        # Create progress display
        progress_table = Table(show_header=True, header_style="bold magenta")
        progress_table.add_column("Task", style="cyan")
        progress_table.add_column("Progress", style="green")
        progress_table.add_column("Status", style="yellow")
        progress_table.add_column("Time", style="blue")

        for tracker in self.progress_trackers.values():
            elapsed = time.time() - tracker.start_time

            # Progress bar
            if tracker.total:
                percent = min(100.0, (tracker.completed / tracker.total) * 100)
                progress_str = f"{tracker.completed:.1f}/{tracker.total:.1f} ({percent:.1f}%)"
            else:
                progress_str = f"{tracker.completed:.1f}"

            # Time display
            time_str = f"{elapsed:.1f}s"

            progress_table.add_row(
                tracker.description,
                progress_str,
                tracker.status,
                time_str
            )

        self.update_component("progress", progress_table)

    def _update_status_display(self) -> None:
        """Update the status display component."""
        state_colors = {
            UIState.IDLE: "green",
            UIState.PROCESSING: "yellow",
            UIState.STREAMING: "cyan",
            UIState.ERROR: "red",
            UIState.WAITING: "blue"
        }

        color = state_colors.get(self.current_state, "white")
        status_text = Text(f"Status: {self.current_state.value.title()}", style=color)

        # Add spinner for active states
        if self.current_state in [UIState.PROCESSING, UIState.STREAMING]:
            spinner = Spinner("dots", text=status_text.plain)
            self.update_component("status", Columns([spinner, status_text]))
        else:
            self.update_component("status", status_text)

    def _should_update(self) -> bool:
        """
        Determine if an update should be triggered based on timing.

        Returns:
            True if update should proceed
        """
        current_time = time.time()
        time_since_last = current_time - self._last_update

        if time_since_last >= self.update_interval:
            return True

        # Check FPS limit
        fps_time = 1.0 / self.max_fps
        if time_since_last >= fps_time:
            return True

        return False

    def _trigger_update(self) -> None:
        """Trigger a UI update."""
        if not self.live_display:
            return

        try:
            # Build layout from components
            layout = self._build_layout()

            # Update live display
            self.live_display.update(layout)
            self._last_update = time.time()
            self.update_count += 1

        except Exception as e:
            logger.error(f"Error triggering UI update: {e}")
            self.dropped_updates += 1

    def _build_layout(self) -> Layout:
        """
        Build the current UI layout from registered components.

        Returns:
            Rich Layout object
        """
        layout = Layout()

        # Create main sections
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=2)
        )

        # Header: status
        if "status" in self.components:
            layout["header"].update(self.components["status"].renderable)

        # Main: content and progress
        layout["main"].split_row(
            Layout(name="content"),
            Layout(name="sidebar", size=40)
        )

        if "content" in self.components:
            layout["content"].update(self.components["content"].renderable)

        if "progress" in self.components:
            layout["sidebar"].update(self.components["progress"].renderable)

        # Footer: could be used for additional info
        layout["footer"].update(Text("Grok CLI - Real-time Updates Active", style="dim"))

        return layout

    def get_stats(self) -> Dict[str, Any]:
        """
        Get update manager statistics.

        Returns:
            Dictionary with stats
        """
        return {
            "total_updates": self.update_count,
            "dropped_updates": self.dropped_updates,
            "active_progress": len(self.progress_trackers),
            "registered_components": len(self.components),
            "current_state": self.current_state.value,
            "uptime": time.time() - getattr(self, '_start_time', time.time())
        }

    def shutdown(self) -> None:
        """Shutdown the update manager."""
        self._running = False
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=1.0)

        logger.info("Real-time update manager shutdown")