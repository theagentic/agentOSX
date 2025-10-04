"""
Integration Tests for AgentOSX Phase 1.

Tests the core components:
- MCP protocol
- Agent lifecycle
- Tool system
- Streaming
- SDK builder
"""

import asyncio
import pytest
from typing import AsyncIterator

from agentosx import (
    AgentBuilder,
    BaseAgent,
    AgentStatus,
    ExecutionContext,
    StreamEvent,
    EventType,
)
from agentosx.mcp.protocol import MCPProtocol, MCPRequest, ToolDefinition
from agentosx.mcp.server import MCPServer
from agentosx.mcp.client import MCPClient
from agentosx.mcp.tools import ToolAdapter
from agentosx.streaming.events import TextEvent


# ===== Protocol Tests =====

def test_mcp_protocol_request():
    """Test MCP request serialization."""
    request = MCPRequest(
        id="test-1",
        method="tools/call",
        params={"name": "test_tool", "arguments": {"arg": "value"}}
    )
    
    serialized = MCPProtocol.serialize_message(request)
    assert "jsonrpc" in serialized
    assert serialized["jsonrpc"] == "2.0"
    assert serialized["method"] == "tools/call"
    
    # Test parsing
    parsed = MCPProtocol.parse_message(serialized)
    assert parsed.id == "test-1"
    assert parsed.method == "tools/call"


def test_tool_definition():
    """Test tool definition creation."""
    tool = ToolDefinition(
        name="test_tool",
        description="A test tool",
        input_schema={
            "type": "object",
            "properties": {
                "arg": {"type": "string"}
            }
        }
    )
    
    assert tool.name == "test_tool"
    assert "properties" in tool.input_schema


# ===== Tool Adapter Tests =====

@pytest.mark.asyncio
async def test_tool_adapter():
    """Test tool registration and execution."""
    adapter = ToolAdapter()
    
    # Register a simple tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    adapter.register_tool(
        name="add",
        func=add,
        description="Add two numbers"
    )
    
    # Execute tool
    result = await adapter.execute_tool("add", {"a": 2, "b": 3})
    assert result == 5


@pytest.mark.asyncio
async def test_async_tool():
    """Test async tool execution."""
    adapter = ToolAdapter()
    
    async def fetch_data(url: str) -> str:
        """Fetch data from URL."""
        await asyncio.sleep(0.01)  # Simulate network delay
        return f"Data from {url}"
    
    adapter.register_tool("fetch", fetch_data)
    
    result = await adapter.execute_tool("fetch", {"url": "https://example.com"})
    assert "Data from" in result


# ===== Agent Tests =====

class TestAgent(BaseAgent):
    """Test agent implementation."""
    
    def __init__(self):
        super().__init__(
            name="test-agent",
            version="1.0.0",
            description="Test agent"
        )
        self.initialized = False
        self.started = False
    
    async def on_init(self):
        self.initialized = True
    
    async def on_start(self):
        self.started = True
    
    async def process(self, input: str, context=None) -> str:
        return f"Processed: {input}"


@pytest.mark.asyncio
async def test_agent_lifecycle():
    """Test agent lifecycle transitions."""
    agent = TestAgent()
    
    # Initial state
    assert agent.status == AgentStatus.IDLE
    assert not agent.initialized
    
    # Initialize
    await agent.initialize()
    assert agent.status == AgentStatus.INITIALIZING
    assert agent.initialized
    
    # Start
    await agent.start()
    assert agent.status == AgentStatus.RUNNING
    assert agent.started
    
    # Process
    result = await agent.process("test input")
    assert result == "Processed: test input"
    
    # Stop
    await agent.stop()
    assert agent.status == AgentStatus.STOPPED


@pytest.mark.asyncio
async def test_agent_context():
    """Test agent execution context."""
    agent = TestAgent()
    await agent.initialize()
    await agent.start()
    
    # Set context
    context = ExecutionContext(
        input="test",
        session_id="session-1",
        user_id="user-1"
    )
    
    agent.set_context(context)
    retrieved = agent.get_context()
    
    assert retrieved.session_id == "session-1"
    assert retrieved.user_id == "user-1"


# ===== SDK Builder Tests =====

