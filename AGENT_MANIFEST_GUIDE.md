# Agent Manifest Guide

## Overview

Agent manifests are YAML files that declaratively configure agents in AgentOSX. They enable configuration-driven agent development, separating concerns between agent logic (Python code) and configuration (YAML).

## Why Use Manifests?

✅ **Declarative Configuration**: Define agent behavior without code  
✅ **Version Control**: Track configuration changes separately from code  
✅ **Environment Portability**: Same agent code, different configs per environment  
✅ **Hot Reloading**: Update configuration without restarting agent  
✅ **Schema Validation**: Pydantic models ensure configuration correctness  
✅ **Documentation**: Self-documenting agent capabilities  

---

## Complete Manifest Structure

```yaml
# Agent Manifest Schema v1.0
# File: agent.yaml

# ============================================================================
# SECTION 1: Persona - Agent Identity and Behavior
# ============================================================================
persona:
  name: "My Agent"
  description: "Brief description of what this agent does"
  system_prompt: |
    You are an AI assistant specialized in...
    Your primary goal is to...
  tone: "professional"  # or: casual, friendly, technical, formal
  traits:
    - analytical
    - creative
    - detail-oriented
  goals:
    - "Help users achieve X"
    - "Provide accurate information about Y"

# ============================================================================
# SECTION 2: LLM Configuration - Model Selection and Settings
# ============================================================================
llm:
  primary:
    provider: "openai"  # openai, anthropic, google_gemini, grok, ollama, together, openrouter
    model: "gpt-4-turbo"
    temperature: 0.7
    max_tokens: 4096
    top_p: 0.9
  
  fallback:  # Optional backup when primary fails
    provider: "anthropic"
    model: "claude-3-sonnet-20240229"
    temperature: 0.7

# ============================================================================
# SECTION 3: Tools - Agent Capabilities
# ============================================================================
tools:
  - name: "search_web"
    description: "Search the web for information"
    schema:
      type: "object"
      properties:
        query:
          type: "string"
          description: "Search query"
        max_results:
          type: "integer"
          description: "Maximum number of results"
          default: 10
      required: ["query"]
    implementation: "tools.search_tool"  # Python module path
    config:
      api_key: "${SEARCH_API_KEY}"  # Environment variable
      timeout: 30

  - name: "analyze_data"
    description: "Analyze structured data"
    schema:
      type: "object"
      properties:
        data:
          type: "array"
          items:
            type: "object"
        analysis_type:
          type: "string"
          enum: ["summary", "trends", "anomalies"]
      required: ["data", "analysis_type"]
    implementation: "tools.analytics_tool"

# ============================================================================
# SECTION 4: Memory - State Persistence
# ============================================================================
memory:
  # Vector store for semantic memory
  vector:
    provider: "chroma"  # chroma, pinecone, weaviate
    collection: "agent_memory"
    embedding_model: "text-embedding-3-small"
    config:
      persist_directory: "./data/chroma"
      distance_metric: "cosine"
  
  # Conversation buffer
  buffer:
    type: "sliding_window"  # or: token_buffer, summary
    max_messages: 50
    max_tokens: 4000
  
  # Persistence
  persistence: true
  storage_path: "./data/agent_state"

# ============================================================================
# SECTION 5: Workflows - Multi-Step Processes
# ============================================================================
workflows:
  - name: "process_task"
    description: "Main task processing workflow"
    type: "graph"  # graph, sequential, parallel
    
    nodes:
      - id: "start"
        type: "start"
      
      - id: "research"
        type: "agent"
        agent_id: "research_agent"
        config:
          input_template: "Research: {input}"
          output_key: "research_data"
        retry:
          max_retries: 3
          retry_delay: 1.0
      
      - id: "checkpoint_1"
        type: "checkpoint"
        config:
          name: "after_research"
      
      - id: "write"
        type: "agent"
        agent_id: "writer_agent"
        config:
          input_template: "Write based on: {research_data}"
          output_key: "draft"
      
      - id: "quality_check"
        type: "condition"
        config:
          condition: "quality_score > 0.8"
          output_key: "passes_quality"
      
      - id: "approve"
        type: "checkpoint"
        config:
          name: "awaiting_approval"
          manual_approval: true
          timeout: 3600  # 1 hour
      
      - id: "publish"
        type: "agent"
        agent_id: "publisher_agent"
        config:
          input_template: "Publish: {draft}"
      
      - id: "error_handler"
        type: "error_handler"
        config:
          retry: true
          fallback_node: "start"
      
      - id: "end"
        type: "end"
    
    edges:
      - from: "start"
        to: "research"
        condition: "always"
      
      - from: "research"
        to: "checkpoint_1"
        condition: "on_success"
      
      - from: "checkpoint_1"
        to: "write"
        condition: "always"
      
      - from: "write"
        to: "quality_check"
        condition: "on_success"
      
      - from: "quality_check"
        to: "approve"
        condition: "conditional"
        condition_func: "lambda state: state.variables.get('passes_quality', False)"
      
      - from: "quality_check"
        to: "write"
        condition: "conditional"
        condition_func: "lambda state: not state.variables.get('passes_quality', True)"
      
      - from: "approve"
        to: "publish"
        condition: "on_success"
      
      - from: "publish"
        to: "end"
        condition: "on_success"
      
      - from: "research"
        to: "error_handler"
        condition: "on_failure"
      
      - from: "write"
        to: "error_handler"
        condition: "on_failure"

# ============================================================================
# SECTION 6: Governance - Policies and Controls
# ============================================================================
governance:
  # Content filtering
  content_filters:
    - type: "toxicity"
      threshold: 0.7
      action: "reject"  # reject, warn, log
    
    - type: "pii"
      detect: ["email", "phone", "ssn"]
      action: "redact"
    
    - type: "plagiarism"
      similarity_threshold: 0.7
      action: "warn"
  
  # Rate limiting
  rate_limits:
    requests_per_minute: 20
    requests_per_hour: 500
    requests_per_day: 5000
    
    # Per-tool limits
    tool_limits:
      search_web: 100  # per hour
      publish_content: 10  # per day
  
  # Approval requirements
  approval:
    required_for:
      - "publish"
      - "delete"
      - "external_api_call"
    approvers:
      - "admin@example.com"
    timeout: 3600  # seconds
  
  # Cost controls
  cost_controls:
    max_cost_per_request: 1.0  # USD
    max_cost_per_day: 50.0
    alert_threshold: 40.0

# ============================================================================
# SECTION 7: AgentOS Integration - External System Connection
# ============================================================================
agentos:
  enabled: true
  
  # Event subscriptions
  events:
    subscribe:
      - "task.created"
      - "workflow.started"
    publish:
      - "task.completed"
      - "task.failed"
  
  # API configuration
  api:
    base_url: "http://localhost:8000"
    auth_token: "${AGENTOS_TOKEN}"
    timeout: 30
  
  # Marketplace
  marketplace:
    publish: true
    visibility: "private"  # public, private, organization

# ============================================================================
# SECTION 8: MCP Configuration - Model Context Protocol
# ============================================================================
mcp:
  # MCP Server (resources this agent exposes)
  server:
    enabled: true
    
    resources:
      - uri: "agent://data/results"
        name: "Agent Results"
        description: "Recent processing results"
        mime_type: "application/json"
      
      - uri: "agent://status"
        name: "Agent Status"
        description: "Current agent status and metrics"
        mime_type: "application/json"
    
    prompts:
      - name: "summarize"
        description: "Summarize agent results"
        arguments:
          - name: "result_id"
            description: "ID of result to summarize"
            required: true
    
    tools:
      - name: "query_memory"
        description: "Query agent's vector memory"
        input_schema:
          type: "object"
          properties:
            query:
              type: "string"
  
  # MCP Clients (external MCP servers to connect to)
  clients:
    - name: "github-mcp"
      command: "uvx"
      args:
        - "mcp-server-github"
      env:
        GITHUB_TOKEN: "${GITHUB_TOKEN}"
    
    - name: "slack-mcp"
      command: "npx"
      args:
        - "-y"
        - "@modelcontextprotocol/server-slack"
      env:
        SLACK_TOKEN: "${SLACK_TOKEN}"

# ============================================================================
# SECTION 9: Environment Variables - Configuration Injection
# ============================================================================
env:
  # Required variables (agent won't start without these)
  required:
    - OPENAI_API_KEY
    - SEARCH_API_KEY
  
  # Optional variables with defaults
  optional:
    LOG_LEVEL: "INFO"
    CACHE_TTL: "3600"
    MAX_RETRIES: "3"

# ============================================================================
# SECTION 10: Metadata - Agent Information
# ============================================================================
metadata:
  version: "1.0.0"
  author: "Your Name"
  license: "MIT"
  tags:
    - ai
    - assistant
    - research
  
  # Performance metrics
  performance:
    avg_response_time_ms: 500
    success_rate: 0.95
    uptime_days: 30
  
  # Logging configuration
  logging:
    level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: "json"  # json, text
    output: "stdout"  # stdout, file, both
    file_path: "./logs/agent.log"
    rotation: "daily"
    retention_days: 30
```

