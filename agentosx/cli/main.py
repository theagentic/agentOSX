"""
AgentOSX CLI - Main Entry Point

Provides developer-friendly commands for agent development, testing, and deployment.
"""

import typer
from rich.console import Console
from rich.panel import Panel
from pathlib import Path

# Import command modules
from agentosx.cli.commands import (
    init,
    dev,
    run,
    test,
    mcp,
    deploy,
    agent,
    playground,
)

# Create main app
app = typer.Typer(
    name="agentosx",
    help="🤖 AgentOSX - Production-grade multi-agent framework",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Create console for rich output
console = Console()

# Add command groups
app.add_typer(agent.app, name="agent", help="Agent management commands")
app.add_typer(mcp.app, name="mcp", help="MCP server commands")


@app.command()
def init(
    name: str = typer.Argument(..., help="Agent name"),
    template: str = typer.Option("basic", help="Template type: basic, twitter, blog, crew"),
    path: Path = typer.Option(None, help="Target directory"),
):
    """
    🚀 Create a new agent from template
    
    Examples:
        agentosx init my-agent
        agentosx init twitter-bot --template=twitter
        agentosx init research-crew --template=crew --path=./agents
    """
    init.init_agent(name, template, path)


@app.command()
def dev(
    agent: str = typer.Argument(..., help="Agent name or path"),
    watch: bool = typer.Option(True, help="Enable hot reload"),
    port: int = typer.Option(8000, help="Server port"),
    host: str = typer.Option("localhost", help="Server host"),
):
    """
    🔥 Start development server with hot reload
    
    Examples:
        agentosx dev my-agent
        agentosx dev ./agents/twitter-agent --port=3000
        agentosx dev my-agent --no-watch
    """
    dev.start_dev_server(agent, watch, port, host)


@app.command()
def run(
    agent: str = typer.Argument(..., help="Agent name or path"),
    input_text: str = typer.Option(None, "--input", "-i", help="Input text"),
    file: Path = typer.Option(None, "--file", "-f", help="Input file"),
    workflow: str = typer.Option(None, help="Workflow to execute"),
    stream: bool = typer.Option(False, help="Stream output"),
):
    """
    ▶️  Execute agent locally
    
    Examples:
        agentosx run my-agent --input="Hello world"
        agentosx run my-agent --file=input.txt --stream
        agentosx run my-agent --workflow=blog-pipeline
    """
    run.run_agent(agent, input_text, file, workflow, stream)


@app.command()
def test(
    agent: str = typer.Argument(None, help="Agent to test (all if not specified)"),
    suite: str = typer.Option("all", help="Test suite: unit, integration, e2e, all"),
    coverage: bool = typer.Option(False, help="Generate coverage report"),
    verbose: bool = typer.Option(False, "-v", help="Verbose output"),
):
    """
    🧪 Run test suites
    
    Examples:
        agentosx test
        agentosx test my-agent --suite=unit
        agentosx test --coverage -v
    """
    test.run_tests(agent, suite, coverage, verbose)


@app.command()
def deploy(
    agent: str = typer.Argument(..., help="Agent name or path"),
    env: str = typer.Option("production", help="Environment: dev, staging, production"),
    agentos: bool = typer.Option(True, help="Deploy to agentOS"),
    build: bool = typer.Option(True, help="Build before deploy"),
):
    """
    🚀 Deploy agent to production
    
    Examples:
        agentosx deploy my-agent
        agentosx deploy my-agent --env=staging
        agentosx deploy my-agent --no-agentos
    """
    deploy.deploy_agent(agent, env, agentos, build)


@app.command()
def playground(
    agent: str = typer.Option(None, help="Agent to load"),
    web: bool = typer.Option(False, help="Start web UI"),
    port: int = typer.Option(8080, help="Web UI port"),
):
    """
    🎮 Interactive agent playground
    
    Examples:
        agentosx playground
        agentosx playground --agent=my-agent
        agentosx playground --web --port=3000
    """
    playground.start_playground(agent, web, port)


@app.callback()
def callback():
    """
    AgentOSX - Production-grade multi-agent framework
    
    Build, test, and deploy agents with ease.
    """
    pass


def version_callback(value: bool):
    """Show version information."""
    if value:
        from agentosx import __version__
        console.print(Panel(
            f"[bold cyan]AgentOSX[/bold cyan] v{__version__}\n"
            "[dim]Production-grade multi-agent framework[/dim]",
            title="Version",
            border_style="cyan"
        ))
        raise typer.Exit()


@app.command()
def version():
    """Show version information"""
    version_callback(True)


if __name__ == "__main__":
    app()