@pytest.mark.asyncio
async def test_agent_builder():
    """Test fluent agent builder."""
    
    def test_tool(arg: str) -> str:
        return f"Result: {arg}"
    
    agent = (
        AgentBuilder()
        .name("builder-test")
        .version("1.0.0")
        .description("Built with builder")
        .llm("anthropic", "claude-3-sonnet")
        .tool("test", test_tool, "Test tool")
        .system_prompt("Test prompt")
        .metadata("key", "value")
        .build()
    )
    
    assert agent.name == "builder-test"
    assert agent.version == "1.0.0"
    assert agent.description == "Built with builder"


def test_builder_validation():
    """Test builder validation."""
    # Missing name should raise error
    with pytest.raises(ValueError, match="name is required"):
        AgentBuilder().llm("anthropic", "claude-3-sonnet").build()
    
    # Missing LLM config should raise error
    with pytest.raises(ValueError, match="LLM configuration is required"):
        AgentBuilder().name("test").build()


# ===== Streaming Tests =====

class StreamingAgent(BaseAgent):
    """Agent with streaming support."""
    
    def __init__(self):
        super().__init__(name="streaming-agent", version="1.0.0")
    
    async def process(self, input: str, context=None) -> str:
        return f"Response: {input}"
    
    async def stream(self, input: str, context=None) -> AsyncIterator[StreamEvent]:
        """Stream response in chunks."""
        words = ["Hello", "from", "streaming", "agent"]
        for word in words:
            yield TextEvent(
                agent_id=self.name,
                text=word + " "
            )
            await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_streaming():
    """Test streaming responses."""
    agent = StreamingAgent()
    await agent.initialize()
    await agent.start()
    
    events = []
    async for event in agent.stream("test"):
        events.append(event)
    
    assert len(events) == 4
    assert all(e.type == EventType.TEXT for e in events)
    
    # Reconstruct full response
    full_text = "".join(e.data["text"] for e in events)
    assert "Hello from streaming agent" in full_text


@pytest.mark.asyncio
async def test_streaming_sse_format():
    """Test SSE format conversion."""
    agent = StreamingAgent()
    await agent.initialize()
    await agent.start()
    
    sse_events = []
    async for event in agent.stream("test"):
        sse_data = event.to_sse()
        sse_events.append(sse_data)
    
    # Check SSE format
    assert all("event:" in e for e in sse_events)
    assert all("data:" in e for e in sse_events)


# ===== MCP Server Tests =====

@pytest.mark.asyncio
async def test_mcp_server_initialization():
    """Test MCP server initialization."""
    server = MCPServer(name="test-server")
    
    # Register a tool
    def echo(message: str) -> str:
        return message
    
    server.register_tool("echo", "Echo a message", echo)
    
    # Get tool list
    tools = server._tool_adapter._tools
    assert "echo" in tools


@pytest.mark.asyncio
async def test_agent_to_mcp_server():
    """Test converting agent to MCP server."""
    agent = TestAgent()
    await agent.initialize()
    
    mcp_server = agent.to_mcp_server()
    assert mcp_server is not None
    assert isinstance(mcp_server, MCPServer)


# ===== Integration Test =====

@pytest.mark.asyncio
async def test_full_integration():
    """Test complete agent workflow."""
    
    # Create agent with tools
    def calculate(expression: str) -> str:
        try:
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"Error: {e}"
    
    agent = (
        AgentBuilder()
        .name("integration-test")
        .llm("anthropic", "claude-3-sonnet")
        .tool("calculate", calculate, "Calculate expressions")
        .build()
    )
    
    # Lifecycle
    await agent.initialize()
    await agent.start()
    
    # Process
    context = ExecutionContext(
        input="2 + 2",
        session_id="test-session"
    )
    
    result = await agent.process("Calculate 2 + 2", context)
    assert result is not None
    
    # Convert to MCP server
    mcp_server = agent.to_mcp_server()
    assert mcp_server is not None
    
    # Cleanup
    await agent.stop()


# ===== Run Tests =====

if __name__ == "__main__":
    print("Running AgentOSX Phase 1 Integration Tests")
    print("=" * 60)
    
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
