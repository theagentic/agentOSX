"""
AgentOSX Complete Example.

Demonstrates:
- Building agents with SDK
- MCP server/client integration
- Streaming responses
- Tool registration
- Lifecycle management
"""

import asyncio
import logging
from typing import AsyncIterator

from agentosx import (
    AgentBuilder,
    BaseAgent,
    ExecutionContext,
    StreamEvent,
    EventType,
)
from agentosx.mcp.transport import StdioTransport
from agentosx.streaming import SSEHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== Example 1: Simple Agent with Tools =====

async def example_simple_agent():
    """Create a simple agent with tools."""
    
    # Define some tools
    async def calculator(expression: str) -> float:
        """Evaluate a mathematical expression."""
        try:
            return float(eval(expression))
        except Exception as e:
            return f"Error: {e}"
    
    async def search(query: str) -> str:
        """Search for information (mock)."""
        return f"Search results for '{query}': [Result 1, Result 2, Result 3]"
    
    # Build agent using fluent API
    agent = (
        AgentBuilder()
        .name("demo-agent")
        .version("1.0.0")
        .description("A demonstration agent with multiple tools")
        .llm("anthropic", "claude-3-sonnet", temperature=0.7)
        .tool("calculate", calculator, "Evaluate mathematical expressions")
        .tool("search", search, "Search for information")
        .system_prompt("You are a helpful assistant with access to calculator and search tools.")
        .metadata("author", "AgentOSX Demo")
        .build()
    )
    
    # Initialize agent
    await agent.initialize()
    await agent.start()
    
    # Process some input
    context = ExecutionContext(
        input="What is 2 + 2?",
        session_id="demo-session-1"
    )
    
    result = await agent.process("What is 2 + 2?", context)
    logger.info(f"Result: {result}")
    
    await agent.stop()


# ===== Example 2: Custom Agent with Lifecycle Hooks =====

class WeatherAgent(BaseAgent):
    """Custom agent that provides weather information."""
    
    def __init__(self):
        super().__init__(
            name="weather-agent",
            version="1.0.0",
            description="Provides weather information"
        )
        self.api_connected = False
    
    async def on_init(self):
        """Initialize weather API connection."""
        logger.info("Connecting to weather API...")
        self.api_connected = True
    
    async def on_start(self):
        """Start agent."""
        logger.info(f"Weather agent started. API connected: {self.api_connected}")
    
    async def on_stop(self):
        """Stop agent."""
        logger.info("Disconnecting from weather API...")
        self.api_connected = False
    
    async def on_message(self, message: str):
        """Log incoming messages."""
        logger.info(f"Received message: {message}")
    
    async def process(self, input: str, context=None) -> str:
        """Process weather queries."""
        # In production, this would call a real weather API
        location = input.replace("weather in ", "").strip()
        return f"Weather in {location}: Sunny, 72°F, Humidity: 45%"
    
    async def stream(self, input: str, context=None) -> AsyncIterator[StreamEvent]:
        """Stream weather updates."""
        from agentosx.streaming.events import (
            AgentStartEvent,
            ThinkingEvent,
            TextEvent,
            AgentCompleteEvent
        )
        
        # Start event
        yield AgentStartEvent(
            agent_id=self.name,
            timestamp=asyncio.get_event_loop().time()
        )
        
        # Thinking event
        yield ThinkingEvent(
            agent_id=self.name,
            thought="Looking up weather data..."
        )
        
        await asyncio.sleep(0.5)  # Simulate API delay
        
        # Stream response in chunks
        response = await self.process(input, context)
        for word in response.split():
            yield TextEvent(
                agent_id=self.name,
                text=word + " "
            )
            await asyncio.sleep(0.1)
        
        # Complete event
        yield AgentCompleteEvent(
            agent_id=self.name,
            result=response
        )


async def example_custom_agent():
    """Demonstrate custom agent with lifecycle hooks."""
    
    agent = WeatherAgent()
    
    # Initialize and start
    await agent.initialize()
    await agent.start()
    
    # Process query
    result = await agent.process("weather in San Francisco")
    logger.info(f"Result: {result}")
    
    # Stream query
    logger.info("Streaming response:")
    async for event in agent.stream("weather in New York"):
        if event.type == EventType.TEXT:
            print(event.data.get("text"), end="", flush=True)
    print()
    
    # Stop agent
    await agent.stop()


