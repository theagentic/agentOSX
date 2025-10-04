# AgentOSX API Reference

Complete API documentation for AgentOSX v1.0.0

## Table of Contents

1. [Core Agent API](#core-agent-api)
2. [MCP Integration](#mcp-integration)
3. [SDK Builder](#sdk-builder)
4. [Streaming](#streaming)
5. [Tools](#tools)
6. [Lifecycle & State](#lifecycle--state)

---

## Core Agent API

### BaseAgent

Base class for all agents.

```python
from agentosx import BaseAgent, AgentStatus, ExecutionContext

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name: str,           # Agent name
            version: str,        # Version string
            description: str     # Description
        )
```

#### Methods

##### `async initialize() -> None`
Initialize the agent. Transitions to INITIALIZING state and calls `on_init()` hook.

```python
await agent.initialize()
```

##### `async start() -> None`
Start the agent. Transitions to RUNNING state and calls `on_start()` hook.

```python
await agent.start()
```

##### `async stop() -> None`
Stop the agent. Transitions to STOPPED state and calls `on_stop()` hook.

```python
await agent.stop()
```

##### `async process(input: str, context: ExecutionContext = None) -> str`
Process input and return response. **Must be implemented by subclasses.**

```python
result = await agent.process("Hello", context)
```

##### `async stream(input: str, context: ExecutionContext = None) -> AsyncIterator[StreamEvent]`
Stream response as events. Override for streaming support.

```python
async for event in agent.stream("Hello"):
    print(event.data)
```

##### `to_mcp_server() -> MCPServer`
Convert agent to MCP server.

```python
mcp_server = agent.to_mcp_server()
```

##### `register_mcp_tool(name: str, func: Callable, description: str, schema: dict = None) -> None`
Register a tool on the agent's MCP server.

```python
agent.register_mcp_tool("search", search_func, "Search the web")
```

#### Lifecycle Hooks

Override these methods to customize behavior:

```python
async def on_init(self):
    """Called after initialization."""
    pass

async def on_start(self):
    """Called when agent starts."""
    pass

async def on_stop(self):
    """Called before agent stops."""
    pass

async def on_message(self, message: str):
    """Called on each message."""
    pass

async def on_tool_call(self, tool_name: str, arguments: dict):
    """Called before tool execution."""
    pass

async def on_tool_result(self, tool_name: str, result: Any):
    """Called after tool execution."""
    pass

async def on_error(self, error: Exception):
    """Called on errors."""
    pass
```

#### State Management

```python
# Get current state
state: AgentState = agent.get_state()

# Update state
agent.update_state(
    context={"key": "value"},
    metadata={"meta": "data"}
)

# Set execution context
context = ExecutionContext(
    input="Hello",
    session_id="session-123",
    user_id="user-456"
)
agent.set_context(context)

# Get execution context
context = agent.get_context()
```

#### Properties

```python
agent.name          # str: Agent name
agent.version       # str: Agent version
agent.description   # str: Agent description
agent.status        # AgentStatus: Current status
```

### AgentStatus

Enum of agent states:

```python
from agentosx import AgentStatus

AgentStatus.IDLE          # Not started
AgentStatus.INITIALIZING  # Being initialized
AgentStatus.RUNNING       # Active
AgentStatus.PAUSED        # Paused
AgentStatus.STOPPED       # Stopped
AgentStatus.ERROR         # Error state
```

### ExecutionContext

Context for agent execution:

```python
from agentosx import ExecutionContext

context = ExecutionContext(
    input: str,                    # Input text
    session_id: str,               # Session ID
    user_id: Optional[str] = None, # User ID
    metadata: Dict = {}            # Metadata
)
```

### AgentLoader

Load agents from YAML manifests:

```python
from agentosx import AgentLoader

loader = AgentLoader()

# Load from file
agent = loader.load_from_file("agent.yaml")

# Load from dict
config = {...}
agent = loader.load_from_dict(config)
```

---

## MCP Integration

### MCPServer

Expose agent capabilities via MCP protocol:

```python
from agentosx.mcp import MCPServer

server = MCPServer(
    name: str,                    # Server name
    version: str = "1.0.0"        # MCP version
)
```

#### Methods

##### `register_tool(name: str, description: str, func: Callable, input_schema: dict = None) -> None`
Register a tool.

```python
server.register_tool(
    name="search",
    description="Search the web",
    func=search_function,
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        }
    }
)
```

##### `register_resource(uri: str, name: str, description: str, reader: Callable) -> None`
Register a resource.

```python
server.register_resource(
    uri="agent://status",
    name="Status",
    description="Agent status",
    reader=lambda: {"status": "ok"}
)
```

##### `register_prompt(name: str, description: str, template: str, arguments: List[dict] = None) -> None`
Register a prompt template.

```python
server.register_prompt(
    name="greeting",
    description="Greeting prompt",
    template="Hello {{name}}!",
    arguments=[{"name": "name", "type": "string"}]
)
```

##### `async start(transport: Transport) -> None`
Start MCP server with transport.

```python
from agentosx.mcp.transport import StdioTransport

transport = StdioTransport()
await server.start(transport)
```

### MCPClient

Connect to external MCP servers:

```python
from agentosx.mcp import MCPClient

client = MCPClient(name: str = "client")
```

#### Methods

##### `async connect(transport: Transport, auto_discover: bool = True) -> None`
Connect to MCP server.

```python
transport = StdioTransport()
await client.connect(transport, auto_discover=True)
```

##### `async discover_tools() -> List[ToolDefinition]`
Discover available tools.

```python
tools = await client.discover_tools()
```

##### `async call_tool(name: str, arguments: dict) -> Any`
Call a tool.

```python
result = await client.call_tool("search", {"query": "AI"})
```

##### `async discover_resources() -> List[ResourceDefinition]`
Discover resources.

```python
resources = await client.discover_resources()
```

##### `async read_resource(uri: str) -> Any`
Read resource content.

```python
content = await client.read_resource("agent://status")
```

### Transports

#### StdioTransport

STDIO (newline-delimited JSON):

```python
from agentosx.mcp.transport import StdioTransport

transport = StdioTransport()
```

#### SSETransport

Server-Sent Events:

```python
from agentosx.mcp.transport import SSETransport

transport = SSETransport(
    url: str,                 # Server URL
    keepalive_interval: int = 30  # Keepalive interval
)
```

#### WebSocketTransport

WebSocket:

```python
from agentosx.mcp.transport import WebSocketTransport

transport = WebSocketTransport(
    url: str,                 # WebSocket URL
    reconnect: bool = True    # Auto-reconnect
)
```

---

## SDK Builder

### AgentBuilder

Fluent API for building agents:

```python
from agentosx import AgentBuilder

builder = AgentBuilder()
```

#### Methods

All methods return `self` for chaining.

##### `name(name: str) -> AgentBuilder`
Set agent name.

```python
builder.name("my-agent")
```

##### `version(version: str) -> AgentBuilder`
Set agent version.

```python
builder.version("1.0.0")
```

##### `description(description: str) -> AgentBuilder`
Set agent description.

```python
builder.description("My custom agent")
```

##### `llm(provider: str, model: str, **kwargs) -> AgentBuilder`
Configure LLM.

```python
builder.llm(
    "anthropic",
    "claude-3-sonnet",
    temperature=0.7,
    max_tokens=2000
)
```

##### `tool(name: str, func: Callable, description: str = None, schema: dict = None) -> AgentBuilder`
Add a tool.

```python
builder.tool("search", search_func, "Search the web")
```

##### `mcp_server(transport: str = "stdio", port: int = None, **capabilities) -> AgentBuilder`
Enable MCP server.

```python
builder.mcp_server(transport="stdio")
```

##### `system_prompt(prompt: str) -> AgentBuilder`
Set system prompt.

```python
builder.system_prompt("You are a helpful assistant.")
```

##### `metadata(key: str, value: Any) -> AgentBuilder`
Add metadata.

```python
builder.metadata("author", "John Doe")
```

##### `build() -> BaseAgent`
Build the agent.

```python
agent = builder.build()
```

#### Complete Example

```python
agent = (
    AgentBuilder()
    .name("my-agent")
    .version("1.0.0")
    .description("My agent")
    .llm("anthropic", "claude-3-sonnet", temperature=0.7)
    .tool("search", search_func)
    .tool("analyze", analyze_func)
    .mcp_server(transport="stdio")
    .system_prompt("You are helpful.")
    .metadata("author", "Me")
    .build()
)
```

---

## Streaming

### StreamEvent

Base class for streaming events:

```python
from agentosx.streaming import StreamEvent, EventType

class StreamEvent:
    type: EventType           # Event type
    data: Dict[str, Any]      # Event data
    timestamp: float          # Unix timestamp
```

#### Methods

##### `to_sse() -> str`
Convert to SSE format.

```python
sse_data = event.to_sse()
# Returns: "event: text\ndata: {...}\n\n"
```

##### `to_vercel_format() -> dict`
Convert to Vercel AI SDK format.

```python
vercel_data = event.to_vercel_format()
```

### Event Types

```python
from agentosx.streaming import EventType

EventType.AGENT_START       # Agent started
EventType.AGENT_THINKING    # Agent thinking
EventType.AGENT_COMPLETE    # Agent completed
EventType.TOOL_CALL_START   # Tool call started
EventType.TOOL_CALL_COMPLETE # Tool call completed
EventType.LLM_TOKEN         # LLM token generated
EventType.LLM_COMPLETE      # LLM completed
EventType.ERROR             # Error occurred
EventType.TEXT              # Text chunk
EventType.DATA              # Data chunk
```

### Specific Events

#### TextEvent

Text chunk:

```python
from agentosx.streaming.events import TextEvent

event = TextEvent(
    agent_id="my-agent",
    text="Hello world"
)
```

#### ToolCallEvent

Tool call:

```python
from agentosx.streaming.events import ToolCallEvent

event = ToolCallEvent(
    agent_id="my-agent",
    tool_name="search",
    arguments={"query": "AI"}
)
```

### Handlers

#### SSEHandler

Server-Sent Events handler:

```python
from agentosx.streaming import SSEHandler

handler = SSEHandler(keepalive_interval: int = 30)

async for sse_data in handler.stream(event_generator):
    print(sse_data)
```

#### WebSocketHandler

WebSocket handler:

```python
from agentosx.streaming import WebSocketHandler

handler = WebSocketHandler()
await handler.connect(websocket)
await handler.send_event(event)
```

### Formatters

#### VercelAIFormatter

Vercel AI SDK format:

```python
from agentosx.streaming.formatters import VercelAIFormatter

formatter = VercelAIFormatter()
vercel_data = formatter.format(event)
```

#### OpenAIFormatter

OpenAI streaming format:

```python
from agentosx.streaming.formatters import OpenAIFormatter

formatter = OpenAIFormatter()
openai_data = formatter.format(event)
```

---

## Tools

### ToolAdapter

Convert Python functions to MCP tools:

```python
from agentosx.mcp.tools import ToolAdapter

adapter = ToolAdapter()
```

#### Methods

##### `register_tool(name: str, func: Callable, description: str = None, input_schema: dict = None) -> None`
Register a tool.

```python
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

adapter.register_tool("add", add, "Add two numbers")
```

##### `async execute_tool(name: str, arguments: dict) -> Any`
Execute a tool.

```python
result = await adapter.execute_tool("add", {"a": 2, "b": 3})
# Returns: 5
```

##### `get_tool_definition(name: str) -> ToolDefinition`
Get tool definition.

```python
definition = adapter.get_tool_definition("add")
```

### ToolExecutor

Execute tools with retry and timeout:

```python
from agentosx.mcp.tools import ToolExecutor

executor = ToolExecutor(
    timeout: int = 30,        # Timeout in seconds
    max_retries: int = 3,     # Max retry attempts
    backoff_factor: float = 2.0  # Exponential backoff
)
```

#### Methods

##### `async execute(func: Callable, *args, **kwargs) -> Any`
Execute with retry and timeout.

```python
result = await executor.execute(my_function, arg1, arg2)
```

##### `async execute_streaming(func: Callable, *args, **kwargs) -> AsyncIterator`
Execute streaming function.

```python
async for chunk in executor.execute_streaming(stream_func):
    print(chunk)
```

---

## Lifecycle & State

### LifecycleManager

Manage agent lifecycle:

```python
from agentosx.agents.lifecycle import LifecycleManager, LifecyclePhase

manager = LifecycleManager()
```

#### Methods

##### `transition_to(phase: LifecyclePhase) -> None`
Transition to new phase.

```python
manager.transition_to(LifecyclePhase.RUNNING)
```

##### `register_handler(phase: LifecyclePhase, handler: Callable) -> None`
Register phase handler.

```python
async def on_start():
    print("Starting...")

manager.register_handler(LifecyclePhase.STARTING, on_start)
```

### StateManager

Manage agent state with snapshots:

```python
from agentosx.agents.state import StateManager

manager = StateManager()
```

#### Methods

##### `snapshot() -> dict`
Create state snapshot.

```python
snapshot = manager.snapshot()
```

##### `restore(snapshot: dict) -> None`
Restore from snapshot.

```python
manager.restore(snapshot)
```

##### `rollback(steps: int = 1) -> None`
Rollback state.

```python
manager.rollback(steps=2)
```

---

## Decorators

### @agent

Mark class as agent:

```python
from agentosx.agents.decorators import agent

@agent(name="my-agent", version="1.0.0", description="My agent")
class MyAgent(BaseAgent):
    pass
```

### @tool

Mark method as tool:

```python
from agentosx.agents.decorators import tool

@tool(name="search", description="Search")
def search(self, query: str) -> str:
    return f"Results for: {query}"
```

### @hook

Register lifecycle hook:

```python
from agentosx.agents.decorators import hook

@hook("on_start")
async def startup(self):
    print("Starting...")
```

### @streaming

Mark method as streaming:

```python
from agentosx.agents.decorators import streaming

@streaming
async def generate(self, prompt: str):
    for word in prompt.split():
        yield word
```

---

## Utilities

### SDK Utilities

```python
from agentosx.sdk.utilities import (
    generate_id,
    safe_json_dumps,
    safe_json_loads,
    retry_async,
    validate_schema,
    merge_configs,
    format_duration
)

# Generate unique ID
id = generate_id(prefix="agent", length=8)

# Safe JSON operations
json_str = safe_json_dumps({"key": "value"})
data = safe_json_loads(json_str)

# Retry async function
result = await retry_async(
    async_func,
    max_attempts=3,
    delay=1.0,
    backoff=2.0
)

# Validate JSON Schema
is_valid = validate_schema(data, schema)

# Merge configs
config = merge_configs(base_config, override_config)

# Format duration
duration = format_duration(123.45)  # "2.1m"
```

---

## Error Handling

All async methods can raise exceptions. Use try/except:

```python
try:
    await agent.initialize()
    await agent.start()
    result = await agent.process("input")
except Exception as e:
    print(f"Error: {e}")
finally:
    await agent.stop()
```

---

## Type Hints

AgentOSX uses type hints throughout:

```python
from typing import AsyncIterator, Optional, Dict, Any
from agentosx import BaseAgent, StreamEvent

async def my_func(agent: BaseAgent) -> str:
    result: str = await agent.process("input")
    return result
```

---

For more examples, see the `examples/` directory and `QUICKSTART.md`.
