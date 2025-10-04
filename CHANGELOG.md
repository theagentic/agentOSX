# Changelog

All notable changes to AgentOSX will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-10-04

### 🎉 Initial Release

AgentOSX v0.1.0 is a production-ready, MCP-native multi-agent framework for building, orchestrating, and governing agents at scale.

### Added

#### Phase 1: MCP Foundation
- **MCP Protocol Integration** - Native Model Context Protocol support
  - MCP server for exposing agent capabilities
  - MCP client for consuming external tools
  - Tool adapter with automatic schema inference
  - Resource management and URI resolution
  - Prompt template system
  - Three transport layers: STDIO, SSE, WebSocket

- **Declarative Agent System**
  - YAML-based agent manifests (`agent.yaml`)
  - Pydantic schema validation
  - AgentLoader for loading agents from configuration
  - Support for 10 manifest sections (persona, llm, tools, memory, workflows, governance, agentos, mcp, env, metadata)

- **Agent Lifecycle Management**
  - BaseAgent with comprehensive lifecycle hooks
  - States: IDLE, INITIALIZING, RUNNING, PAUSED, STOPPED, ERROR
  - 7 lifecycle hooks: `on_init()`, `on_start()`, `on_stop()`, `on_message()`, `on_tool_call()`, `on_tool_result()`, `on_error()`
  - Automatic state transitions
  - Execution context with conversation history

- **Streaming Support**
  - Real-time streaming with AsyncIterator
  - 5 event types: TEXT, TOOL_CALL, TOOL_RESULT, ERROR, DONE
  - SSE (Server-Sent Events) formatter
  - WebSocket handler
  - Vercel AI SDK compatibility

- **Tool System**
  - Dynamic tool discovery and registration
  - `@tool` decorator with automatic schema inference
  - JSON Schema validation
  - Async tool execution
  - Tool result caching
  - Built-in tools (filesystem, web, code, agentOS)

- **State Management**
  - Checkpointing with version history
  - State snapshots with timestamps
  - Rollback to any previous version
  - Serializable state for persistence

#### Phase 2: Multi-Agent Orchestration
- **Orchestration Patterns**
  - Swarm-style handoffs with context preservation
  - CrewAI-style teams with role-based collaboration
  - LangGraph-style workflows with DAG execution

- **Central Coordinator**
  - Agent registry with discovery
  - Orchestrator management (handoff, crew, graph)
  - Dynamic agent routing

- **Workflow Engine**
  - 6 node types: START, END, AGENT, CONDITION, CHECKPOINT, PARALLEL
  - 4 edge conditions: ALWAYS, ON_SUCCESS, ON_FAILURE, CONDITIONAL
  - Checkpointing for long-running workflows
  - Parallel execution support
  - Error handling with fallback

- **Event-Driven Architecture**
  - Message bus with pub/sub pattern
  - Priority queuing (high, normal, low)
  - Async event dispatch
  - Topic-based routing

- **Migrated Agents**
  - Twitter agent from agentOS (OAuth2, scheduling, persona)
  - Blog agent from agentOS (research, writing, publishing)

#### Phase 3: Developer Experience
- **Rich CLI** - 9 commands powered by Typer + Rich
  - `agentosx init` - Create new agents from templates
  - `agentosx run` - Execute agents with streaming
  - `agentosx dev` - Development server with hot reload
  - `agentosx test` - Run tests with coverage
  - `agentosx mcp` - Manage MCP servers
  - `agentosx agent` - Agent management
  - `agentosx playground` - Interactive REPL
  - `agentosx deploy` - Deploy to agentOS

- **Hot Reload System**
  - File watching with `watchfiles`
  - Automatic agent reloading on code changes
  - Preserves agent state across reloads
  - Graceful error handling

- **Interactive Playground**
  - REPL interface powered by `prompt-toolkit`
  - Command history and autocomplete
  - Multi-line input support
  - Rich formatting for responses
  - 7 slash commands: `/load`, `/reload`, `/status`, `/history`, `/clear`, `help`, `exit`

- **Testing Infrastructure**
  - pytest integration with async support
  - Evaluation harness for agent testing
  - 6 built-in metrics: accuracy, latency, token_usage, semantic_similarity, response_length, word_count
  - Test fixtures and conftest setup
  - Coverage reporting

- **Comprehensive Documentation**
  - Getting started guide
  - Architecture documentation
  - Agent development guide
  - CLI reference
  - API reference
  - Agent manifest guide
  - Quickstart examples

#### Phase 4: AgentOS Integration & Marketplace
- **AgentOS Integration Layer**
  - REST API client with httpx (async, connection pooling, retry logic)
  - WebSocket client with Socket.IO
  - Authentication support (JWT, OAuth)
  - 10 API endpoints integrated

