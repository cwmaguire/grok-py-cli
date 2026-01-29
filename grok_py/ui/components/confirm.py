"""
Confirmation Dialog Component

Provides interactive confirmation dialogs for the Grok CLI interface.
"""

from typing import Optional, Callable
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.align import Align

from ...utils.logging import get_logger

logger = get_logger(__name__)


class ConfirmationDialog:
    """Rich-based confirmation dialog component."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def confirm(self, message: str, default: bool = False) -> bool:
        """Show a simple yes/no confirmation dialog."""
        try:
            result = Confirm.ask(f"[bold yellow]{message}[/bold yellow]", default=default, console=self.console)
            logger.info(f"Confirmation: {message} -> {result}")
            return result
        except KeyboardInterrupt:
            logger.info("Confirmation cancelled by user")
            return False

    def confirm_with_details(self, title: str, message: str, details: Optional[str] = None, default: bool = False) -> bool:
        """Show a detailed confirmation dialog with panel."""
        content = message
        if details:
            content += f"\n\n[dim]{details}[/dim]"

        panel = Panel(
            Text(content),
            title=f"[bold yellow]{title}[/bold yellow]",
            border_style="yellow"
        )
        self.console.print(panel)

        return self.confirm("Do you want to proceed?", default=default)

    def multi_choice(self, message: str, choices: list, default: Optional[str] = None) -> Optional[str]:
        """Show a multiple choice dialog."""
        choice_str = "/".join(choices)
        try:
            result = Prompt.ask(f"{message} ({choice_str})", choices=choices, default=default, console=self.console)
            logger.info(f"Multi-choice: {message} -> {result}")
            return result
        except KeyboardInterrupt:
            logger.info("Multi-choice cancelled by user")
            return None

    def confirm_destructive_action(self, action: str, target: str, consequences: Optional[str] = None) -> bool:
        """Show confirmation for destructive actions."""
        title = f"⚠️  Confirm {action.title()}"
        message = f"Are you sure you want to {action} [bold red]{target}[/bold red]?"

        details = None
        if consequences:
            details = f"Consequences: {consequences}"

        return self.confirm_with_details(title, message, details, default=False)

    def confirm_file_operation(self, operation: str, filepath: str, size_info: Optional[str] = None) -> bool:
        """Show confirmation for file operations."""
        title = f"File {operation.title()}"
        message = f"Operation: {operation}\nFile: [cyan]{filepath}[/cyan]"

        if size_info:
            message += f"\nSize: {size_info}"

        return self.confirm_with_details(title, message)

    def show_warning_and_confirm(self, warning: str, action: str) -> bool:
        """Show a warning and ask for confirmation."""
        warning_panel = Panel(
            Text(f"⚠️  {warning}", style="bold yellow"),
            title="[bold red]Warning[/bold red]",
            border_style="red"
        )
        self.console.print(warning_panel)

        return self.confirm(f"Do you still want to {action}?", default=False)

    def batch_confirm(self, items: list, action: str) -> tuple:
        """Confirm a batch operation on multiple items."""
        if not items:
            return True, []

        # Show summary
        summary_panel = Panel(
            Text(f"Items to {action}: {len(items)}\n" + "\n".join(f"• {item}" for item in items[:5]) +
                 ("\n... and more" if len(items) > 5 else "")),
            title=f"[bold]Batch {action.title()}[/bold]",
            border_style="blue"
        )
        self.console.print(summary_panel)

        if not self.confirm(f"Proceed with {action} on all {len(items)} items?"):
            return False, []

        # Individual confirmations if needed
        confirmed_items = []
        for item in items:
            if self.confirm(f"{action.title()} {item}?"):
                confirmed_items.append(item)

        return True, confirmed_items

    def confirm_with_preview(self, title: str, preview_content: str, action: str) -> bool:
        """Show confirmation with content preview."""
        preview_panel = Panel(
            Text(preview_content),
            title="[bold]Preview[/bold]",
            border_style="cyan"
        )
        self.console.print(preview_panel)

        return self.confirm_with_details(title, f"Do you want to {action} with this content?", default=True)

    def cancel_operation(self, reason: str = "Operation cancelled by user"):
        """Display cancellation message."""
        cancel_panel = Panel(
            Text(f"❌ {reason}", style="bold red"),
            title="[bold red]Cancelled[/bold red]",
            border_style="red"
        )
        self.console.print(cancel_panel)
        logger.info(reason)