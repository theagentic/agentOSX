# Migration Guide: agentOS → AgentOSX

This guide helps you migrate existing agentOS agents to the AgentOSX framework.

## Overview

**AgentOSX complements agentOS, not replaces it.** Think of AgentOSX as a modern framework that:
- Adds MCP protocol support for interoperability
- Provides declarative YAML configuration
- Enables multi-agent orchestration
- Offers rich developer tooling (CLI, hot reload, playground)
- Connects to the agent marketplace

Your agentOS backend continues to run, and AgentOSX agents can deploy to it.

---

## Migration Strategies

### Strategy 1: Gradual Migration (Recommended)
Keep both frameworks running side-by-side. Migrate agents one at a time.

### Strategy 2: Full Migration
Convert all agents to AgentOSX at once. Requires testing all agents.

### Strategy 3: Hybrid Approach
Use agentOS for simple agents, AgentOSX for complex multi-agent workflows.

---

## Step-by-Step Migration

### 1. Install AgentOSX

```bash
pip install -r requirements.txt
```

### 2. Convert Agent Code

#### Before (agentOS):
```python
# agents/twitter_agent/agent.py
from core.agent_base import AgentBase

class Agent(AgentBase):
    def __init__(self, config=None):
        super().__init__("twitter_agent", config)
        self.api_key = os.getenv("TWITTER_API_KEY")
    
    def process(self, command: str) -> dict:
        # Process command
        return {
            "status": "success",
            "message": "Tweet posted",
            "spoke": "I posted your tweet!",
            "data": {"tweet_id": "123"},
            "agent": "twitter_agent",
            "agent_id": "twitter_agent"
        }
```

#### After (AgentOSX):
```python
# agents/twitter_agent/agent.py
from agentosx import BaseAgent, ExecutionContext, tool
import os

class TwitterAgent(BaseAgent):
    """Twitter agent with OAuth2 and scheduling."""
    
    def __init__(self):
        super().__init__(
            name="twitter_agent",
            version="1.0.0",
            description="Post tweets and manage Twitter account"
        )
        self.api_key = os.getenv("TWITTER_API_KEY")
    
    async def on_init(self):
        """Initialize Twitter API client."""
        # Setup Twitter client
        pass
    
    async def process(self, input: str, context: ExecutionContext = None) -> str:
        """Process tweet command."""
        # Your existing logic
        return "Tweet posted successfully!"
    
    @tool
    async def post_tweet(self, text: str) -> str:
        """Post a tweet."""
        # Your tweet logic
        return f"Posted: {text}"
```

### 3. Create Agent Manifest

Create `agent.yaml` in your agent directory:

```yaml
# agents/twitter_agent/agent.yaml
name: twitter_agent
version: 1.0.0
description: Post tweets and manage Twitter account

persona:
  name: Twitter Bot
  instructions: |
    You are a helpful Twitter assistant that posts tweets,
    monitors mentions, and engages with followers.
  tone: friendly
  traits:
    - professional
    - concise
    - engaging

llm:
  primary:
    provider: openai
    model: gpt-4
    temperature: 0.7
    max_tokens: 500

tools:
  - name: post_tweet
    description: Post a tweet
    schema:
      type: object
      properties:
        text:
          type: string
          description: Tweet text
      required: [text]

memory:
  type: inmem
  config:
    max_items: 100

agentos:
  enabled: true
  url: http://localhost:5000
  sync_interval: 30

metadata:
  author: Your Name
  license: MIT
  tags:
    - social
    - twitter
  category: social_media
```

### 4. Migrate Configuration

#### Before (agentOS):
```bash
# agents/twitter_agent/.env
TWITTER_API_KEY=xyz123
TWITTER_API_SECRET=abc456
```

#### After (AgentOSX):
```bash
# .env (root level)
TWITTER_API_KEY=xyz123
TWITTER_API_SECRET=abc456
OPENAI_API_KEY=sk-...
```

### 5. Test Agent Locally

```bash
# Initialize agent (if starting from scratch)
agentosx init twitter_agent --template=twitter

# Run agent
agentosx run twitter_agent --input="Post a tweet about AI"

# Test in playground
agentosx playground --agent=twitter_agent
```

### 6. Deploy to agentOS

```bash
# Deploy to agentOS backend
agentosx deploy twitter_agent --verify

# Check status
agentosx agent list --remote
```

---

## Feature Mapping

| agentOS Feature | AgentOSX Equivalent | Migration Notes |
|----------------|---------------------|-----------------|
| `Agent.process(command)` | `BaseAgent.process(input, context)` | Make async, add context param |
| `.env` config | `agent.yaml` + `.env` | Split config from secrets |
| Return dict with `status`, `message`, `spoke` | Return string | Simpler return type |
| `AgentBase` | `BaseAgent` | Import from `agentosx` |
| Flask routes | MCP tools | Expose via MCP instead |
| Socket.IO events | Event subscriber | Use `EventSubscriber` |
| Process logger | Built-in logging | Use Python `logging` module |
| Agent discovery | Agent registry | Use `Coordinator` |

---

## Breaking Changes

### 1. Async/Await Required
All agent methods must be async in AgentOSX:

```python
# Before
def process(self, command):
    return "result"

# After
async def process(self, input, context=None):
    return "result"
```

### 2. Response Format
AgentOSX returns simple strings instead of dicts:

