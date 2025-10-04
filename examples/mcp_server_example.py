"""
AgentOSX Examples - MCP Server Example.

Demonstrates how to create an MCP server from an agent.
"""

import asyncio
import logging
from agentosx import BaseAgent, AgentBuilder
from agentosx.mcp.transport import StdioTransport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Example 1: Simple agent with MCP server
async def example_simple_mcp():
    """Create a simple agent and expose it as an MCP server."""
    
    # Define a tool
    async def greet(name: str) -> str:
        """Greet a user by name."""
        return f"Hello, {name}!"
    
    # Build agent with MCP server
    agent = (
        AgentBuilder()
        .name("greeter-agent")
        .description("A friendly greeting agent")
        .llm("anthropic", "claude-3-sonnet")
        .tool("greet", greet, "Greet a user by name")
        .mcp_server(transport="stdio")
        .build()
    )
    
    # Initialize agent
    await agent.initialize()
    
    # Start MCP server
    transport = StdioTransport()
    mcp_server = agent.to_mcp_server()
    
    logger.info("Starting MCP server on STDIO...")
    await mcp_server.start(transport)


# Example 2: Custom agent class with MCP
class WeatherAgent(BaseAgent):
    """Custom agent that provides weather information."""
    
    def __init__(self):
        super().__init__(
            name="weather-agent",
            version="1.0.0",
            description="Provides weather information"
        )
    
    async def process(self, input: str, context=None) -> str:
        """Process weather queries."""
        # In production, this would call a weather API
        return f"Weather for {input}: Sunny, 72°F"
    
    async def get_weather(self, location: str) -> dict:
        """Get weather for a location."""
        return {
            "location": location,
            "temperature": 72,
            "condition": "Sunny",
            "humidity": 45
        }


async def example_custom_agent():
    """Create custom agent with MCP server."""
    
    agent = WeatherAgent()
    
    # Convert to MCP server
    mcp_server = agent.to_mcp_server()
    
    # Register additional tools
    mcp_server.register_tool(
        name="get_weather",
        description="Get current weather for a location",
        func=agent.get_weather,
        input_schema={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or coordinates"
                }
            },
            "required": ["location"]
        }
    )
    
    # Initialize and start
    await agent.initialize()
    
    transport = StdioTransport()
    logger.info("Starting Weather Agent MCP server...")
    await mcp_server.start(transport)


if __name__ == "__main__":
    # Run simple example
    asyncio.run(example_simple_mcp())
    
    # Or run custom agent example:
    # asyncio.run(example_custom_agent())
