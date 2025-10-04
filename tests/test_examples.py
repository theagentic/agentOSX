"""
Example Tests for AgentOSX Framework.

These tests demonstrate best practices for testing agents built with AgentOSX.
Use these as templates when creating tests for your own agents.
"""

import asyncio
import pytest
from typing import AsyncIterator

from agentosx import (
    BaseAgent,
    AgentBuilder,
    AgentStatus,
)
from agentosx.streaming.events import TextEvent, EventType
from agentosx.mcp.server import MCPServer
from agentosx.mcp.tools import ToolAdapter


# ===== Example 1: Simple Agent =====

class SimpleCalculatorAgent(BaseAgent):
    """Example: A simple calculator agent."""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            version="1.0.0",
            description="Performs basic calculations"
        )
    
    async def process(self, input: str, context=None) -> str:
        """Process mathematical expressions."""
        try:
            # Simple eval for demo (don't use in production!)
            result = eval(input)
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {str(e)}"


@pytest.mark.asyncio
async def test_simple_calculator_agent():
    """Example: Test a simple agent."""
    # Create and initialize agent
    agent = SimpleCalculatorAgent()
    await agent.initialize()
    await agent.start()
    
    # Test processing
    result = await agent.process("2 + 2")
    assert "Result: 4" in result
    
    # Test lifecycle
    assert agent.state.status == AgentStatus.RUNNING
    
    # Clean up
    await agent.stop()
    assert agent.state.status == AgentStatus.STOPPED


# ===== Example 2: Agent with Custom Tools =====

class WeatherAgent(BaseAgent):
    """Example: Agent with custom tools."""
    
    def __init__(self):
        super().__init__(
            name="weather",
            version="1.0.0",
            description="Provides weather information"
        )
        self.weather_data = {
            "new york": "Sunny, 72°F",
            "london": "Rainy, 58°F",
            "tokyo": "Cloudy, 65°F"
        }
    
    async def on_init(self):
        """Register tools during initialization."""
        # You can register tools here
        pass
    
    async def process(self, input: str, context=None) -> str:
        """Get weather for a city."""
        city = input.lower().strip()
        weather = self.weather_data.get(city, "Weather data not available")
        return f"Weather in {input}: {weather}"


@pytest.mark.asyncio
async def test_weather_agent_with_tools():
    """Example: Test agent with custom tools."""
    agent = WeatherAgent()
    await agent.initialize()
    await agent.start()
    
    # Test with valid city
    result = await agent.process("New York")
    assert "Sunny" in result
    assert "72°F" in result
    
    # Test with invalid city
    result = await agent.process("Unknown City")
    assert "not available" in result.lower()
    
    await agent.stop()


# ===== Example 3: Streaming Agent =====

class StreamingChatAgent(BaseAgent):
    """Example: Agent with streaming responses."""
    
    def __init__(self):
        super().__init__(
            name="streaming-chat",
            version="1.0.0",
            description="Chat agent with streaming support"
        )
    
    async def process(self, input: str, context=None) -> str:
        """Non-streaming response."""
        return f"You said: {input}"
    
    async def stream(self, input: str, context=None) -> AsyncIterator[TextEvent]:
        """Streaming response - yields tokens one by one."""
        response = f"You said: {input}. Here's a streaming response!"
        words = response.split()
        
        for word in words:
            yield TextEvent(
                text=word + " ",
                agent_id=self.name
            )
            await asyncio.sleep(0.01)  # Simulate streaming delay


@pytest.mark.asyncio
async def test_streaming_chat_agent():
    """Example: Test streaming agent."""
    agent = StreamingChatAgent()
    await agent.initialize()
    await agent.start()
    
    # Test regular processing
    result = await agent.process("Hello")
    assert "You said: Hello" in result
    
    # Test streaming
    events = []
    async for event in agent.stream("Hello"):
        events.append(event)
        assert isinstance(event, TextEvent)
        assert event.type == EventType.LLM_TOKEN
    
    # Should have received multiple events
    assert len(events) > 0
    
    # Reconstruct full message
    full_text = "".join(e.text for e in events)
    assert "You said: Hello" in full_text
    assert "streaming response" in full_text
    
    await agent.stop()


# ===== Example 4: Agent with MCP Server =====

@pytest.mark.asyncio
async def test_agent_with_mcp_server():
    """Example: Test agent exposed as MCP server."""
    agent = SimpleCalculatorAgent()
    await agent.initialize()
    
    # Convert agent to MCP server
    mcp_server = agent.to_mcp_server()
    
    # Verify server was created
    assert mcp_server is not None
    assert mcp_server.name == "calculator"
    
    # Check that agent's process method is registered as a tool
    tools = mcp_server.list_tools()
    assert len(tools) > 0
    
    # Find the agent's process tool
    process_tool = next((t for t in tools if "process" in t.name), None)
    assert process_tool is not None
    
    await agent.stop()


# ===== Example 5: Agent with State Management =====

class StatefulCounterAgent(BaseAgent):
    """Example: Agent that maintains state."""
    
    def __init__(self):
        super().__init__(
            name="counter",
            version="1.0.0",
            description="Counts interactions"
        )
    
    async def on_init(self):
        """Initialize state."""
        self.state.memory["count"] = 0
        self.state.memory["history"] = []
    
    async def process(self, input: str, context=None) -> str:
        """Process input and update state."""
        # Increment counter
        self.state.memory["count"] += 1
        
        # Store in history
        self.state.memory["history"].append(input)
        
        return f"Processed {self.state.memory['count']} messages. Latest: {input}"


