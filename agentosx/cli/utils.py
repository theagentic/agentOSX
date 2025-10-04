"""
CLI Utilities

Helper functions for CLI commands.
"""

import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
import yaml

console = Console()


def success(message: str):
    """Print success message."""
    console.print(f"[bold green]✓[/bold green] {message}")


def error(message: str, exit_code: int = 1):
    """Print error message and optionally exit."""
    console.print(f"[bold red]✗[/bold red] {message}", style="red")
    if exit_code:
        sys.exit(exit_code)


def warning(message: str):
    """Print warning message."""
    console.print(f"[bold yellow]⚠[/bold yellow] {message}", style="yellow")


def info(message: str):
    """Print info message."""
    console.print(f"[bold blue]ℹ[/bold blue] {message}")


def spinner(text: str):
    """Create a spinner progress."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )


def find_agent_path(agent: str) -> Optional[Path]:
    """
    Find agent directory.
    
    Searches:
    1. Direct path if exists
    2. ./agents/{agent}
    3. Current directory
    """
    # Try as direct path
    path = Path(agent)
    if path.exists():
        if path.is_dir():
            return path
        if path.suffix == ".yaml":
            return path.parent
    
    # Try in agents directory
    agents_path = Path.cwd() / "agents" / agent
    if agents_path.exists():
        return agents_path
    
    # Try current directory
    if (Path.cwd() / "agent.yaml").exists():
        return Path.cwd()
    
    return None


def load_agent_manifest(agent_path: Path) -> dict:
    """Load agent manifest from YAML."""
    manifest_path = agent_path / "agent.yaml"
    if not manifest_path.exists():
        error(f"No agent.yaml found in {agent_path}")
    
    with open(manifest_path) as f:
        return yaml.safe_load(f)


def create_table(title: str, columns: list) -> Table:
    """Create a styled table."""
    table = Table(title=title, show_header=True, header_style="bold magenta")
    for col in columns:
        table.add_column(col)
    return table


def print_code(code: str, language: str = "python"):
    """Print syntax-highlighted code."""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(syntax)


def confirm(message: str, default: bool = False) -> bool:
    """Ask for user confirmation."""
    from rich.prompt import Confirm
    return Confirm.ask(message, default=default)


def prompt(message: str, default: str = None) -> str:
    """Prompt for user input."""
    from rich.prompt import Prompt
    return Prompt.ask(message, default=default)


def print_panel(content: str, title: str, style: str = "cyan"):
    """Print content in a panel."""
    console.print(Panel(content, title=title, border_style=style))


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"


def load_config() -> dict:
    """Load .agentosx.yaml configuration."""
    config_path = Path.cwd() / ".agentosx.yaml"
    if not config_path.exists():
        return {}
    
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def save_config(config: dict):
    """Save .agentosx.yaml configuration."""
    config_path = Path.cwd() / ".agentosx.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