- **State Synchronization**
  - Bidirectional state sync
  - Memory synchronization (working + episodic)
  - Execution trace streaming
  - 3 conflict resolution strategies: last-write-wins, merge, manual
  - Version tracking with SHA256 hashing

- **Deployment Manager**
  - One-click deployment to agentOS
  - tar.gz bundling with manifest
  - Health check verification (30s timeout)
  - Automatic rollback on failure
  - Deployment history tracking

- **Event Subscriber**
  - Real-time platform event subscriptions
  - 7 event types: execution_log, message, progress, user_trigger, deployment, health_check, system_error
  - Decorator-based handlers: `@subscriber.on("event")`
  - Event filtering support

- **Built-in AgentOS Tools**
  - 7 tools for platform operations
  - `list_agents()`, `get_agent_status()`, `trigger_agent()`, `get_execution_logs()`
  - `manage_secrets()` - Secret management (set/get/delete/list)
  - `query_marketplace()`, `install_agent()`
  - MCP integration wrappers

- **Agent Marketplace**
  - Registry client for search and discovery
  - Agent publisher with validation pipeline
    - Structure validation (required files check)
    - Metadata validation (name, version, description, author, license)
    - Security checks (hardcoded secrets, eval/exec, subprocess)
    - Package creation with SHA256 + MD5 checksums
  - Agent installer with verification
    - Download and verify checksums
    - Dependency installation (pip)
    - Version-specific installation
    - Update and uninstall support
  - Semantic versioning support
    - Version comparison operators
    - Compatibility checking
    - Version bumping (major, minor, patch)
    - Upgrade path calculation

### Changed
- N/A (initial release)

### Deprecated
- N/A (initial release)

### Removed
- N/A (initial release)

### Fixed
- Import errors in `state.py` (missing `List` typing)
- Type hint errors in WebSocket transport classes
- Import errors in `installer.py` (missing `List` import)

### Security
- No secrets in logs or error messages
- PII redaction in execution traces
- Secure secret management in agentOS tools
- SHA256 checksum verification for marketplace packages
- Security audit in agent publisher (detects hardcoded secrets, eval/exec)

---

## Known Limitations

1. **Phase 2 Orchestration**: 92% complete, some advanced workflow features pending
2. **Optional Dependencies**: Some features require manual installation (`tweepy`, `watchdog`, `google-generativeai`)
3. **AgentOS Integration**: Requires running agentOS backend locally
4. **Marketplace**: No public registry yet (local/private only)
5. **MCP Transports**: WebSocket transport requires `websockets` package

---

## Upgrade Guide

### From agentOS v1.x

AgentOSX is designed to work alongside agentOS, not replace it. To migrate agents:

1. **Create agent manifest** (`agent.yaml`):
   ```yaml
   name: my-agent
   version: 1.0.0
   persona:
     instructions: |
       Your agent prompt here
   llm:
     provider: openai
     model: gpt-4
   ```

2. **Wrap agent class**:
   ```python
   from agentosx import BaseAgent
   
   class MyAgent(BaseAgent):
       async def process(self, input: str, context=None) -> str:
           # Your existing agent logic
           pass
   ```

3. **Deploy to agentOS**:
   ```bash
   agentosx deploy my-agent --env=production
   ```

See `MIGRATION.md` for detailed migration guide.

---

## Breaking Changes

N/A (initial release)

---

## Compatibility

- **Python**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Operating Systems**: Windows, macOS, Linux
- **AgentOS**: v1.0.0 and above
- **MCP Protocol**: v1.0.0

---

## Dependencies

### Core
- `pydantic>=2.0.0` - Data validation
- `pyyaml>=6.0` - YAML parsing
- `python-dotenv>=1.0.0` - Environment variables
- `requests>=2.31.0` - HTTP client

### CLI & Developer Experience
- `typer>=0.9.0` - CLI framework
- `rich>=13.0.0` - Terminal formatting
- `watchfiles>=0.21.0` - File watching
- `prompt-toolkit>=3.0.0` - Interactive REPL

### AgentOS Integration
- `httpx>=0.25.0` - Async HTTP client
- `python-socketio[client]>=5.10.0` - WebSocket/Socket.IO

### Testing
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support

### Optional
- `websockets>=11.0.0` - WebSocket transport
- `openai>=1.0.0` - OpenAI integration
- `anthropic>=0.7.0` - Anthropic integration
- `google-generativeai>=0.3.0` - Google Gemini integration

---

## Contributors

- **Core Team**: AgentOSX Development Team
- **Community**: Special thanks to early adopters and testers

---

## Links

- **GitHub**: https://github.com/theagentic/agentOSX
- **Documentation**: `docs/`
- **Examples**: `examples/`
- **Issues**: https://github.com/theagentic/agentOSX/issues
- **Discord**: https://discord.gg/agentosx (coming soon)

---

[0.1.0]: https://github.com/theagentic/agentOSX/releases/tag/v0.1.0
