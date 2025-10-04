"""
MCP Command - MCP server management
"""

import typer
import asyncio
from pathlib import Path

from agentosx.cli.utils import success, error, info, find_agent_path, create_table

app = typer.Typer(help="MCP server commands")


@app.command("start")
def start(
    agent: str = typer.Argument(..., help="Agent name or path"),
    transport: str = typer.Option("stdio", help="Transport: stdio, sse, websocket"),
    port: int = typer.Option(8000, help="Port for SSE/WebSocket"),
):
    """
    Start MCP server for agent.
    
    Examples:
        agentosx mcp start my-agent
        agentosx mcp start my-agent --transport=sse --port=3000
    """
    # Find agent
    agent_path = find_agent_path(agent)
    if not agent_path:
        error(f"Agent not found: {agent}")
    
    info(f"Starting MCP server for '{agent}'...")
    info(f"Transport: {transport}")
    
    if transport in ["sse", "websocket"]:
        info(f"Port: {port}")
    
    try:
        asyncio.run(_start_mcp_server(agent_path, transport, port))
    except KeyboardInterrupt:
        success("MCP server stopped")
    except Exception as e:
        error(f"Server error: {e}")


async def _start_mcp_server(agent_path: Path, transport: str, port: int):
    """Start MCP server asynchronously."""
    import sys
    sys.path.insert(0, str(agent_path.parent))
    
    # Import agent
    import importlib.util
    spec = importlib.util.spec_from_file_location("agent_module", agent_path / "agent.py")
    agent_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_module)
    
    # Find agent class
    agent_class = None
    for item_name in dir(agent_module):
        item = getattr(agent_module, item_name)
        if isinstance(item, type) and hasattr(item, "to_mcp_server"):
            agent_class = item
            break
    
    if not agent_class:
        raise ValueError("No agent class found")
    
    # Create agent and MCP server
    agent = agent_class()
    await agent.start()
    
    mcp_server = agent.to_mcp_server()
    
    # Select transport
    if transport == "stdio":
        from agentosx.mcp.transport.stdio import StdioTransport
        transport_impl = StdioTransport()
    elif transport == "sse":
        from agentosx.mcp.transport.sse import SSETransport
        transport_impl = SSETransport(port=port)
    elif transport == "websocket":
        from agentosx.mcp.transport.websocket import WebSocketTransport
        transport_impl = WebSocketTransport(port=port)
    else:
        raise ValueError(f"Unknown transport: {transport}")
    
    # Start server
    success("MCP server started successfully")
    await mcp_server.start(transport_impl)


@app.command("list")
def list_servers():
    """
    List running MCP servers.
    
    Examples:
        agentosx mcp list
    """
    # TODO: Implement server registry and listing
    info("Listing MCP servers...")
    
    table = create_table("Running MCP Servers", ["Agent", "Transport", "Port", "Status"])
    # Add example row
    table.add_row("my-agent", "stdio", "-", "running")
    
    from rich.console import Console
    Console().print(table)


@app.command("stop")
def stop(
    agent: str = typer.Argument(..., help="Agent name"),
):
    """
    Stop MCP server.
    
    Examples:
        agentosx mcp stop my-agent
    """
    # TODO: Implement server stopping
    info(f"Stopping MCP server for '{agent}'...")
    success("MCP server stopped")