```python
# Before
return {
    "status": "success",
    "message": "Done",
    "spoke": "I did it!",
    "data": {...}
}

# After
return "Task completed successfully"
```

If you need structured data, use JSON:
```python
import json
return json.dumps({"status": "success", "data": {...}})
```

### 3. Configuration Split
Separate code config (agent.yaml) from secrets (.env):

```yaml
# agent.yaml - public config
llm:
  provider: openai
  model: gpt-4
```

```bash
# .env - secrets
OPENAI_API_KEY=sk-...
```

### 4. Tool Registration
Use `@tool` decorator instead of custom routes:

```python
# Before (agentOS)
@app.route('/twitter/post', methods=['POST'])
def post_tweet():
    data = request.json
    # Post tweet
    return {"status": "success"}

# After (AgentOSX)
@tool
async def post_tweet(self, text: str) -> str:
    """Post a tweet."""
    # Post tweet
    return "Tweet posted"
```

---

## Common Migration Patterns

### Pattern 1: Simple Command Agent
```python
# Before (agentOS)
class Agent(AgentBase):
    def process(self, command):
        if "post" in command:
            return self.post_tweet(command)
        return {"status": "error", "message": "Unknown command"}

# After (AgentOSX)
class MyAgent(BaseAgent):
    async def process(self, input, context=None):
        if "post" in input:
            return await self.post_tweet(input)
        return "I don't understand that command"
```

### Pattern 2: Scheduled Agent
```python
# Before (agentOS)
class Agent(AgentBase):
    def __init__(self, config):
        super().__init__("scheduler", config)
        self.schedule_task()
    
    def schedule_task(self):
        # Custom scheduling
        pass

# After (AgentOSX)
class SchedulerAgent(BaseAgent):
    async def on_start(self):
        """Start background scheduler."""
        asyncio.create_task(self.run_scheduler())
    
    async def run_scheduler(self):
        while self.status == AgentStatus.RUNNING:
            await self.execute_task()
            await asyncio.sleep(3600)  # 1 hour
```

### Pattern 3: Multi-Tool Agent
```python
# Before (agentOS)
class Agent(AgentBase):
    def process(self, command):
        if "search" in command:
            return self.search(command)
        elif "summarize" in command:
            return self.summarize(command)

# After (AgentOSX)
class MultiToolAgent(BaseAgent):
    @tool
    async def search(self, query: str) -> str:
        """Search the web."""
        # Search logic
        return "Search results"
    
    @tool
    async def summarize(self, text: str) -> str:
        """Summarize text."""
        # Summarize logic
        return "Summary"
    
    async def process(self, input, context=None):
        # LLM decides which tool to call
        return await self.execute_with_llm(input)
```

---

## Troubleshooting

### Issue 1: ImportError - Module Not Found
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

### Issue 2: Agent Not Found
```bash
# Solution: Check agent directory structure
agentosx agent list --local

# Verify agent.yaml exists
ls agents/my_agent/agent.yaml
```

### Issue 3: Deployment Fails
```bash
# Solution: Verify agentOS is running
curl http://localhost:5000/debug/status

# Check agent manifest
agentosx run my_agent --input="test"
```

### Issue 4: Tools Not Discovered
```python
# Solution: Ensure @tool decorator is used
from agentosx import tool

@tool
async def my_tool(self, param: str) -> str:
    """Tool description."""
    return "result"
```

### Issue 5: Memory Issues
```yaml
# Solution: Configure memory in agent.yaml
memory:
  type: inmem  # or sqlite, chroma
  config:
    max_items: 100  # Limit memory size
```

---

## Migration Checklist

- [ ] Install AgentOSX: `pip install -r requirements.txt`
- [ ] Convert agent class to async
- [ ] Create `agent.yaml` manifest
- [ ] Move secrets to `.env`
- [ ] Add `@tool` decorators to methods
- [ ] Test locally: `agentosx run my-agent --input="test"`
- [ ] Test in playground: `agentosx playground --agent=my-agent`
- [ ] Deploy to agentOS: `agentosx deploy my-agent`
- [ ] Verify deployment: `agentosx agent list --remote`
- [ ] Update documentation
- [ ] Notify users of changes

---

## Compatibility Matrix

| Component | agentOS v1.0 | AgentOSX v0.1 | Compatible? |
|-----------|--------------|---------------|-------------|
| REST API | ✅ | ✅ | ✅ Yes |
| WebSocket | ✅ | ✅ | ✅ Yes |
| Agent Structure | ✅ | ⚠️ Different | ⚠️ Migration needed |
| Configuration | .env | .env + agent.yaml | ⚠️ Split required |
| Tool System | Routes | @tool decorator | ❌ No (migration needed) |
| Deployment | Manual | CLI command | ✅ Improved |
| Marketplace | ❌ | ✅ | ➕ New feature |
| MCP Protocol | ❌ | ✅ | ➕ New feature |
| Orchestration | ❌ | ✅ | ➕ New feature |

---

## Getting Help

- **Documentation**: `docs/`
- **Examples**: `examples/`
- **GitHub Issues**: https://github.com/theagentic/agentOSX/issues
- **Discord**: https://discord.gg/agentosx (coming soon)
- **Email**: support@agentosx.dev

---

## Next Steps

1. **Complete Migration**: Follow checklist above
2. **Explore New Features**: Try MCP, orchestration, marketplace
3. **Join Community**: Share your migration experience
4. **Contribute**: Help improve migration tools and docs
