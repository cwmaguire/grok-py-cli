"""
Status Display Component

Provides status displays and notifications for the Grok CLI interface.
"""

from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.columns import Columns
from rich.align import Align
from datetime import datetime

from ...utils.logging import get_logger

logger = get_logger(__name__)


class StatusDisplay:
    """Rich-based status display component."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.status_items: Dict[str, Dict[str, Any]] = {}

    def set_status(self, key: str, status: str, color: str = "white", details: Optional[str] = None):
        """Set a status item."""
        self.status_items[key] = {
            "status": status,
            "color": color,
            "details": details,
            "timestamp": datetime.now()
        }
        logger.debug(f"Set status: {key} = {status}")

    def update_status(self, key: str, **kwargs):
        """Update an existing status item."""
        if key in self.status_items:
            self.status_items[key].update(kwargs)
            self.status_items[key]["timestamp"] = datetime.now()
            logger.debug(f"Updated status: {key}")
        else:
            logger.warning(f"Status key {key} not found")

    def remove_status(self, key: str):
        """Remove a status item."""
        if key in self.status_items:
            del self.status_items[key]
            logger.debug(f"Removed status: {key}")

    def display_status_table(self):
        """Display all status items in a table."""
        if not self.status_items:
            return

        table = Table(title="[bold]System Status[/bold]")
        table.add_column("Component", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="green")
        table.add_column("Last Updated", style="yellow")

        for key, info in self.status_items.items():
            status_text = f"[{info['color']}]{info['status']}[/{info['color']}]"
            details = info.get('details', '')
            timestamp = info['timestamp'].strftime('%H:%M:%S')
            table.add_row(key, status_text, details, timestamp)

        self.console.print(table)

    def display_status_panels(self):
        """Display status items as panels."""
        if not self.status_items:
            return

        panels = []
        for key, info in self.status_items.items():
            content = f"Status: [{info['color']}]{info['status']}[/{info['color']}]\n"
            if info.get('details'):
                content += f"Details: {info['details']}\n"
            content += f"Updated: {info['timestamp'].strftime('%H:%M:%S')}"

            panel = Panel(
                Text(content),
                title=f"[bold]{key}[/bold]",
                border_style=info['color']
            )
            panels.append(panel)

        self.console.print(Columns(panels, equal=True, expand=True))

    def show_notification(self, message: str, level: str = "info"):
        """Show a notification message."""
        color_map = {
            "info": "blue",
            "success": "green",
            "warning": "yellow",
            "error": "red"
        }
        color = color_map.get(level, "white")

        icon_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        icon = icon_map.get(level, "•")

        notification = Panel(
            Text(f"{icon} {message}", style=f"bold {color}"),
            title=f"[bold {color}]{level.upper()}[/bold {color}]",
            border_style=color
        )
        self.console.print(notification)
        logger.info(f"Displayed {level} notification: {message}")

    def show_system_info(self):
        """Display system information."""
        import platform
        import psutil
        import os

        try:
            system_info = f"""
OS: {platform.system()} {platform.release()}
Python: {platform.python_version()}
CPU: {psutil.cpu_percent()}%
Memory: {psutil.virtual_memory().percent}%
Disk: {psutil.disk_usage('/').percent}%
PID: {os.getpid()}
            """.strip()

            panel = Panel(
                Text(system_info),
                title="[bold]System Information[/bold]",
                border_style="cyan"
            )
            self.console.print(panel)
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")

    def clear_all_status(self):
        """Clear all status items."""
        self.status_items.clear()
        logger.debug("Cleared all status items")

    def get_status_summary(self) -> str:
        """Get a summary of all status items."""
        if not self.status_items:
            return "No status items"

        summary = []
        for key, info in self.status_items.items():
            summary.append(f"{key}: {info['status']}")

        return " | ".join(summary)