---

## Manifest Sections Explained

### 1. Persona
Defines agent identity and behavior personality.

**Key Fields:**
- `name`: Agent display name
- `system_prompt`: Core instructions for LLM
- `tone`: Communication style
- `traits`: Behavioral characteristics
- `goals`: Primary objectives

**Example:**
```yaml
persona:
  name: "Research Assistant"
  system_prompt: |
    You are an expert research assistant.
    Always cite sources and verify facts.
  tone: "professional"
  traits: ["thorough", "analytical"]
  goals: ["Provide accurate research"]
```

---

### 2. LLM Configuration
Specifies which models to use and their parameters.

**Supported Providers:**
- `openai` - GPT models
- `anthropic` - Claude models
- `google_gemini` - Gemini models
- `grok` - Grok models
- `ollama` - Local models
- `together` - Together AI
- `openrouter` - OpenRouter aggregator

**Key Parameters:**
- `temperature`: Randomness (0.0 = deterministic, 1.0 = creative)
- `max_tokens`: Maximum response length
- `top_p`: Nucleus sampling parameter

**Example:**
```yaml
llm:
  primary:
    provider: "anthropic"
    model: "claude-3-opus-20240229"
    temperature: 0.3  # Lower for factual tasks
  fallback:
    provider: "openai"
    model: "gpt-4"
```

