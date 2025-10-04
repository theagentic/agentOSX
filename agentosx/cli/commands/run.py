"""
Run Command - Execute agents locally
"""

import asyncio
from pathlib import Path
from typing import Optional

from agentosx.cli.utils import success, error, info, find_agent_path, load_agent_manifest, format_duration
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
import time

console = Console()


def run_agent(agent: str, input_text: Optional[str], file: Optional[Path], workflow: Optional[str], stream: bool):
    """
    Execute agent locally.
    
    Args:
        agent: Agent name or path
        input_text: Input text
        file: Input file
        workflow: Workflow to execute
        stream: Stream output
    """
    # Find agent
    agent_path = find_agent_path(agent)
    if not agent_path:
        error(f"Agent not found: {agent}")
    
    # Get input
    if not input_text and not file:
        error("Provide input via --input or --file")
    
    if file:
        if not file.exists():
            error(f"File not found: {file}")
        input_text = file.read_text()
    
    info(f"Running agent '{agent}'...")
    if workflow:
        info(f"Workflow: {workflow}")
    
    # Load and run agent
    try:
        result = asyncio.run(_run_agent_async(agent_path, input_text, workflow, stream))
        
        # Display result
        console.print()
        console.print(Panel(
            result["output"],
            title=f"✓ Agent Output ({format_duration(result['duration'])})",
            border_style="green"
        ))
        
        success("Agent execution completed")
        
    except Exception as e:
        error(f"Execution failed: {e}")


async def _run_agent_async(agent_path: Path, input_text: str, workflow: Optional[str], stream: bool):
    """Run agent asynchronously."""
    import sys
    sys.path.insert(0, str(agent_path.parent))
    
    # Import agent
    manifest = load_agent_manifest(agent_path)
    agent_name = manifest.get("persona", {}).get("name", "Agent")
    
    # Try to import agent module
    agent_module_path = agent_path / "agent.py"
    if not agent_module_path.exists():
        raise FileNotFoundError(f"No agent.py found in {agent_path}")
    
    # Dynamic import
    import importlib.util
    spec = importlib.util.spec_from_file_location("agent_module", agent_module_path)
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
        raise ValueError("No agent class found in agent.py")
    
    # Create and run agent
    agent_instance = agent_class()
    await agent_instance.start()
    
    start_time = time.time()
    
    if stream:
        # Stream output
        console.print(f"\n[cyan]Streaming output from {agent_name}...[/cyan]\n")
        
        if hasattr(agent_instance, "stream"):
            async for event in agent_instance.stream(input_text):
                if hasattr(event, "text"):
                    console.print(event.text, end="")
            console.print()  # New line after streaming
            output = "[Streamed output shown above]"
        else:
            output = await agent_instance.process(input_text)
            console.print(output)
    else:
        # Get complete output
        output = await agent_instance.process(input_text)
    
    duration = time.time() - start_time
    
    await agent_instance.stop()
    
    return {
        "output": output,
        "duration": duration,
    }
