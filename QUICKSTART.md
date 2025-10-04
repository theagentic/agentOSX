# AgentOSX Quick Start Guide

Get up and running with AgentOSX in 5 minutes.

## Installation

```bash
# Clone the repository
git clone https://github.com/theagentic/agentOSX.git
cd agentOSX

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from agentosx import AgentBuilder; print('✅ AgentOSX installed successfully!')"
```

## Your First Agent

### 1. Simple Agent with Builder API

Create a file `my_agent.py`:

```python
import asyncio
from agentosx import AgentBuilder

# Define a tool
async def greet(name: str) -> str:
    """Greet a user by name."""
    return f"Hello, {name}! Welcome to AgentOSX!"

# Build agent
agent = (
    AgentBuilder()
    .name("greeter")
    .version("1.0.0")
    .description("A friendly greeting agent")
    .llm("anthropic", "claude-3-sonnet")
    .tool("greet", greet, "Greet a user by name")
    .system_prompt("You are a friendly assistant.")
    .build()
)

async def main():
    # Initialize and start
    await agent.initialize()
    await agent.start()
    
    # Process input
    result = await agent.process("Greet Alice")
    print(result)
    
    # Clean up
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python my_agent.py
```

### 2. Agent from YAML Manifest

Create `agent.yaml`:

```yaml
version: "1.0"
agent:
  name: "calculator-agent"
  version: "1.0.0"
  description: "A calculator agent"
  
  llm:
    provider: "anthropic"
    model: "claude-3-sonnet"
    temperature: 0.7
    max_tokens: 2000
  
  tools:
    - "calculate"
  
  mcp:
    enabled: true
    transport: "stdio"
    expose_tools: true
```

Load and run:

```python
from agentosx import AgentLoader

async def main():
    loader = AgentLoader()
    agent = loader.load_from_file("agent.yaml")
    
    await agent.initialize()
    await agent.start()
    
    result = await agent.process("Calculate 2 + 2")
    print(result)

asyncio.run(main())
```

### 3. Custom Agent Class

For more control, subclass `BaseAgent`:

```python
from agentosx import BaseAgent, ExecutionContext

class WeatherAgent(BaseAgent):
    """Custom agent for weather queries."""
    
    def __init__(self):
        super().__init__(
            name="weather-agent",
            version="1.0.0",
            description="Provides weather information"
        )
    
    async def on_init(self):
        """Initialize weather API connection."""
        print("Connecting to weather API...")
        self.api_key = "your-api-key"
    
    async def on_start(self):
        """Agent started."""
        print("Weather agent is ready!")
    
    async def process(self, input: str, context=None) -> str:
        """Process weather queries."""
        # In production, call actual weather API
        return f"Weather info for: {input}"

# Use it
agent = WeatherAgent()
await agent.initialize()
await agent.start()
result = await agent.process("San Francisco")
```

## Expose as MCP Server

Make your agent available to Claude Desktop or other MCP clients:

```python
from agentosx import AgentBuilder
from agentosx.mcp.transport import StdioTransport

# Create agent
agent = (
    AgentBuilder()
    .name("my-mcp-agent")
    .llm("anthropic", "claude-3-sonnet")
    .tool("my_tool", my_tool_func)
    .mcp_server(transport="stdio")
    .build()
)

# Start MCP server
async def main():
    await agent.initialize()
    
    mcp_server = agent.to_mcp_server()
    transport = StdioTransport()
    
    print("MCP Server started on STDIO")
    await mcp_server.start(transport)

asyncio.run(main())
```

Add to Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "my-agent": {
      "command": "python",
      "args": ["path/to/my_agent.py"]
    }
  }
}
```

## Streaming Responses

Enable real-time streaming for better UX:

```python
from agentosx import BaseAgent, StreamEvent
from agentosx.streaming.events import TextEvent

class StreamingAgent(BaseAgent):
    async def stream(self, input: str, context=None):
        """Stream response in chunks."""
        words = ["Streaming", "response", "from", "agent"]
        
        for word in words:
            yield TextEvent(
                agent_id=self.name,
                text=word + " "
            )
            await asyncio.sleep(0.1)

# Use it
agent = StreamingAgent()
await agent.initialize()

async for event in agent.stream("Hello"):
    if event.type == EventType.TEXT:
        print(event.data["text"], end="", flush=True)
