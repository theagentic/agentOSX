# agentOS: Production-Ready Python Agent Framework

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
