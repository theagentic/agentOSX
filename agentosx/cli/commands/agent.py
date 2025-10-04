"""
Agent Command - Agent management
"""

import typer
from pathlib import Path

from agentosx.cli.utils import success, info, create_table, find_agent_path

app = typer.Typer(help="Agent management commands")


@app.command("list")
def list_agents(
    local: bool = typer.Option(True, help="List local agents"),
    remote: bool = typer.Option(False, help="List remote agents"),
):
    """
    List agents.
    
    Examples:
        agentosx agent list
        agentosx agent list --remote
    """
    if local:
        _list_local_agents()
    
    if remote:
        _list_remote_agents()


def _list_local_agents():
    """List local agents."""
    info("Local agents:")
    
    agents_dir = Path.cwd() / "agents"
    if not agents_dir.exists():
        info("No agents directory found")
        return
    
    table = create_table("Local Agents", ["Name", "Version", "Status"])
    
    for agent_dir in agents_dir.iterdir():
        if agent_dir.is_dir() and (agent_dir / "agent.yaml").exists():
            # Load manifest
            import yaml
            with open(agent_dir / "agent.yaml") as f:
                manifest = yaml.safe_load(f)
            
            name = manifest.get("persona", {}).get("name", agent_dir.name)
            version = manifest.get("metadata", {}).get("version", "unknown")
            
            table.add_row(name, version, "ready")
    
    from rich.console import Console
    Console().print(table)


def _list_remote_agents():
    """List remote agents."""
    info("Remote agents (agentOS):")
    # TODO: Implement agentOS API integration
    info("Not yet implemented")


@app.command("create")
def create_agent(
    name: str = typer.Argument(..., help="Agent name"),
    from_template: str = typer.Option("basic", "--from", help="Template name"),
):
    """
    Create agent from template (alias for init).
    
    Examples:
        agentosx agent create my-agent
        agentosx agent create my-bot --from=twitter
    """
    from agentosx.cli.commands.init import init_agent
    init_agent(name, from_template, None)
