"""
Hot Reload Server

Development server with file watching and automatic reloading.
"""

import asyncio
import importlib.util
from pathlib import Path
from typing import Optional, Set
from watchfiles import awatch
from rich.console import Console

console = Console()


class HotReloadServer:
    """
    Development server with hot reload.
    
    Watches agent files and automatically reloads when changes detected.
    """
    
    def __init__(
        self,
        agent_path: Path,
        host: str = "localhost",
        port: int = 8000,
        watch: bool = True,
    ):
        self.agent_path = agent_path
        self.host = host
        self.port = port
        self.watch_enabled = watch
        
        self.agent = None
        self.mcp_server = None
        self.watched_files: Set[Path] = set()
        
    async def start(self):
        """Start the development server."""
        console.print(f"[bold cyan]AgentOSX Development Server[/bold cyan]")
        console.print(f"Agent: {self.agent_path.name}")
        console.print(f"Server: http://{self.host}:{self.port}")
        console.print()
        
        # Load agent initially
        await self._load_agent()
        
        if self.watch_enabled:
            console.print("[green]✓[/green] Hot reload enabled")
            console.print(f"[dim]Watching: {self.agent_path}[/dim]")
            console.print()
            
            # Start file watcher
            await self._watch_files()
        else:
            # Just run the server
            await self._run_server()
    
    async def _load_agent(self):
        """Load or reload the agent."""
        try:
            # Import agent module
            spec = importlib.util.spec_from_file_location(
                "agent_module",
                self.agent_path / "agent.py"
            )
            agent_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(agent_module)
            
            # Find agent class
            agent_class = None
            for item_name in dir(agent_module):
                item = getattr(agent_module, item_name)
                if isinstance(item, type) and hasattr(item, "process"):
                    agent_class = item
                    break
            
            if not agent_class:
                console.print("[red]✗[/red] No agent class found")
                return
            
            # Stop existing agent
            if self.agent:
                await self.agent.stop()
            
            # Create new agent instance
            self.agent = agent_class()
            await self.agent.start()
            
            # Create MCP server
            self.mcp_server = self.agent.to_mcp_server()
            
            console.print("[green]✓[/green] Agent loaded successfully")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to load agent: {e}")
    
    async def _watch_files(self):
        """Watch files for changes."""
        watch_paths = [self.agent_path]
        
        async for changes in awatch(*watch_paths):
            console.print()
            console.print(f"[yellow]Changes detected:[/yellow]")
            
            for change_type, path in changes:
                console.print(f"  {change_type}: {Path(path).name}")
            
            console.print("[cyan]Reloading agent...[/cyan]")
            await self._load_agent()
            console.print()
    
    async def _run_server(self):
        """Run the MCP server."""
        # TODO: Implement actual server running
        # For now, just keep running
        while True:
            await asyncio.sleep(1)
