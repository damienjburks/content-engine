"""
Progress tracking and summary utilities for content publishing operations.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import colorlog


@dataclass
class OperationResult:
    """Represents the result of a publishing operation."""
    title: str
    platform: str
    action: str  # 'created', 'updated', 'skipped', 'deleted', 'failed'
    success: bool
    error_message: Optional[str] = None
    article_id: Optional[str] = None
    url: Optional[str] = None


@dataclass
class ProgressTracker:
    """Tracks progress and results of publishing operations."""
    
    console: Console = field(default_factory=Console)
    results: List[OperationResult] = field(default_factory=list)
    
    def setup_colored_logging(self) -> None:
        """Setup colorlog for colored console output."""
        # Create a colorlog formatter
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s: %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%'
        )
        
        # Get the root logger and configure it
        logger = logging.getLogger()
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create and configure handler
        handler = colorlog.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    def add_result(self, result: OperationResult) -> None:
        """Add an operation result to tracking."""
        self.results.append(result)
    
    def create_progress_context(self, description: str = "Processing"):
        """Create a rich progress context manager."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            transient=True
        )
    
    def print_summary(self) -> None:
        """Print a comprehensive summary of all operations."""
        if not self.results:
            self.console.print("[yellow]No operations were performed.[/yellow]")
            return
        
        # Categorize results
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        skipped = [r for r in successful if r.action == 'skipped']
        published = [r for r in successful if r.action in ['created', 'updated']]
        deleted = [r for r in successful if r.action == 'deleted']
        
        # Create summary statistics
        stats_table = Table(title="📊 Operation Summary", show_header=True, header_style="bold magenta")
        stats_table.add_column("Category", style="cyan", no_wrap=True)
        stats_table.add_column("Count", justify="right", style="green")
        
        stats_table.add_row("✅ Successful", str(len(successful)))
        stats_table.add_row("📝 Published/Updated", str(len(published)))
        stats_table.add_row("🗑️  Deleted", str(len(deleted)))
        stats_table.add_row("⏭️  Skipped (No Changes)", str(len(skipped)))
        stats_table.add_row("❌ Failed", str(len(failed)))
        stats_table.add_row("📋 Total Operations", str(len(self.results)))
        
        self.console.print(stats_table)
        self.console.print()
        
        # Detailed results by category
        if published:
            self._print_category_table("✅ Successfully Published/Updated", published, "green")
        
        if deleted:
            self._print_category_table("🗑️ Successfully Deleted", deleted, "blue")
        
        if skipped:
            self._print_category_table("⏭️ Skipped (No Changes Needed)", skipped, "yellow")
        
        if failed:
            self._print_category_table("❌ Failed Operations", failed, "red", show_errors=True)
        
        # Overall status
        if failed:
            status_color = "red"
            status_icon = "❌"
            status_text = f"Completed with {len(failed)} failures"
        elif skipped and not published and not deleted:
            status_color = "yellow"
            status_icon = "⏭️"
            status_text = "All articles were up to date"
        else:
            status_color = "green"
            status_icon = "✅"
            status_text = "All operations completed successfully"
        
        self.console.print(
            Panel(
                f"[{status_color}]{status_icon} {status_text}[/{status_color}]",
                title="Final Status",
                border_style=status_color
            )
        )
    
    def _print_category_table(
        self, 
        title: str, 
        results: List[OperationResult], 
        color: str,
        show_errors: bool = False
    ) -> None:
        """Print a table for a specific category of results, grouped by article."""
        table = Table(title=title, show_header=True, header_style=f"bold {color}")
        table.add_column("Article", style="white", no_wrap=False, max_width=40)
        table.add_column("Platforms", style="cyan", no_wrap=False, max_width=25)
        table.add_column("Action", style=color, no_wrap=True)
        
        if show_errors:
            table.add_column("Errors", style="red", no_wrap=False, max_width=50)
        else:
            table.add_column("Details", style="dim", no_wrap=False, max_width=35)
        
        # Group results by article title
        grouped_results = {}
        for result in results:
            if result.title not in grouped_results:
                grouped_results[result.title] = []
            grouped_results[result.title].append(result)
        
        for article_title, article_results in grouped_results.items():
            # Get platforms and actions
            platforms = []
            actions = set()
            details = []
            errors = []
            
            for result in article_results:
                platforms.append(result.platform)
                actions.add(result.action)
                
                if show_errors:
                    error_msg = result.error_message or "Unknown error"
                    if len(error_msg) > 30:
                        error_msg = error_msg[:27] + "..."
                    errors.append(f"{result.platform}: {error_msg}")
                else:
                    id_or_url = result.url or result.article_id or "-"
                    if id_or_url != "-" and len(id_or_url) > 20:
                        id_or_url = id_or_url[:17] + "..."
                    details.append(f"{result.platform}: {id_or_url}")
            
            # Format action text
            if len(actions) == 1:
                action = list(actions)[0]
                if action == 'created':
                    action_text = "📝 Created"
                elif action == 'updated':
                    action_text = "🔄 Updated"
                elif action == 'skipped':
                    action_text = "⏭️ Skipped"
                elif action == 'deleted':
                    action_text = "🗑️ Deleted"
                elif action == 'failed':
                    action_text = "❌ Failed"
                else:
                    action_text = action.title()
            else:
                # Mixed actions
                action_text = "Mixed"
            
            platforms_text = ", ".join(platforms)
            
            if show_errors:
                errors_text = "\n".join(errors)
                table.add_row(article_title, platforms_text, action_text, errors_text)
            else:
                details_text = "\n".join(details)
                table.add_row(article_title, platforms_text, action_text, details_text)
        
        self.console.print(table)
        self.console.print()
    
    def get_platform_summary(self) -> Dict[str, Dict[str, int]]:
        """Get summary statistics by platform."""
        summary = {}
        
        for result in self.results:
            platform = result.platform
            if platform not in summary:
                summary[platform] = {
                    'total': 0,
                    'successful': 0,
                    'failed': 0,
                    'skipped': 0,
                    'published': 0,
                    'deleted': 0
                }
            
            summary[platform]['total'] += 1
            
            if result.success:
                summary[platform]['successful'] += 1
                if result.action == 'skipped':
                    summary[platform]['skipped'] += 1
                elif result.action in ['created', 'updated']:
                    summary[platform]['published'] += 1
                elif result.action == 'deleted':
                    summary[platform]['deleted'] += 1
            else:
                summary[platform]['failed'] += 1
        
        return summary