# AgentOSX CLI Quick Reference

## Installation

```bash
pip install -r requirements.txt
```

## Core Commands

### Create Agent
```bash
# Basic agent
agentosx init my-agent

# From template
agentosx init twitter-bot --template=twitter
agentosx init blog-writer --template=blog
agentosx init my-crew --template=crew
```

### Run Agent
```bash
# Simple run
agentosx run my-agent --input="Hello!"

# From file
agentosx run my-agent --input-file=prompt.txt

# With streaming
agentosx run my-agent --input="Hello!" --stream
```

### Development Server
```bash
# With hot reload
agentosx dev my-agent --watch

# Custom port
agentosx dev my-agent --watch --port=8000 --host=0.0.0.0
```

### Testing
```bash
# All tests
agentosx test my-agent

# Specific suite
agentosx test my-agent --suite=unit
agentosx test my-agent --suite=integration
agentosx test my-agent --suite=e2e

# With coverage
agentosx test my-agent --coverage

# Verbose output
agentosx test my-agent --verbose

# Watch mode
agentosx test my-agent --watch
```

### MCP Server
```bash
# Start with stdio (CLI tools)
agentosx mcp start my-agent --transport=stdio

# Start with SSE (web apps)
agentosx mcp start my-agent --transport=sse --port=8080

# Start with WebSocket (real-time)
agentosx mcp start my-agent --transport=websocket --port=8080

# List running servers
agentosx mcp list

# Stop server
agentosx mcp stop my-agent
```

### Agent Management
```bash
# List local agents
agentosx agent list --local

# List remote agents (agentOS)
agentosx agent list --remote

# Create new agent
agentosx agent create my-agent
```

### Interactive Playground
```bash
# Start with agent
agentosx playground --agent=my-agent

# Start empty (load later)
agentosx playground

# Web UI mode
agentosx playground --web
```

### Deployment
```bash
# Deploy to staging
agentosx deploy my-agent --env=staging

# Deploy to production
agentosx deploy my-agent --env=production --build
```

## Playground Commands

Once in the playground:

```
# Chat
> Hello there!

# Commands
/load <path>      Load an agent
/reload           Reload current agent
/status           Show agent status
/history          Show command history
/clear            Clear screen
help              Show help message
exit              Exit playground
```

## Agent Structure

Created by `agentosx init`:

```
my-agent/
├── agent.yaml        # Configuration
├── agent.py          # Agent code
├── README.md         # Documentation
└── .gitignore        # Git ignore
```

## Configuration File (`agent.yaml`)

```yaml
name: my-agent
version: 1.0.0

persona:
  instructions: |
    System prompt here

llm:
  provider: openai  # openai, anthropic, google, grok, ollama, together, openrouter
  model: gpt-4
  temperature: 0.7
  max_tokens: 1000

tools:
  - name: tool_name
    description: Tool description

memory:
  type: inmem  # inmem, sqlite, chroma
  config:
    path: ./memory.db  # for sqlite/chroma

policy:
  approvals:
    - sensitive_action
  content_filter:
    enabled: true
    blocked_words: [spam, scam]
  rate_limit:
    requests_per_minute: 10
```

## Agent Code Template

```python
from agentosx.agents.base import Agent, tool, hook

class MyAgent(Agent):
    """Agent description."""
    
    name = "my-agent"
    
    async def process(self, input_text: str) -> str:
        """Process input and return response."""
        return "Response"
    
    async def stream(self, input_text: str):
        """Stream response chunks."""
        yield {"type": "text", "text": "chunk"}
    
    @tool
    def my_tool(self, param: str) -> str:
        """Tool description."""
        return "result"
    
    @hook("start")
    async def on_start(self):
        """Called when agent starts."""
        pass
    
    @hook("stop")
    async def on_stop(self):
        """Called when agent stops."""
        pass
```

## Testing

### Unit Test
```python
import pytest

@pytest.mark.unit
@pytest.mark.asyncio
async def test_agent():
    agent = MyAgent()
    await agent.start()
    result = await agent.process("test")
    assert result is not None
    await agent.stop()
```

### Evaluation
```python
from agentosx.evaluation import EvaluationHarness, accuracy

dataset = [
    {"input": "Hello", "expected": "Hi"},
]

harness = EvaluationHarness(agent, metrics=[accuracy])
report = await harness.evaluate(dataset)
harness.print_report(report)
```

## Available Metrics

- `accuracy` - Exact match scoring
- `latency` - Response time
- `token_usage` - Token count
- `semantic_similarity` - Word overlap
- `response_length` - Character count
- `word_count` - Word count

## LLM Providers

| Provider | Models |
|----------|--------|
| openai | gpt-4, gpt-3.5-turbo |
| anthropic | claude-3-opus, claude-3-sonnet, claude-3-haiku |
| google | gemini-pro |
| grok | grok-1 |
| ollama | llama2, mistral, etc. |
| together | Various open models |
| openrouter | 100+ models |

## Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY=sk-...

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Google
export GOOGLE_API_KEY=...

# Grok
export GROK_API_KEY=...

# Together AI
export TOGETHER_API_KEY=...

# OpenRouter
export OPENROUTER_API_KEY=...
```

## Common Workflows

### Quick Prototype
```bash
agentosx init prototype
cd prototype
# Edit agent.py and agent.yaml
agentosx run prototype --input="test"
```

### Development with Hot Reload
```bash
agentosx init dev-agent
cd dev-agent
agentosx dev dev-agent --watch
# Make changes, see live updates
```

### Testing Before Deploy
```bash
agentosx test my-agent --suite=unit --coverage
agentosx test my-agent --suite=integration
agentosx playground --agent=my-agent
# Manual testing
agentosx deploy my-agent --env=production
```

### MCP Integration
```bash
# Create agent
agentosx init mcp-agent

# Add tools to agent.py
@tool
def my_tool(self, param: str) -> str:
    return "result"

# Run as MCP server
agentosx mcp start mcp-agent --transport=stdio
```

## Troubleshooting

### Agent not found
```bash
# Check current directory
agentosx agent list --local

# Use full path
agentosx run /full/path/to/agent --input="test"
```

### Import errors
```bash
# Install dependencies
pip install -r requirements.txt

# Check Python version (3.8+)
python --version
```

### Tests failing
```bash
# Run with verbose output
agentosx test my-agent --verbose

# Check specific suite
agentosx test my-agent --suite=unit -vv
```

## Getting Help

```bash
# General help
agentosx --help

# Command help
agentosx init --help
agentosx run --help
agentosx test --help
```

## Documentation

- **Getting Started**: `docs/getting-started.md`
- **Architecture**: `docs/architecture.md`
- **Agent Development**: `docs/agent-development.md`
- **Examples**: `examples/quickstart/`

## Resources

- GitHub: https://github.com/agentOSX/agentOSX
- Docs: `docs/`
- Examples: `examples/`
- Discord: https://discord.gg/agentosx
