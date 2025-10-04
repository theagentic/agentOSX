"""
Dev Command - Development server with hot reload
"""

import asyncio
from pathlib import Path
from typing import Optional

from agentosx.cli.utils import success, error, info, find_agent_path
from agentosx.dev.hot_reload import HotReloadServer


def start_dev_server(agent: str, watch: bool, port: int, host: str):
    """
    Start development server with hot reload.
    
    Args:
        agent: Agent name or path
        watch: Enable file watching
        port: Server port
        host: Server host
    """
    # Find agent
    agent_path = find_agent_path(agent)
    if not agent_path:
        error(f"Agent not found: {agent}")
    
    info(f"Starting development server for '{agent}'...")
    info(f"Server: http://{host}:{port}")
    if watch:
        info("Hot reload: enabled")
    
    # Start server
    try:
        server = HotReloadServer(
            agent_path=agent_path,
            host=host,
            port=port,
            watch=watch,
        )
        
        asyncio.run(server.start())
        
    except KeyboardInterrupt:
        success("Server stopped")
    except Exception as e:
        error(f"Server error: {e}")
