# Getting Started with AgentOSX

Welcome to AgentOSX! This guide will help you build your first agent in 5 minutes.

## Installation

```bash
pip install agentosx
```

## Quick Start

### 1. Create Your First Agent

```bash
agentosx init my-first-agent
cd my-first-agent
```

This creates a basic agent structure:

```
my-first-agent/
├── agent.yaml        # Agent configuration
├── agent.py          # Agent code
└── README.md         # Documentation
```

### 2. Configure Your Agent

Edit `agent.yaml`:

```yaml
name: my-first-agent
version: 1.0.0

persona:
  instructions: |
    You are a helpful assistant that provides information about AgentOSX.

llm:
  provider: openai
  model: gpt-4
  temperature: 0.7

tools: []
memory:
  type: inmem
```

### 3. Run Your Agent

```bash
agentosx run my-first-agent --input="Hello!"
```

You should see:

```
✓ Agent loaded: my-first-agent
Processing...

╭─ Agent Response ─╮
│ Hello! How can I │
│ help you today?  │
╰──────────────────╯

Duration: 1.23s
```

## Development Mode

Enable hot reload for faster development:

```bash
agentosx dev my-first-agent --watch
```

Now any changes to your agent files will automatically reload!

## Interactive Playground

Test your agent interactively:

```bash
agentosx playground --agent=my-first-agent
```

Try these commands:
- Type any message to chat with your agent
- `/reload` - Reload the agent
- `/status` - Check agent status
- `/history` - View command history
- `help` - Show all commands

## MCP Server Mode

Run your agent as an MCP server:

```bash
agentosx mcp start my-first-agent --transport=stdio
```

Your agent is now available as an MCP server that other applications can connect to!

## Testing

Run tests for your agent:

```bash
agentosx test my-first-agent --suite=unit
```

## Next Steps

- **Add Tools**: Learn how to add tools to your agent in [Agent Development](agent-development.md)
- **Use Memory**: Understand memory systems in [Architecture](architecture.md)
- **Orchestration**: Build multi-agent systems with [Orchestration](orchestration.md)
- **Deploy**: Deploy to production with [Deployment Guide](deployment.md)

## Templates

AgentOSX includes templates for common use cases:

### Twitter Agent

```bash
agentosx init my-twitter-bot --template=twitter
```

Creates an agent that can post to Twitter, read mentions, and reply.

### Blog Writer

```bash
agentosx init my-blog-writer --template=blog
```

Creates an agent that can research topics, write blog posts, and generate SEO metadata.

### Crew Agent

```bash
agentosx init my-crew --template=crew
```

Creates a multi-agent crew with specialized roles (researcher, writer, editor).

## Help & Support

- **Documentation**: Full docs at [docs/](../docs/)
- **Examples**: See [examples/](../examples/)
- **Issues**: Report bugs on [GitHub](https://github.com/agentOSX/agentOSX/issues)
- **Community**: Join our [Discord](https://discord.gg/agentosx)

## Common Commands

```bash
# Create agent
agentosx init <name> [--template=TYPE]

# Run agent
agentosx run <agent> --input="text"

# Development server
agentosx dev <agent> --watch --port=8000

# Test agent
agentosx test <agent> [--suite=unit|integration|e2e]

# MCP server
agentosx mcp start <agent> [--transport=stdio|sse|websocket]
agentosx mcp list
agentosx mcp stop <name>

# Agent management
agentosx agent list [--local] [--remote]
agentosx agent create <name>

# Interactive mode
agentosx playground [--agent=NAME] [--web]

# Deploy
agentosx deploy <agent> [--env=production]
```

Happy building! 🚀
