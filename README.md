# AgentOSX

Production-grade, MCP-native multi-agent framework for building, orchestrating, and governing agents at scale.

## 🎯 Key Features

### Phase 1: MCP Foundation ✅
- **MCP (Model Context Protocol) Integration**: Native support for exposing and consuming MCP servers
- **Declarative Agent Definition**: YAML-based agent manifests with schema validation
- **Lifecycle Management**: Comprehensive hooks for initialization, execution, and teardown
- **Streaming Support**: Real-time streaming with SSE, WebSocket, and Vercel AI SDK compatibility
- **Tool System**: Dynamic tool discovery, registration, and execution with schema inference
- **State Management**: Checkpointing, versioning, and rollback capabilities
- **Transport Layers**: STDIO, SSE, and WebSocket transports for MCP communication

### Phase 2: Multi-Agent Orchestration ✅
- **Three Orchestration Patterns**: Swarm-style handoffs, CrewAI-style teams, LangGraph-style workflows
- **Central Coordinator**: Agent registry, discovery, and orchestrator management
- **Context Preservation**: Serializable handoff contexts with conversation history
- **Workflow Graphs**: DAG-based execution with 6 node types and 4 edge conditions
- **Event-Driven Coordination**: Message bus with pub/sub pattern and priority queuing
- **Advanced Workflows**: Checkpointing, conditional branching, parallel execution, error handlers
- **Agent Migrations**: Twitter and Blog agents migrated from agentOS with manifest-driven config

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Create Your First Agent

```python
from agentosx import AgentBuilder

# Define a tool
async def search_web(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

# Build agent
agent = (
    AgentBuilder()
    .name("search-agent")
    .llm("anthropic", "claude-3-sonnet")
    .tool("search", search_web)
    .mcp_server(transport="stdio")
    .build()
)

# Run agent
await agent.initialize()
result = await agent.process("Find information about AI")
print(result)
```

### Multi-Agent Orchestration

```python
from agentosx.orchestration import Coordinator, HandoffManager, WorkflowGraph, NodeType

# Setup coordinator
coordinator = Coordinator()
await coordinator.register_agent("research", research_agent)
await coordinator.register_agent("writer", writer_agent)

# Option 1: Swarm-style handoffs
handoff_manager = HandoffManager(coordinator)
result = await handoff_manager.handoff(
    from_agent_id="research",
    to_agent_id="writer",
    input="Write about AI trends"
)

# Option 2: CrewAI-style teams
from agentosx.orchestration import Crew, CrewRole
crew = Crew(name="content-crew")
await crew.add_member("research", research_agent, CrewRole.WORKER)
await crew.add_task("Research AI trends")
results = await crew.execute()

# Option 3: LangGraph-style workflows
workflow = WorkflowGraph("pipeline", coordinator)
workflow.add_node("research", NodeType.AGENT, agent_id="research")
workflow.add_node("write", NodeType.AGENT, agent_id="writer")
workflow.add_edge("research", "write")
state = await workflow.execute(input="AI trends 2025")
```

### Load from Manifest

Create `agents/my_agent/agent.yaml`:

```yaml
persona:
  name: "Research Assistant"
  system_prompt: "You are an expert researcher"

llm:
  primary:
    provider: "anthropic"
    model: "claude-3-sonnet"
    temperature: 0.7

tools:
  - name: "search_web"
    schema:
      type: "object"
      properties:
        query: {type: "string"}
    implementation: "tools.search_tool"

workflows:
  - name: "research_flow"
    type: "graph"
    nodes:
      - {id: "start", type: "start"}
      - {id: "research", type: "agent"}
      - {id: "end", type: "end"}

mcp:
  server:
    resources:
      - uri: "agent://results"
```

Load and run:

```python
import yaml

# Load manifest
with open("agents/my_agent/agent.yaml") as f:
    manifest = yaml.safe_load(f)

# Create agent from manifest
from agents.my_agent.agent import MyAgent
agent = MyAgent()
await agent.start()
```

## 📚 Documentation

- **[PHASE2_COMPLETE.md](PHASE2_COMPLETE.md)** - Phase 2 orchestration features and implementation status
- **[AGENT_MANIFEST_GUIDE.md](AGENT_MANIFEST_GUIDE.md)** - Complete guide to agent manifest YAML schema
- **[PLAN.md](PLAN.md)** - Project roadmap and development phases
- **[PRD.md](PRD.md)** - Product requirements document

## 🏗️ Architecture

### Phase 1: MCP Foundation

AgentOSX implements the Model Context Protocol for bidirectional tool and resource sharing:

- **Server Mode**: Expose agent capabilities as MCP tools
- **Client Mode**: Consume external MCP servers (filesystem, git, databases)
- **Dynamic Discovery**: Automatically register and discover tools
- **Streaming**: Support for long-running operations with progress updates

### Phase 2: Multi-Agent Orchestration

Three orchestration patterns for different coordination needs:

