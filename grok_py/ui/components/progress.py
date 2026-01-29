"""
Progress Indicator Component

Provides progress bars and spinners for long-running operations in the Grok CLI.
"""

import asyncio
from typing import Optional, Callable
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text

from ...utils.logging import get_logger

logger = get_logger(__name__)


class ProgressIndicator:
    """Rich-based progress indicator with bars and spinners."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
            refresh_per_second=10
        )
        self.tasks: dict = {}

    def start_task(self, description: str, total: Optional[int] = None) -> str:
        """Start a new progress task."""
        task_id = self.progress.add_task(description, total=total)
        task_key = f"task_{len(self.tasks)}"
        self.tasks[task_key] = task_id
        logger.debug(f"Started progress task: {description}")
        return task_key

    def update_task(self, task_key: str, advance: int = 1, description: Optional[str] = None):
        """Update an existing progress task."""
        if task_key in self.tasks:
            task_id = self.tasks[task_key]
            if description:
                self.progress.update(task_id, advance=advance, description=description)
            else:
                self.progress.update(task_id, advance=advance)
        else:
            logger.warning(f"Task {task_key} not found")

    def complete_task(self, task_key: str):
        """Mark a task as completed."""
        if task_key in self.tasks:
            task_id = self.tasks[task_key]
            self.progress.update(task_id, completed=True)
            logger.debug(f"Completed progress task: {task_key}")
            del self.tasks[task_key]

    async def run_with_progress(self, description: str, coro, *args, **kwargs):
        """Run a coroutine with progress indication."""
        task_key = self.start_task(description)

        try:
            with self.progress:
                result = await coro(*args, **kwargs)
            self.complete_task(task_key)
            return result
        except Exception as e:
            self.complete_task(task_key)
            logger.error(f"Error in progress task: {e}")
            raise

    def show_spinner(self, message: str = "Processing..."):
        """Show a simple spinner."""
        with self.console.status(f"[bold green]{message}[/bold green]", spinner="dots"):
            pass  # Use in context manager

    async def show_spinner_async(self, message: str = "Processing...", duration: float = 1.0):
        """Show a spinner for a specific duration."""
        with self.console.status(f"[bold green]{message}[/bold green]", spinner="dots"):
            await asyncio.sleep(duration)

    def display_progress_panel(self, title: str, current: int, total: int, status: str = ""):
        """Display a progress panel."""
        percentage = (current / total) * 100 if total > 0 else 0
        progress_bar = f"[{'█' * int(percentage // 5)}{'░' * (20 - int(percentage // 5))}]"

        content = f"""
Current: {current}/{total}
Progress: {progress_bar} {percentage:.1f}%
Status: {status}
        """.strip()

        panel = Panel(
            Text(content),
            title=f"[bold]{title}[/bold]",
            border_style="blue"
        )
        self.console.print(panel)

    def reset(self):
        """Reset all progress tasks."""
        self.tasks.clear()
        logger.debug("Reset progress indicator")