```

## Add Tools Dynamically

```python
# Define tools
def search_web(query: str) -> str:
    """Search the web."""
    return f"Results for: {query}"

def analyze_text(text: str) -> dict:
    """Analyze text."""
    return {
        "length": len(text),
        "words": len(text.split())
    }

# Build agent with multiple tools
agent = (
    AgentBuilder()
    .name("multi-tool-agent")
    .llm("anthropic", "claude-3-sonnet")
    .tool("search", search_web)
    .tool("analyze", analyze_text)
    .build()
)
```

## Use Lifecycle Hooks

```python
class MyAgent(BaseAgent):
    async def on_init(self):
        """Called after initialization."""
        print("Agent initialized!")
        self.data = []
    
    async def on_start(self):
        """Called when agent starts."""
        print("Agent starting...")
        self.active = True
    
    async def on_stop(self):
        """Called before agent stops."""
        print("Agent stopping...")
        self.active = False
    
    async def on_message(self, message: str):
        """Called on each message."""
        self.data.append(message)
    
    async def on_error(self, error: Exception):
        """Called on errors."""
        print(f"Error occurred: {error}")
```

## Common Patterns

### 1. Agent with State

```python
from agentosx import BaseAgent, ExecutionContext

class StatefulAgent(BaseAgent):
    async def process(self, input: str, context=None):
        # Get current state
        state = self.get_state()
        
        # Update state
        self.update_state(
            context={"last_input": input},
            metadata={"count": state.metadata.get("count", 0) + 1}
        )
        
        return f"Processed input #{state.metadata['count']}"
```

### 2. Agent with Context

```python
context = ExecutionContext(
    input="Hello",
    session_id="session-123",
    user_id="user-456",
    metadata={"lang": "en"}
)

agent.set_context(context)
result = await agent.process("Hello", context)
```

### 3. Multiple Tools

```python
tools = {
    "calculate": lambda expr: eval(expr),
    "uppercase": lambda text: text.upper(),
    "reverse": lambda text: text[::-1],
}

builder = AgentBuilder().name("tool-agent").llm("anthropic", "claude-3-sonnet")

for name, func in tools.items():
    builder.tool(name, func, f"Tool: {name}")

agent = builder.build()
```

## Run Examples

The repository includes several complete examples:

```bash
# Simple MCP server
python examples/mcp_server_example.py

# Complete feature demonstration
python examples/complete_example.py

# Social media posting agent
python examples/social_post_demo.py
```

## Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/test_integration.py -v

# Run specific test
pytest tests/test_integration.py::test_agent_lifecycle -v
```

## Environment Setup

Create `.env` file for API keys:

```bash
# LLM Provider Keys
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Optional
GOOGLE_API_KEY=your_key_here
XAI_API_KEY=your_key_here
```

Load in code:

```python
from dotenv import load_dotenv
load_dotenv()
```

## Debugging

Enable debug logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Next Steps

1. **Read the docs:**
   - [README.md](README.md) - Project overview
   - [PLAN.md](PLAN.md) - Technical details
   - [PHASE1_COMPLETE.md](PHASE1_COMPLETE.md) - Features list

2. **Explore examples:**
   - Check out `examples/` directory
   - Run `complete_example.py` for interactive demos

3. **Build your agent:**
   - Start with `AgentBuilder` for rapid prototyping
   - Use YAML manifests for declarative agents
   - Subclass `BaseAgent` for full control

4. **Join the community:**
   - Report issues on GitHub
   - Contribute improvements
   - Share your agents

## Troubleshooting

### Import Error

```python
# If you get import errors, ensure agentOSX is in your Python path
import sys
sys.path.insert(0, '/path/to/agentOSX')
```

### Async Issues

```python
# Always use asyncio.run() for top-level async code
import asyncio

async def main():
    # Your async code here
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

### MCP Server Not Working

- Ensure STDIO transport is used for Claude Desktop
- Check that agent is properly initialized
- Verify JSON-RPC messages are formatted correctly

## Support

- **Issues:** https://github.com/theagentic/agentOSX/issues
- **Discussions:** https://github.com/theagentic/agentOSX/discussions
- **Documentation:** See project docs/

---

**Happy building with AgentOSX! 🚀**
