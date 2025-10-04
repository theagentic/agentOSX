# AgentOSX Architecture

This document provides a detailed overview of AgentOSX's architecture and design principles.

## Overview

AgentOSX is built on three core layers:

1. **Foundation Layer** - Core abstractions (agents, LLMs, memory, tools)
2. **Protocol Layer** - MCP integration for interoperability
3. **Orchestration Layer** - Multi-agent coordination patterns

```
┌─────────────────────────────────────────┐
│         Developer Experience            │
│  (CLI, Hot Reload, Testing, Docs)      │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│         Orchestration Layer             │
│  (Swarm, CrewAI, LangGraph Patterns)   │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│          Protocol Layer (MCP)           │
│  (Servers, Transports, Discovery)      │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│         Foundation Layer                │
│  (Agents, LLMs, Memory, Tools)         │
└─────────────────────────────────────────┘
```

## Foundation Layer

### Agents

The `Agent` class is the core abstraction:

```python
from agentosx.agents.base import Agent

class MyAgent(Agent):
    async def process(self, input_text: str) -> str:
        """Process input and return response."""
        pass
    
    async def stream(self, input_text: str):
        """Stream response chunks."""
        pass
```

Key features:
- **Lifecycle Management**: `start()`, `stop()`, `pause()`, `resume()`
- **Status Tracking**: `idle`, `thinking`, `running`, `paused`, `stopped`
- **Event System**: `@hook` decorators for lifecycle events
- **Tool Integration**: `@tool` decorators for custom tools

### LLM Router

The `LLMRouter` provides provider-agnostic LLM access:

```python
from agentosx.core.llm import LLMRouter

router = LLMRouter()
response = await router.generate("gpt-4", "Hello!")
```

Supported providers:
- **OpenAI** - GPT-4, GPT-3.5
- **Anthropic** - Claude 3 (Opus, Sonnet, Haiku)
- **Google** - Gemini Pro
- **Grok** - Grok-1
- **Ollama** - Local models
- **Together AI** - Various open models
- **OpenRouter** - 100+ models

### Memory Systems

Three memory backends:

1. **In-Memory** - Fast, ephemeral
2. **SQLite** - Persistent, embedded
3. **ChromaDB** - Vector search, semantic memory

```python
from agentosx.core.memory import Memory

memory = Memory(type="sqlite", path="./memory.db")
await memory.store("key", "value")
value = await memory.retrieve("key")
```

### Policy Engine

Controls agent behavior:

```python
from agentosx.core.policy import (
    ApprovalPolicy,
    ContentFilter,
    RateLimiter,
)

# Require approval for sensitive actions
policy = ApprovalPolicy(
    actions=["post_tweet", "send_email"]
)

# Filter inappropriate content
filter = ContentFilter(
    blocked_words=["spam", "scam"]
)

# Rate limiting
limiter = RateLimiter(
    requests_per_minute=10
)
```

## Protocol Layer (MCP)

### MCP Servers

Convert agents to MCP servers:

```python
from agentosx.mcp import MCPServer

server = agent.to_mcp_server()
await server.run(transport="stdio")
```

### Transports

Three transport modes:

1. **stdio** - Standard input/output (CLI tools)
2. **SSE** - Server-Sent Events (web apps)
3. **WebSocket** - Bidirectional (real-time apps)

### Discovery

Agents automatically expose:
- **Tools** - Available functions
- **Resources** - Data sources
- **Prompts** - Pre-defined templates

## Orchestration Layer

### Swarm Pattern

Autonomous agent handoff:

```python
from agentosx.orchestration import Swarm

swarm = Swarm()
swarm.add_agent(researcher)
swarm.add_agent(writer)

result = await swarm.process("Write about AI")
# researcher → writer (automatic handoff)
```

### CrewAI Pattern

Hierarchical coordination:

```python
from agentosx.orchestration import Crew

crew = Crew(
    agents=[researcher, writer, editor],
    tasks=[research_task, write_task, edit_task],
    process="sequential"  # or "parallel"
)

result = await crew.execute()
```

### LangGraph Pattern

State machine coordination:

```python
from agentosx.orchestration import AgentGraph

graph = AgentGraph()
graph.add_node("research", researcher)
graph.add_node("write", writer)
graph.add_edge("research", "write")

result = await graph.execute(state={"topic": "AI"})
```

## Developer Experience

### CLI

Typer-based CLI with rich formatting:

```bash
agentosx <command> [options]
```

### Hot Reload

Watchfiles-based file monitoring:

```python
from agentosx.dev import HotReloadServer

server = HotReloadServer(agent_path)
await server.start()  # Auto-reloads on file changes
```

### Testing

Pytest with async support:

```python
@pytest.mark.asyncio
async def test_agent():
    agent = MyAgent()
    result = await agent.process("test")
    assert result == "expected"
```

### Evaluation

Standardized evaluation harness:

```python
from agentosx.evaluation import EvaluationHarness

harness = EvaluationHarness(agent, metrics=[accuracy, latency])
report = await harness.evaluate(dataset)
```

## Design Principles

1. **Simplicity First** - Easy things should be easy
2. **Flexibility** - Complex things should be possible
3. **Interoperability** - MCP for cross-framework compatibility
4. **Developer Experience** - Polish in tooling and documentation
5. **Production Ready** - Testing, monitoring, deployment built-in

## Data Flow

```
User Input
    ↓
Agent.process()
    ↓
Policy Check (approvals, filters, rate limits)
    ↓
LLM Router (provider selection)
    ↓
Tool Execution (optional)
    ↓
Memory Storage (optional)
    ↓
Response
```

## Configuration

Agents are configured via YAML:

```yaml
name: my-agent
version: 1.0.0

persona:
  instructions: "System prompt"
  
llm:
  provider: openai
  model: gpt-4
  temperature: 0.7
  max_tokens: 1000
  
tools:
  - name: search
    description: "Search the web"
    
memory:
  type: sqlite
  config:
    path: ./memory.db
    
policy:
  approvals:
    - post_tweet
  content_filter:
    enabled: true
  rate_limit:
    requests_per_minute: 10
```

## Extension Points

1. **Custom LLM Providers** - Implement `LLMProvider` interface
2. **Custom Memory Stores** - Implement `MemoryStore` interface
3. **Custom Tools** - Use `@tool` decorator
4. **Custom Policies** - Implement `Policy` interface
5. **Custom Orchestration** - Compose primitives

## Performance Considerations

- **Streaming** - Use `stream()` for better UX
- **Caching** - Memory stores cache recent results
- **Async** - All I/O is async for concurrency
- **Lazy Loading** - Agents load resources on-demand

## Security

- **API Keys** - Environment variables or config files
- **Content Filtering** - Built-in policy engine
- **Rate Limiting** - Prevent abuse
- **Approval Gates** - Human-in-the-loop for sensitive actions

## Monitoring

- **Status Events** - Track agent lifecycle
- **Tool Calls** - Log all tool invocations
- **LLM Usage** - Track tokens and costs
- **Error Tracking** - Structured error reporting

## Next Steps

- [Agent Development Guide](agent-development.md)
- [MCP Integration Guide](mcp-integration.md)
- [Orchestration Patterns](orchestration.md)
- [API Reference](api-reference.md)