@pytest.mark.asyncio
async def test_stateful_counter_agent():
    """Example: Test agent with state management."""
    agent = StatefulCounterAgent()
    await agent.initialize()
    await agent.start()
    
    # First interaction
    result1 = await agent.process("Hello")
    assert "Processed 1 messages" in result1
    assert agent.state.memory["count"] == 1
    
    # Second interaction
    result2 = await agent.process("World")
    assert "Processed 2 messages" in result2
    assert agent.state.memory["count"] == 2
    
    # Check history
    assert len(agent.state.memory["history"]) == 2
    assert "Hello" in agent.state.memory["history"]
    assert "World" in agent.state.memory["history"]
    
    await agent.stop()


# ===== Example 6: Agent Builder Pattern =====

@pytest.mark.asyncio
async def test_agent_builder_pattern():
    """Example: Test using direct agent instantiation (simpler than builder)."""
    
    # Most users will create agents by subclassing BaseAgent
    # The builder is more advanced and requires LLM configuration
    # For simple agents, direct instantiation is recommended:
    
    agent = SimpleCalculatorAgent()
    
    # Verify configuration
    assert agent.name == "calculator"
    assert agent.version == "1.0.0"
    
    # Initialize and test
    await agent.initialize()
    assert agent.state.status == AgentStatus.IDLE
    
    await agent.start()
    assert agent.state.status == AgentStatus.RUNNING
    
    # Can add MCP server after creation
    mcp_server = agent.to_mcp_server()
    assert mcp_server is not None
    
    await agent.stop()


# ===== Example 7: Testing Tool Adapter =====

@pytest.mark.asyncio
async def test_tool_adapter_registration():
    """Example: Test tool registration and execution."""
    adapter = ToolAdapter()
    
    # Register synchronous tool
    def multiply(a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b
    
    adapter.register_tool(
        name="multiply",
        description="Multiply two numbers",
        func=multiply
    )
    
    # Register async tool
    async def fetch_user(user_id: str) -> dict:
        """Fetch user data."""
        await asyncio.sleep(0.01)
        return {"id": user_id, "name": "Test User"}
    
    adapter.register_tool(
        name="fetch_user",
        description="Fetch user by ID",
        func=fetch_user
    )
    
    # Test synchronous tool
    result1 = await adapter.execute_tool("multiply", {"a": 3, "b": 4})
    assert result1 == 12
    
    # Test async tool
    result2 = await adapter.execute_tool("fetch_user", {"user_id": "123"})
    assert result2["id"] == "123"
    assert result2["name"] == "Test User"
    
    # List tools
    tools = adapter.list_tools()
    assert len(tools) == 2
    assert any(t.name == "multiply" for t in tools)
    assert any(t.name == "fetch_user" for t in tools)


# ===== Example 8: Testing Error Handling =====

class ErrorProneAgent(BaseAgent):
    """Example: Agent that demonstrates error handling."""
    
    def __init__(self):
        super().__init__(
            name="error-prone",
            version="1.0.0",
            description="Demonstrates error handling"
        )
    
    async def process(self, input: str, context=None) -> str:
        """Process with error handling."""
        if input == "error":
            raise ValueError("Intentional error for testing")
        return f"Success: {input}"


@pytest.mark.asyncio
async def test_agent_error_handling():
    """Example: Test agent error handling."""
    agent = ErrorProneAgent()
    await agent.initialize()
    await agent.start()
    
    # Test successful processing
    result = await agent.process("hello")
    assert "Success: hello" in result
    
    # Test error condition
    with pytest.raises(ValueError, match="Intentional error"):
        await agent.process("error")
    
    # Agent should still be running after error
    assert agent.state.status == AgentStatus.RUNNING
    
    await agent.stop()


# ===== Example 9: Testing Context Passing =====

@pytest.mark.asyncio
async def test_agent_context_usage():
    """Example: Test passing context to agents."""
    
    class ContextAwareAgent(BaseAgent):
        def __init__(self):
            super().__init__(name="context-aware", version="1.0.0")
        
        async def process(self, input: str, context=None) -> str:
            if context:
                session = context.get("session_id", "unknown")
                user = context.get("user_id", "unknown")
                return f"Input: {input}, Session: {session}, User: {user}"
            return f"Input: {input}, No context"
    
    agent = ContextAwareAgent()
    await agent.initialize()
    await agent.start()
    
    # Test without context
    result1 = await agent.process("test")
    assert "No context" in result1
    
    # Test with context
    context = {
        "session_id": "session-123",
        "user_id": "user-456"
    }
    result2 = await agent.process("test", context)
    assert "session-123" in result2
    assert "user-456" in result2
    
    await agent.stop()


# ===== Example 10: Performance Testing =====

@pytest.mark.asyncio
async def test_agent_performance():
    """Example: Test agent performance."""
    agent = SimpleCalculatorAgent()
    await agent.initialize()
    await agent.start()
    
    import time
    
    # Test processing speed
    start_time = time.time()
    
    # Process multiple requests
    tasks = [agent.process(f"{i} + {i}") for i in range(100)]
    results = await asyncio.gather(*tasks)
    
    elapsed_time = time.time() - start_time
    
    # Verify all results
    assert len(results) == 100
    assert all("Result:" in r for r in results)
    
    # Check performance (should be fast)
    assert elapsed_time < 1.0  # Should complete in less than 1 second
    
    print(f"Processed 100 requests in {elapsed_time:.2f} seconds")
    print(f"Average: {elapsed_time/100*1000:.2f}ms per request")
    
    await agent.stop()
