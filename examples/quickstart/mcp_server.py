"""
MCP Server Example

Shows how to expose an agent as an MCP server.
"""

import asyncio
from agentosx.agents.base import Agent, tool


class CalculatorAgent(Agent):
    """A calculator agent with basic math tools."""
    
    name = "calculator"
    
    @tool
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    @tool
    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b
    
    @tool
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b
    
    @tool
    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    
    async def process(self, input_text: str) -> str:
        """Process math questions."""
        # Simple response for demo
        return f"I can help with math! Try asking: 'What is 2 + 2?'"


async def main():
    """Run the calculator as an MCP server."""
    # Create agent
    agent = CalculatorAgent()
    await agent.start()
    
    # Convert to MCP server
    server = agent.to_mcp_server()
    
    print("Starting MCP server...")
    print("Tools available:")
    for tool_name in agent.tools:
        print(f"  - {tool_name}")
    
    # Run server (stdio transport for CLI)
    await server.run(transport="stdio")
    
    await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