#### 1. Swarm-style Handoffs (Lightweight Delegation)
- Agent-to-agent task handoffs with context preservation
- Return-to-caller mechanism
- Auto-routing with custom rules
- Serializable contexts for persistence

#### 2. CrewAI-style Teams (Role-Based Collaboration)
- Four crew roles: Manager, Worker, Reviewer, Specialist
- Task queue with priorities and dependencies
- Three execution modes: Sequential, Parallel, Hierarchical
- Shared memory for team state

#### 3. LangGraph-style Workflows (DAG Execution)
- 6 node types: Agent, Condition, Checkpoint, Parallel, Error Handler, Start/End
- 4 edge conditions: Always, On Success, On Failure, Conditional
- State management with checkpointing
- Retry logic and error handling
- YAML workflow definitions

### Message Bus
Event-driven coordination with pub/sub pattern:
- Topic-based routing with wildcards
- Priority queuing (LOW, NORMAL, HIGH, CRITICAL)
- Handler statistics and message history
- AgentOS event system integration

### Agent Lifecycle

```
1. Initialize → 2. Start → 3. Process → 4. Stop
       ↓            ↓           ↓          ↓
   on_init()   on_start()  on_message() on_stop()
```

## 📁 Project Structure

```
agentOSX/
├── agentosx/                 # Core framework
│   ├── orchestration/        # Multi-agent orchestration
│   │   ├── coordinator.py    # Central coordinator (265 lines)
│   │   ├── handoff.py        # Swarm-style handoffs (347 lines)
│   │   ├── crew.py           # CrewAI teams (456 lines)
│   │   ├── graph.py          # LangGraph workflows (546 lines)
│   │   └── message_bus.py    # Event bus (359 lines)
│   ├── core/
│   │   ├── llm/              # LLM abstraction layer
│   │   ├── memory/           # Memory systems
│   │   ├── policy/           # Governance policies
│   │   └── tools/            # Tool system
│   └── agents/
│       └── base.py           # Base agent class
├── agents/                   # Agent implementations
│   ├── _template/            # Agent template (584 lines)
│   ├── twitter_agent/        # Twitter agent (814 lines)
│   │   ├── agent.yaml        # Manifest (330 lines)
│   │   └── agent.py          # Implementation (484 lines)
│   └── blog_agent/           # Blog agent
│       └── agent.yaml        # Manifest (447 lines)
├── examples/
│   ├── orchestration_examples.py  # All patterns demo
│   └── social_post_demo.py
└── docs/
    ├── PHASE2_COMPLETE.md         # Phase 2 status
    └── AGENT_MANIFEST_GUIDE.md    # Manifest guide
```

## 🚀 Examples

### Basic Examples
See the `examples/` directory for:

- **`orchestration_examples.py`** - Complete demonstration of all orchestration patterns
  - Example 1: Swarm-style handoffs with context preservation
  - Example 2: CrewAI-style teams with role-based collaboration
  - Example 3: LangGraph-style workflows with DAG execution
  - Example 4: Message bus coordination with pub/sub
  - Example 5: Combined orchestration using multiple patterns

- **`social_post_demo.py`** - Social media posting agent

### Production Agents

- **Twitter Agent** (`agents/twitter_agent/`)
  - Tweepy v2 API integration
  - Google Gemini for AI thread generation
  - File system monitoring for blog posts
  - 9-node workflow with approval gate
  - Rate limiting and statistics tracking

- **Blog Agent** (`agents/blog_agent/`)
  - Complex 15-node workflow
  - Parallel section writing
  - Quality check with conditional looping
  - Manual approval gate
  - Plagiarism detection

## 📦 Requirements

- Python 3.10+
- pydantic >= 2.0
- pyyaml
- asyncio
- Additional dependencies per agent (tweepy, google-generativeai, etc.)

## ✅ Phase 1 Complete

✅ MCP Protocol Implementation (JSON-RPC 2.0)  
✅ MCP Server with tool/resource/prompt support  
✅ MCP Client with dynamic discovery  
✅ Transport layers (STDIO, SSE, WebSocket)  
✅ Tool adapter with schema inference  
✅ Enhanced BaseAgent with lifecycle hooks  
✅ Agent loader from YAML manifests  
✅ Streaming support with multiple formats  
✅ SDK with fluent builder API  
✅ LLM router with 7 providers  
✅ Policy system (content filters, rate limits, approvals)  
✅ Memory systems (vector, buffer, hybrid)  

## ✅ Phase 2 Complete (92%)

✅ Central Coordinator (265 lines)  
✅ Swarm-style Handoffs (347 lines)  
✅ CrewAI-style Teams (456 lines)  
✅ LangGraph-style Workflows (546 lines)  
✅ Message Bus (359 lines)  
✅ Agent Manifest Schema (274 lines)  
✅ Template Agent (584 lines)  
✅ Twitter Agent Migration (814 lines)  
✅ Comprehensive Examples (orchestration_examples.py)  
🟡 Blog Agent Implementation (manifest complete, implementation pending)  