---

### 3. Tools
Defines agent capabilities with JSON Schema validation.

**Structure:**
- `name`: Tool identifier
- `description`: What the tool does
- `schema`: JSON Schema for input validation
- `implementation`: Python module path
- `config`: Tool-specific settings

**Example:**
```yaml
tools:
  - name: "send_email"
    description: "Send an email message"
    schema:
      type: "object"
      properties:
        to:
          type: "string"
          format: "email"
        subject:
          type: "string"
        body:
          type: "string"
      required: ["to", "subject", "body"]
    implementation: "tools.email_tool"
    config:
      smtp_server: "smtp.gmail.com"
      smtp_port: 587
      from_address: "${EMAIL_FROM}"
```

---

### 4. Memory
Configures state persistence and memory systems.

**Types:**
- **Vector Memory**: Semantic search over past interactions
- **Buffer Memory**: Recent conversation history
- **Persistence**: Save/load agent state

**Example:**
```yaml
memory:
  vector:
    provider: "chroma"
    collection: "research_memory"
    embedding_model: "text-embedding-3-large"
  buffer:
    type: "token_buffer"
    max_tokens: 2000
  persistence: true
```

---

### 5. Workflows
Defines multi-step processes as directed graphs.

**Node Types:**
- `start` / `end`: Entry and exit points
- `agent`: Execute agent logic
- `condition`: Branch based on state
- `checkpoint`: Save state snapshot
- `parallel`: Run nodes concurrently
- `error_handler`: Handle failures

**Edge Conditions:**
- `always`: Always follow
- `on_success`: Only if node succeeds
- `on_failure`: Only if node fails
- `conditional`: Custom condition function

**Example:**
```yaml
workflows:
  - name: "approval_flow"
    nodes:
      - id: "start"
        type: "start"
      - id: "process"
        type: "agent"
        retry:
          max_retries: 3
      - id: "approve"
        type: "checkpoint"
        config:
          manual_approval: true
      - id: "end"
        type: "end"
    edges:
      - from: "start"
        to: "process"
        condition: "always"
      - from: "process"
        to: "approve"
        condition: "on_success"
      - from: "approve"
        to: "end"
```

---

### 6. Governance
Enforces policies, rate limits, and approvals.

**Features:**
- Content filtering (toxicity, PII, plagiarism)
- Rate limiting (per-minute, per-hour, per-day)
- Approval gates for sensitive operations
- Cost controls

**Example:**
```yaml
governance:
  content_filters:
    - type: "pii"
      detect: ["email", "phone"]
      action: "redact"
  rate_limits:
    requests_per_minute: 60
  approval:
    required_for: ["delete_data"]
  cost_controls:
    max_cost_per_day: 100.0
```

---

### 7. AgentOS Integration
Connects agent to external AgentOS system.

**Example:**
```yaml
agentos:
  enabled: true
  events:
    subscribe: ["task.created"]
    publish: ["task.completed"]
  api:
    base_url: "https://agentos.example.com"
```

---

### 8. MCP Configuration
Model Context Protocol for resource exposure and consumption.

**Server**: Resources/prompts this agent exposes  
**Clients**: External MCP servers to connect to

**Example:**
```yaml
mcp:
  server:
    resources:
      - uri: "agent://results"
        mime_type: "application/json"
  clients:
    - name: "github-mcp"
      command: "uvx"
      args: ["mcp-server-github"]
```