# ===== Example 3: MCP Server Integration =====

async def example_mcp_server():
    """Create an agent and expose it as an MCP server."""
    
    # Define tools
    async def get_time() -> str:
        """Get current time."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async def add_numbers(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    # Build agent with MCP server enabled
    agent = (
        AgentBuilder()
        .name("mcp-demo-agent")
        .llm("anthropic", "claude-3-sonnet")
        .tool("get_time", get_time, "Get the current time")
        .tool("add", add_numbers, "Add two numbers together")
        .mcp_server(transport="stdio")
        .build()
    )
    
    await agent.initialize()
    
    # Get MCP server
    mcp_server = agent.to_mcp_server()
    
    # Register additional resources
    mcp_server.register_resource(
        uri="agent://status",
        name="Agent Status",
        description="Current agent status",
        reader=lambda: {"status": agent.status.value, "name": agent.name}
    )
    
    # Start MCP server
    transport = StdioTransport()
    logger.info("Starting MCP server on STDIO...")
    logger.info("This server can now be consumed by Claude Desktop or other MCP clients")
    
    # In production, this would run indefinitely
    # await mcp_server.start(transport)
    
    # For demo, just show configuration
    logger.info("MCP Server configured with:")
    logger.info(f"  - Tools: get_time, add")
    logger.info(f"  - Resources: agent://status")
    logger.info(f"  - Transport: STDIO")


# ===== Example 4: Streaming with SSE =====

async def example_streaming():
    """Demonstrate streaming with Server-Sent Events."""
    
    agent = WeatherAgent()
    await agent.initialize()
    await agent.start()
    
    # Create SSE handler
    sse_handler = SSEHandler()
    
    # Stream events
    logger.info("Streaming with SSE format:")
    async for event in agent.stream("weather in London"):
        sse_data = event.to_sse()
        print(sse_data)
    
    await agent.stop()


# ===== Example 5: Agent from YAML Manifest =====

async def example_yaml_agent():
    """Load agent from YAML manifest."""
    from agentosx import AgentLoader
    
    # Create a sample manifest
    manifest = """
version: "1.0"
agent:
  name: "yaml-agent"
  version: "1.0.0"
  description: "Agent loaded from YAML"
  
  llm:
    provider: "anthropic"
    model: "claude-3-sonnet"
    temperature: 0.7
    max_tokens: 2000
  
  mcp:
    enabled: true
    transport: "stdio"
    expose_tools: true
  
  metadata:
    author: "AgentOSX Demo"
    category: "demonstration"
"""
    
    # Save to file
    with open("demo_agent.yaml", "w") as f:
        f.write(manifest)
    
    # Load agent
    loader = AgentLoader()
    agent = loader.load_from_file("demo_agent.yaml")
    
    logger.info(f"Loaded agent: {agent.name} v{agent.version}")
    logger.info(f"Description: {agent.description}")
    
    await agent.initialize()
    logger.info(f"Agent status: {agent.status}")


# ===== Main Menu =====

async def main():
    """Run examples."""
    
    print("=" * 60)
    print("AgentOSX Complete Examples")
    print("=" * 60)
    print()
    print("Select an example to run:")
    print("1. Simple agent with tools")
    print("2. Custom agent with lifecycle hooks")
    print("3. MCP server integration")
    print("4. Streaming with SSE")
    print("5. Load agent from YAML manifest")
    print("6. Run all examples")
    print()
    
    choice = input("Enter choice (1-6): ").strip()
    
    examples = {
        "1": ("Simple Agent", example_simple_agent),
        "2": ("Custom Agent", example_custom_agent),
        "3": ("MCP Server", example_mcp_server),
        "4": ("Streaming", example_streaming),
        "5": ("YAML Agent", example_yaml_agent),
    }
    
    if choice == "6":
        # Run all examples
        for name, func in examples.values():
            print(f"\n{'=' * 60}")
            print(f"Running: {name}")
            print('=' * 60)
            try:
                await func()
            except Exception as e:
                logger.error(f"Error in {name}: {e}", exc_info=True)
    elif choice in examples:
        name, func = examples[choice]
        print(f"\nRunning: {name}\n")
        await func()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
