# Testing Guide for AgentOSX

This guide shows you how to write effective tests for your AgentOSX agents.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Agent Testing](#basic-agent-testing)
3. [Testing Agent Lifecycle](#testing-agent-lifecycle)
4. [Testing Tools and MCP](#testing-tools-and-mcp)
5. [Testing Streaming](#testing-streaming)
6. [Testing State Management](#testing-state-management)
7. [Best Practices](#best-practices)
8. [Example Test Suite](#example-test-suite)

## Getting Started

### Prerequisites

Install testing dependencies:

```bash
pip install pytest pytest-asyncio pytest-cov
```

### Test File Structure

```
your-agent/
├── agent.py           # Your agent implementation
├── tests/
│   ├── __init__.py
│   ├── test_agent.py      # Basic agent tests
│   ├── test_tools.py      # Tool-specific tests
│   └── test_integration.py # Integration tests
└── pytest.ini         # Pytest configuration
```

### Basic pytest.ini

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    asyncio: mark test as async
    integration: mark test as integration test
    slow: mark test as slow running
```

## Basic Agent Testing

### Simple Agent Test

```python
import pytest
from agentosx import BaseAgent, AgentStatus

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="my-agent",
            version="1.0.0",
            description="My custom agent"
        )
    
    async def process(self, input: str, context=None) -> str:
        return f"Processed: {input}"

@pytest.mark.asyncio
async def test_my_agent():
    # Create agent
    agent = MyAgent()
    
    # Initialize
    await agent.initialize()
    assert agent.state.status == AgentStatus.IDLE
    
    # Start
    await agent.start()
    assert agent.state.status == AgentStatus.RUNNING
    
    # Process input
    result = await agent.process("Hello")
    assert "Processed: Hello" in result
    
    # Stop
    await agent.stop()
    assert agent.state.status == AgentStatus.STOPPED
```

## Testing Agent Lifecycle

### Test Lifecycle Hooks

```python
@pytest.mark.asyncio
async def test_lifecycle_hooks():
    class TrackedAgent(BaseAgent):
        def __init__(self):
            super().__init__(name="tracked", version="1.0.0")
            self.init_called = False
            self.start_called = False
            self.stop_called = False
        
        async def on_init(self):
            self.init_called = True
        
        async def on_start(self):
            self.start_called = True
        
        async def on_stop(self):
            self.stop_called = True
        
        async def process(self, input: str, context=None) -> str:
            return input
    
    agent = TrackedAgent()
    
    # Test initialization hook
    await agent.initialize()
    assert agent.init_called
    
    # Test start hook
    await agent.start()
    assert agent.start_called
    
    # Test stop hook
    await agent.stop()
    assert agent.stop_called
```

### Test State Transitions

```python
@pytest.mark.asyncio
async def test_state_transitions():
    agent = MyAgent()
    
    # Initial state
    assert agent.state.status == AgentStatus.IDLE
    
    # Initialize -> IDLE
    await agent.initialize()
    assert agent.state.status == AgentStatus.IDLE
    
    # Start -> RUNNING
    await agent.start()
    assert agent.state.status == AgentStatus.RUNNING
    
    # Stop -> STOPPED
    await agent.stop()
    assert agent.state.status == AgentStatus.STOPPED
```

## Testing Tools and MCP

### Test Tool Registration

```python
from agentosx.mcp.tools import ToolAdapter

@pytest.mark.asyncio
async def test_tool_registration():
    adapter = ToolAdapter()
    
    # Define a tool
    def add_numbers(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    # Register tool
    adapter.register_tool(
        name="add",
        description="Add two numbers",
        func=add_numbers
    )
    
    # Verify registration
    tools = adapter.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "add"
    
    # Test execution
    result = await adapter.execute_tool("add", {"a": 5, "b": 3})
    assert result == 8
```

### Test Async Tools

```python
@pytest.mark.asyncio
async def test_async_tool():
    adapter = ToolAdapter()
    
    # Define async tool
    async def fetch_data(url: str) -> dict:
        """Fetch data from URL."""
        import asyncio
        await asyncio.sleep(0.01)  # Simulate API call
        return {"url": url, "status": "success"}
    
    # Register and test
    adapter.register_tool(
        name="fetch",
        description="Fetch data",
        func=fetch_data
    )
    
    result = await adapter.execute_tool("fetch", {"url": "https://api.example.com"})
    assert result["status"] == "success"
```

### Test MCP Server

```python
from agentosx.mcp.server import MCPServer

@pytest.mark.asyncio
async def test_mcp_server():
    # Create agent
    agent = MyAgent()
    await agent.initialize()
    
    # Convert to MCP server
    server = agent.to_mcp_server()
    
    # Verify server
    assert server is not None
    assert server.name == "my-agent"
    
    # Check tools
    tools = server.list_tools()
    assert len(tools) > 0
```

## Testing Streaming

### Test Streaming Responses

```python
from agentosx.streaming.events import TextEvent, EventType

class StreamingAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="streaming", version="1.0.0")
    
    async def process(self, input: str, context=None) -> str:
        return f"Response: {input}"
    
    async def stream(self, input: str, context=None):
        """Stream response word by word."""
        words = ["Hello", "from", "streaming", "agent"]
        for word in words:
            yield TextEvent(text=word + " ", agent_id=self.name)
            await asyncio.sleep(0.01)

@pytest.mark.asyncio
async def test_streaming():
    agent = StreamingAgent()
    await agent.initialize()
    await agent.start()
    
    # Collect all events
    events = []
    async for event in agent.stream("test"):
        events.append(event)
    
    # Verify events
    assert len(events) == 4
    assert all(isinstance(e, TextEvent) for e in events)
    assert all(e.type == EventType.LLM_TOKEN for e in events)
    
    # Reconstruct message
    full_text = "".join(e.text for e in events)
    assert "Hello from streaming agent" in full_text
```

### Test Event Types

```python
@pytest.mark.asyncio
async def test_event_types():
    agent = StreamingAgent()
    await agent.initialize()
    await agent.start()
    
    event_types = []
    async for event in agent.stream("test"):
        event_types.append(event.type)
    
    # All should be LLM_TOKEN events
    assert all(t == EventType.LLM_TOKEN for t in event_types)
```

## Testing State Management

### Test State Persistence

```python
class StatefulAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="stateful", version="1.0.0")
    
    async def on_init(self):
        self.state.memory["counter"] = 0
        self.state.memory["history"] = []
    
    async def process(self, input: str, context=None) -> str:
        self.state.memory["counter"] += 1
        self.state.memory["history"].append(input)
        return f"Count: {self.state.memory['counter']}"

@pytest.mark.asyncio
async def test_state_management():
    agent = StatefulAgent()
    await agent.initialize()
    await agent.start()
    
    # First interaction
    result1 = await agent.process("first")
    assert "Count: 1" in result1
    
    # Second interaction
    result2 = await agent.process("second")
    assert "Count: 2" in result2
    
    # Verify state
    assert agent.state.memory["counter"] == 2
    assert len(agent.state.memory["history"]) == 2
    assert "first" in agent.state.memory["history"]
```

### Test Context Data

```python
@pytest.mark.asyncio
async def test_context_data():
    agent = MyAgent()
    await agent.initialize()
    await agent.start()
    
    # Set context
    agent.state.context = {
        "session_id": "sess-123",
        "user_id": "user-456",
        "preferences": {"theme": "dark"}
    }
    
    # Verify context
    assert agent.state.context["session_id"] == "sess-123"
    assert agent.state.context["user_id"] == "user-456"
    assert agent.state.context["preferences"]["theme"] == "dark"
```

## Best Practices

### 1. Use Fixtures for Common Setup

```python
import pytest

@pytest.fixture
async def initialized_agent():
    """Fixture that provides an initialized agent."""
    agent = MyAgent()
    await agent.initialize()
    await agent.start()
    yield agent
    await agent.stop()

@pytest.mark.asyncio
async def test_with_fixture(initialized_agent):
    result = await initialized_agent.process("test")
    assert "Processed:" in result
```

### 2. Test Error Conditions

```python
@pytest.mark.asyncio
async def test_error_handling():
    agent = MyAgent()
    await agent.initialize()
    await agent.start()
    
    # Test with invalid input
    with pytest.raises(ValueError):
        await agent.process(None)
```

### 3. Use Parametrized Tests

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("input,expected", [
    ("hello", "Processed: hello"),
    ("world", "Processed: world"),
    ("test", "Processed: test"),
])
async def test_multiple_inputs(input, expected):
    agent = MyAgent()
    await agent.initialize()
    await agent.start()
    
    result = await agent.process(input)
    assert expected in result
    
    await agent.stop()
```

### 4. Test Performance

```python
import time

@pytest.mark.asyncio
@pytest.mark.slow
async def test_performance():
    agent = MyAgent()
    await agent.initialize()
    await agent.start()
    
    start = time.time()
    
    # Process 100 requests
    tasks = [agent.process(f"test-{i}") for i in range(100)]
    await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    
    # Should complete in reasonable time
    assert elapsed < 1.0  # Less than 1 second
    
    await agent.stop()
```

### 5. Mock External Dependencies

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mocked_api():
    agent = MyAgent()
    
    # Mock external API
    with patch('my_agent.api_client.fetch') as mock_fetch:
        mock_fetch.return_value = {"data": "mocked"}
        
        await agent.initialize()
        await agent.start()
        
        result = await agent.process("test")
        
        # Verify mock was called
        mock_fetch.assert_called_once()
        
        await agent.stop()
```

### 6. Test Concurrency

```python
@pytest.mark.asyncio
async def test_concurrent_processing():
    agent = MyAgent()
    await agent.initialize()
    await agent.start()
    
    # Process multiple requests concurrently
    tasks = [
        agent.process("req-1"),
        agent.process("req-2"),
        agent.process("req-3"),
    ]
    
    results = await asyncio.gather(*tasks)
    
    # All should complete successfully
    assert len(results) == 3
    assert all("Processed:" in r for r in results)
    
    await agent.stop()
```

## Example Test Suite

Here's a complete example test suite:

```python
"""
Complete test suite example for MyAgent.
"""

import pytest
import asyncio
from agentosx import BaseAgent, AgentStatus
from agentosx.streaming.events import TextEvent

class MyAgent(BaseAgent):
    """Example agent for testing."""
    
    def __init__(self):
        super().__init__(
            name="my-agent",
            version="1.0.0",
            description="Test agent"
        )
        self.call_count = 0
    
    async def on_init(self):
        self.state.memory["initialized"] = True
    
    async def process(self, input: str, context=None) -> str:
        self.call_count += 1
        if input == "error":
            raise ValueError("Test error")
        return f"Processed: {input} (call #{self.call_count})"
    
    async def stream(self, input: str, context=None):
        words = input.split()
        for word in words:
            yield TextEvent(text=word + " ", agent_id=self.name)
            await asyncio.sleep(0.01)


class TestMyAgent:
    """Test suite for MyAgent."""
    
    @pytest.fixture
    async def agent(self):
        """Create and initialize agent."""
        agent = MyAgent()
        await agent.initialize()
        await agent.start()
        yield agent
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_initialization(self, agent):
        """Test agent initialization."""
        assert agent.name == "my-agent"
        assert agent.version == "1.0.0"
        assert agent.state.status == AgentStatus.RUNNING
        assert agent.state.memory["initialized"] is True
    
    @pytest.mark.asyncio
    async def test_processing(self, agent):
        """Test basic processing."""
        result = await agent.process("hello")
        assert "Processed: hello" in result
        assert "call #1" in result
    
    @pytest.mark.asyncio
    async def test_multiple_calls(self, agent):
        """Test multiple processing calls."""
        await agent.process("first")
        await agent.process("second")
        result = await agent.process("third")
        
        assert "call #3" in result
        assert agent.call_count == 3
    
    @pytest.mark.asyncio
    async def test_error_handling(self, agent):
        """Test error handling."""
        with pytest.raises(ValueError, match="Test error"):
            await agent.process("error")
        
        # Agent should still be running
        assert agent.state.status == AgentStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_streaming(self, agent):
        """Test streaming responses."""
        events = []
        async for event in agent.stream("hello world test"):
            events.append(event)
        
        assert len(events) == 3
        full_text = "".join(e.text for e in events)
        assert "hello world test" in full_text
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, agent):
        """Test concurrent processing."""
        tasks = [agent.process(f"req-{i}") for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert agent.call_count == 5
    
    @pytest.mark.asyncio
    async def test_lifecycle(self):
        """Test complete lifecycle."""
        agent = MyAgent()
        
        # Initial state
        assert agent.state.status == AgentStatus.IDLE
        
        # Initialize
        await agent.initialize()
        assert agent.state.status == AgentStatus.IDLE
        
        # Start
        await agent.start()
        assert agent.state.status == AgentStatus.RUNNING
        
        # Use
        result = await agent.process("test")
        assert "Processed:" in result
        
        # Stop
        await agent.stop()
        assert agent.state.status == AgentStatus.STOPPED
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=your_agent --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_agent.py
```

### Run specific test
```bash
pytest tests/test_agent.py::test_my_agent
```

### Run tests matching pattern
```bash
pytest -k "streaming"
```

### Run with verbose output
```bash
pytest -v
```

### Run async tests
```bash
pytest -v tests/test_agent.py
```

## Coverage Goals

Aim for:
- **80%+ overall coverage**
- **100% coverage** for critical paths
- All error conditions tested
- All lifecycle hooks tested
- All public methods tested

## Continuous Integration

Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: pytest --cov=your_agent --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [AgentOSX Examples](../examples/)
- [Test Examples](../tests/test_examples.py)

## Summary

**Key Testing Principles:**

1. ✅ Test all lifecycle states
2. ✅ Test both success and error cases
3. ✅ Use fixtures for common setup
4. ✅ Test async operations properly
5. ✅ Mock external dependencies
6. ✅ Test concurrency where relevant
7. ✅ Aim for high coverage
8. ✅ Keep tests focused and clear
9. ✅ Use parametrized tests for multiple inputs
10. ✅ Test performance where critical

Happy testing! 🧪
