"""
Playground Command - Interactive agent testing
"""

import asyncio
from pathlib import Path
from typing import Optional

from agentosx.cli.utils import success, error, info, find_agent_path
from agentosx.dev.playground import InteractivePlayground


def start_playground(agent: Optional[str], web: bool, port: int):
    """
    Start interactive playground.
    
    Args:
        agent: Agent to load
        web: Start web UI
        port: Web UI port
    """
    if web:
        info(f"Starting web playground on http://localhost:{port}...")
        # TODO: Implement web UI
        error("Web UI not yet implemented")
    else:
        info("Starting interactive playground...")
        
        # Load agent if specified
        agent_path = None
        if agent:
            agent_path = find_agent_path(agent)
            if not agent_path:
                error(f"Agent not found: {agent}")
        
        # Start REPL
        try:
            playground = InteractivePlayground(agent_path)
            asyncio.run(playground.start())
            
            success("Playground session ended")
        except KeyboardInterrupt:
            success("Playground stopped")
        except Exception as e:
            error(f"Playground error: {e}")