**Total Phase 2 Code: 3,800+ lines**

## 🔜 Next Steps

### Immediate Tasks
1. Complete Blog Agent implementation
2. Create integration test suite
3. Add workflow visualization
4. Create deployment guides

### Phase 3 Planning
- Web UI for orchestration monitoring
- Workflow debugger with step-through
- Performance metrics dashboard
- Additional agent migrations
- Workflow template library
- Policy engine with governance
- CLI tools for development
- Hot reload and debugging tools
- AgentOS integration layer

A plugin-first, multi-provider agent runtime inspired by elizaOS's registry pattern, extended for production use with multi-provider LLMs, social integrations, policy governance, workflows, and observability.

## Features

- **Unified LLM Abstraction**: Support for OpenAI, Anthropic, Google Gemini, Grok, OpenRouter, Together, and Ollama with intelligent routing
- **Social-First**: Native X/Twitter v2, Discord, and Telegram integrations with proper OAuth scopes
- **Plugin Registry**: Everything is a plugin - tools, clients, evaluators, memory backends
- **Governance**: Approval gates, content filters, and rate limiting for production safety
- **Workflows**: Graph and crew-based orchestration with planning capabilities
- **Observability**: Full tracing, metrics collection, and evaluation harness
- **Memory**: Short-term buffers, long-term vector stores, and artifact tracking

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd agentos

# Install dependencies (Python 3.10+)
pip install -r requirements.txt

# Optional: Install for development
pip install -e .
```

### 2. Environment Configuration

Create a `.env` file or set environment variables:

```bash
# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
GROK_API_KEY=...
OPENROUTER_API_KEY=...
TOGETHER_API_KEY=...
OLLAMA_HOST=http://localhost:11434

# X/Twitter (OAuth2 with required scopes)
X_CLIENT_ID=...
X_CLIENT_SECRET=...
X_REDIRECT_URI=http://localhost:8080/callback
X_ACCESS_TOKEN=...
X_REFRESH_TOKEN=...
# Required scopes: tweet.write, users.read, media.write

# Social Platforms
DISCORD_BOT_TOKEN=...
TELEGRAM_BOT_TOKEN=...

# Development
GITHUB_TOKEN=...
```

### 3. Run Examples

```bash
# Social posting with approval flow
python examples/social_post_demo.py

# RAG assistant demo
python examples/rag_demo.py
```

## Architecture

```
agentos/
├── core/
│   ├── llm/           # LLM providers and routing
│   ├── tools/         # Plugin registry and built-in tools
│   ├── memory/        # Memory stores and management
│   ├── policy/        # Governance and safety
│   ├── workflows/     # Graph/crew orchestration
│   └── observability/ # Tracing, metrics, evals
├── agents/            # Pre-built agents
├── examples/          # Runnable demos
└── settings.py        # Configuration management
```

## Key Concepts

### Plugin Registry
All functionality extends through plugins with manifests declaring capabilities, permissions, and dependencies. Similar to elizaOS's pattern but extended for production needs.

### LLM Router
Intelligent routing based on cost, latency, and capabilities with automatic fallbacks:
- Creative tasks → OpenRouter/OpenAI → Anthropic
- Planning → Anthropic → OpenAI
- Local-only → Ollama

### Governance
- **Approvals**: Queue high-impact actions for human review
- **Content Filters**: Block unsafe content with regex and classifiers
- **Rate Limits**: Token bucket implementation per client/agent

### X/Twitter Integration
- Uses v2 API for posting with proper OAuth scopes
- Handles media upload with v1.1 fallback when needed
- Implements idempotency keys and rate limit handling
- Respects tier limits (Free/Basic/Pro)

## Production Considerations

- **Observability**: Every LLM and tool call is traced with spans
- **Security**: Secrets are never logged; PII is redacted
- **Reliability**: Automatic retries with exponential backoff
- **Scalability**: Plugin architecture allows horizontal scaling
- **Testing**: Comprehensive test coverage for critical paths

## Development

### Adding a New Provider

1. Create provider in `core/llm/providers/`
2. Implement `BaseLLM` interface
3. Add to router configuration
4. Update settings for API keys

### Creating Custom Agents

1. Create agent directory in `agents/`
2. Define `persona.yaml` for configuration
3. Implement `agent.py` with business logic
4. Register with plugin manifest

### Writing Plugins

1. Create plugin with manifest.json
2. Define capabilities and permissions
3. Implement required interfaces
4. Place in plugins directory or provide Git URL

## Testing

```bash
# Run unit tests
pytest tests/

# Run integration tests
pytest tests/integration/

# Run eval suite
python -m agentos.core.observability.evals
```

## License

MIT

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## Disclaimer

Always adhere to platform policies and local laws when using social integrations. This framework provides governance tools but ultimate responsibility lies with the operator.
