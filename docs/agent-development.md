# Agent Development Guide

Learn how to build powerful agents with AgentOSX.

## Agent Basics

### Minimal Agent

```python
from agentosx.agents.base import Agent

class HelloAgent(Agent):
    async def process(self, input_text: str) -> str:
        return f"Hello, {input_text}!"
```

### With Configuration

Create `agent.yaml`:

```yaml
name: hello-agent
version: 1.0.0

persona:
  instructions: |
    You are a friendly greeting agent.
    Always respond with enthusiasm!

llm:
  provider: openai
  model: gpt-4
  temperature: 0.9
```

## Adding Tools

### Simple Tool

```python
from agentosx.agents.base import Agent, tool

class CalculatorAgent(Agent):
    @tool
    def add(self, a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b
    
    @tool
    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b
```

### Async Tool

```python
import aiohttp

class WeatherAgent(Agent):
    @tool
    async def get_weather(self, city: str) -> dict:
        """Get current weather for a city."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.weather.com/{city}") as resp:
                return await resp.json()
```

### Tool with Validation

```python
from pydantic import BaseModel

class SearchQuery(BaseModel):
    query: str
    max_results: int = 10

class SearchAgent(Agent):
    @tool
    async def search(self, params: SearchQuery) -> list:
        """Search the web."""
        # Tool inputs are validated automatically
        results = await self._search_api(params.query, params.max_results)
        return results
```

## Memory Integration

### Using Memory

```python
class MemoryAgent(Agent):
    async def process(self, input_text: str) -> str:
        # Store conversation
        await self.memory.store(f"msg_{self.msg_count}", input_text)
        
        # Retrieve history
        history = await self.memory.retrieve_all()
        
        # Generate contextual response
        context = "\n".join(history[-5:])  # Last 5 messages
        response = await self.llm.generate(
            f"Context: {context}\nUser: {input_text}\nAssistant:"
        )
        
        return response
```

### Memory Configuration

```yaml
memory:
  type: sqlite
  config:
    path: ./memory.db
    table: conversations
```

Or with ChromaDB for semantic search:

```yaml
memory:
  type: chroma
  config:
    path: ./chroma_db
    collection: agent_memory
```

## Lifecycle Hooks

### Event Handlers

```python
from agentosx.agents.base import Agent, hook

class LifecycleAgent(Agent):
    @hook("start")
    async def on_start(self):
        """Called when agent starts."""
        print("Agent starting...")
        await self._load_resources()
    
    @hook("stop")
    async def on_stop(self):
        """Called when agent stops."""
        print("Agent stopping...")
        await self._cleanup()
    
    @hook("before_process")
    async def before_process(self, input_text: str):
        """Called before processing input."""
        print(f"Processing: {input_text}")
    
    @hook("after_process")
    async def after_process(self, result: str):
        """Called after processing."""
        print(f"Result: {result}")
```

## Streaming Responses

### Basic Streaming

```python
class StreamingAgent(Agent):
    async def stream(self, input_text: str):
        """Stream response word by word."""
        response = await self.llm.generate(input_text)
        
        for word in response.split():
            yield {
                "type": "text",
                "text": word + " "
            }
```

### LLM Streaming

```python
class LLMStreamingAgent(Agent):
    async def stream(self, input_text: str):
        """Stream directly from LLM."""
        async for chunk in self.llm.stream(input_text):
            yield chunk
```

## Policy Integration

### Content Filtering

```yaml
policy:
  content_filter:
    enabled: true
    blocked_words:
      - spam
      - scam
    blocked_patterns:
      - "\\d{3}-\\d{2}-\\d{4}"  # SSN pattern
```

```python
from agentosx.core.policy import ContentFilter

class FilteredAgent(Agent):
    def __init__(self):
        super().__init__()
        self.filter = ContentFilter.from_config(self.config)
    
    async def process(self, input_text: str) -> str:
        # Check input
        if not self.filter.check(input_text):
            return "Sorry, that input contains inappropriate content."
        
        response = await self.llm.generate(input_text)
        
        # Check output
        if not self.filter.check(response):
            return "I can't provide that response."
        
        return response
```

### Approval Gates

```yaml
policy:
  approvals:
    - post_tweet
    - send_email
    - make_purchase
```

```python
from agentosx.core.policy import ApprovalPolicy

class ApprovalAgent(Agent):
    def __init__(self):
        super().__init__()
        self.approval = ApprovalPolicy.from_config(self.config)
    
    @tool
    async def post_tweet(self, text: str) -> dict:
        """Post a tweet (requires approval)."""
        if not await self.approval.request("post_tweet", {"text": text}):
            return {"error": "Action not approved"}
        
        # Actually post tweet
        result = await self.twitter_client.post(text)
        return result
```

### Rate Limiting

```yaml
policy:
  rate_limit:
    requests_per_minute: 10
    requests_per_hour: 100
```

## Testing Your Agent

### Unit Test

```python
import pytest
from my_agent import MyAgent

@pytest.mark.asyncio
async def test_agent_response():
    agent = MyAgent()
    await agent.start()
    
    result = await agent.process("test input")
    assert result is not None
    assert len(result) > 0
    
    await agent.stop()
```

### Integration Test

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_with_tools():
    agent = MyAgent()
    await agent.start()
    
    # Test tool invocation
    result = await agent.process("What's 2 + 2?")
    assert "4" in result
    
    await agent.stop()
```

### Evaluation

```python
from agentosx.evaluation import EvaluationHarness, accuracy

dataset = [
    {"input": "Hello", "expected": "Hi"},
    {"input": "Goodbye", "expected": "Bye"},
]

harness = EvaluationHarness(agent, metrics=[accuracy])
report = await harness.evaluate(dataset)
harness.print_report(report)
```

## Best Practices

1. **Clear Instructions** - Write detailed persona instructions
2. **Tool Documentation** - Document tool inputs/outputs clearly
3. **Error Handling** - Handle errors gracefully with try/except
4. **Logging** - Use structured logging for debugging
5. **Testing** - Write tests for critical functionality
6. **Memory Management** - Clean up old memory entries
7. **Rate Limiting** - Respect API rate limits
8. **Security** - Validate all inputs, filter outputs

## Common Patterns

### Request-Response

Simple synchronous processing:

```python
class RequestResponseAgent(Agent):
    async def process(self, input_text: str) -> str:
        return await self.llm.generate(input_text)
```

### Streaming

Better UX for long responses:

```python
class StreamingAgent(Agent):
    async def stream(self, input_text: str):
        async for chunk in self.llm.stream(input_text):
            yield chunk
```

### Tool-Using

Agent that uses tools:

```python
class ToolAgent(Agent):
    async def process(self, input_text: str) -> str:
        # Let LLM decide which tools to use
        response = await self.llm.generate_with_tools(
            input_text,
            tools=self.tools
        )
        return response
```

### Conversational

Maintains conversation history:

```python
class ConversationalAgent(Agent):
    async def process(self, input_text: str) -> str:
        # Store message
        await self.memory.store(f"user_{self.turn}", input_text)
        
        # Get history
        history = await self.memory.retrieve_recent(n=10)
        
        # Generate with context
        response = await self.llm.generate_with_history(
            input_text,
            history=history
        )
        
        # Store response
        await self.memory.store(f"assistant_{self.turn}", response)
        
        self.turn += 1
        return response
```

## Next Steps

- [Orchestration Patterns](orchestration.md)
- [MCP Integration](mcp-integration.md)
- [Deployment Guide](deployment.md)
- [API Reference](api-reference.md)
