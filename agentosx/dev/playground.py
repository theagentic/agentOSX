"""
Interactive Playground

REPL interface for testing agents interactively.
"""

import asyncio
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown
import cmd

console = Console()


class InteractivePlayground:
    """
    Interactive playground for agent testing.
    
    Provides a REPL interface with command history and autocomplete.
    """
    
    def __init__(self, agent_path: Optional[Path] = None):
        self.agent_path = agent_path
        self.agent = None
        self.history = []
        
    async def start(self):
        """Start the interactive playground."""
        console.print(Panel(
            "[bold cyan]AgentOSX Interactive Playground[/bold cyan]\n"
            "[dim]Type 'help' for commands, 'exit' to quit[/dim]",
            border_style="cyan"
        ))
        
        # Load agent if path provided
        if self.agent_path:
            await self._load_agent(self.agent_path)
        
        # Start REPL
        await self._repl()
    
    async def _repl(self):
        """Run the REPL loop."""
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold cyan]>[/bold cyan]")
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input[1:])
                elif user_input.lower() in ["exit", "quit", "q"]:
                    break
                elif user_input.lower() == "help":
                    self._show_help()
                else:
                    # Send to agent
                    if self.agent:
                        await self._process_input(user_input)
                    else:
                        console.print("[yellow]No agent loaded. Use /load <path>[/yellow]")
                
                # Add to history
                self.history.append(user_input)
                
            except KeyboardInterrupt:
                console.print()
                if Prompt.ask("Exit playground?", choices=["y", "n"], default="n") == "y":
                    break
            except EOFError:
                break
        
        # Cleanup
        if self.agent:
            await self.agent.stop()
        
        console.print("\n[dim]Goodbye![/dim]")
    
    async def _handle_command(self, command: str):
        """Handle playground commands."""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd == "load":
            if not args:
                console.print("[red]Usage: /load <agent-path>[/red]")
                return
            
            agent_path = Path(args[0])
            await self._load_agent(agent_path)
        
        elif cmd == "reload":
            if self.agent_path:
                await self._load_agent(self.agent_path)
            else:
                console.print("[yellow]No agent to reload[/yellow]")
        
        elif cmd == "status":
            if self.agent:
                console.print(f"[green]Agent loaded: {self.agent.name}[/green]")
                console.print(f"Status: {self.agent.status.value}")
            else:
                console.print("[yellow]No agent loaded[/yellow]")
        
        elif cmd == "history":
            console.print("\n[bold]Command History:[/bold]")
            for i, item in enumerate(self.history[-10:], 1):
                console.print(f"  {i}. {item}")
        
        elif cmd == "clear":
            console.clear()
        
        else:
            console.print(f"[red]Unknown command: /{cmd}[/red]")
            self._show_help()
    
    async def _load_agent(self, agent_path: Path):
        """Load an agent."""
        try:
            # Import agent module
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "agent_module",
                agent_path / "agent.py"
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
                console.print("[red]No agent class found[/red]")
                return
            
            # Stop existing agent
            if self.agent:
                await self.agent.stop()
            
            # Create and start new agent
            self.agent = agent_class()
            await self.agent.start()
            self.agent_path = agent_path
            
            console.print(f"[green]✓ Agent loaded: {self.agent.name}[/green]")
            
        except Exception as e:
            console.print(f"[red]Failed to load agent: {e}[/red]")
    
    async def _process_input(self, user_input: str):
        """Process user input with agent."""
        try:
            console.print("\n[dim]Processing...[/dim]")
            
            result = await self.agent.process(user_input)
            
            console.print()
            console.print(Panel(
                result,
                title="[bold green]Agent Response[/bold green]",
                border_style="green"
            ))
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    def _show_help(self):
        """Show help message."""
        help_text = """
## Commands

- **help** - Show this help message
- **/load <path>** - Load an agent
- **/reload** - Reload current agent
- **/status** - Show agent status
- **/history** - Show command history
- **/clear** - Clear screen
- **exit** - Exit playground

## Usage

Type any text to send to the agent.
Use arrow keys for command history.
Use Ctrl+C to interrupt, Ctrl+D to exit.
"""
        console.print(Markdown(help_text))