---

### 9. Environment Variables
Required and optional configuration from environment.

**Example:**
```yaml
env:
  required:
    - API_KEY
  optional:
    TIMEOUT: "30"
```

---

### 10. Metadata
Agent information and operational settings.

**Example:**
```yaml
metadata:
  version: "2.0.0"
  tags: ["production", "critical"]
  logging:
    level: "INFO"
    format: "json"
```

---

## Loading Manifests in Python

```python
import yaml
from pathlib import Path

def load_agent_manifest(manifest_path: str) -> dict:
    """Load and parse agent manifest."""
    with open(manifest_path, 'r') as f:
        manifest = yaml.safe_load(f)
    
    # Substitute environment variables
    manifest = substitute_env_vars(manifest)
    
    # Validate with Pydantic (optional)
    # manifest = AgentManifestSchema(**manifest)
    
    return manifest

# Usage
manifest = load_agent_manifest("agents/my_agent/agent.yaml")
agent_name = manifest['persona']['name']
llm_provider = manifest['llm']['primary']['provider']
tools = manifest['tools']
```

---

## Best Practices

### ✅ DO
- Use environment variables for secrets (`${VAR_NAME}`)
- Version your manifests (`metadata.version`)
- Include fallback LLM configuration
- Add retry logic to critical nodes
- Use checkpoints for long-running workflows
- Document tools with clear descriptions
- Set appropriate rate limits

### ❌ DON'T
- Hardcode API keys or secrets
- Skip schema validation for tools
- Use very high temperature for factual tasks
- Forget error handlers in workflows
- Set unlimited rate limits
- Ignore cost controls

---

## Common Patterns

### Pattern 1: Simple Agent
```yaml
persona:
  name: "Helper"
llm:
  primary:
    provider: "openai"
    model: "gpt-4"
tools:
  - name: "search"
    schema: {...}
```

### Pattern 2: Workflow Agent
```yaml
workflows:
  - name: "main_flow"
    nodes:
      - {id: start, type: start}
      - {id: process, type: agent}
      - {id: end, type: end}
    edges:
      - {from: start, to: process}
      - {from: process, to: end}
```

### Pattern 3: Multi-Tool Agent
```yaml
tools:
  - name: "search"
  - name: "analyze"
  - name: "report"
governance:
  rate_limits:
    tool_limits:
      search: 100
      report: 10
```

### Pattern 4: Approval-Required Agent
```yaml
workflows:
  - name: "approve_flow"
    nodes:
      - id: "review"
        type: "checkpoint"
        config:
          manual_approval: true
          timeout: 3600
governance:
  approval:
    required_for: ["publish"]
```

---

## Example: Complete Twitter Agent Manifest

See `agents/twitter_agent/agent.yaml` for a production example with:
- Google Gemini LLM for thread generation
- 6 tools (tweet, thread, timeline, engagement, monitor)
- 9-node workflow with approval gate
- Rate limiting (15/min, 50/hour, 10/day)
- MCP server with timeline/analytics resources

---

## Example: Complete Blog Agent Manifest

See `agents/blog_agent/agent.yaml` for a complex example with:
- Claude 3.5 Sonnet + GPT-4 fallback
- 5 tools (research, outline, write, review, publish)
- 15-node workflow with parallel execution
- Quality check with conditional looping
- Manual approval gate before publishing
- Plagiarism detection
- Hybrid memory (vector + buffer)

---

## Validation

Coming soon: `agentosx.manifest.validator` module for:
- Schema validation with Pydantic
- Environment variable checking
- Workflow graph validation (no cycles, connected)
- Tool schema validation (valid JSON Schema)
- Cost estimation based on config

---

## Migration from agentOS

When migrating agents from agentOS:

1. **Extract configuration** from Python code to YAML
2. **Map tools** to manifest tool schema
3. **Define workflows** if multi-step process
4. **Add governance** (rate limits, approvals)
5. **Configure MCP** for resource exposure
6. **Test** with new framework

Example migrations:
- ✅ Twitter agent: Complete
- 🟡 Blog agent: Manifest complete, implementation pending

---

## Next Steps

- **Use Template**: Copy `agents/_template/agent.yaml`
- **Customize**: Modify for your use case
- **Validate**: Ensure schema correctness
- **Test**: Run with `examples/orchestration_examples.py`
- **Deploy**: Load manifest in production

---

**For More Examples:**
- `agents/_template/agent.yaml` - Complete schema reference
- `agents/twitter_agent/agent.yaml` - Production Twitter agent
- `agents/blog_agent/agent.yaml` - Complex workflow example
