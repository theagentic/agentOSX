# AgentOSX Quick Reference

## Orchestration Patterns

### Swarm Handoffs (Lightweight Delegation)

```python
from agentosx.orchestration import Coordinator, HandoffManager, HandoffContext

# Setup
coordinator = Coordinator()
handoff_manager = HandoffManager(coordinator)

# Simple handoff
result = await handoff_manager.handoff(
    from_agent_id="agent1",
    to_agent_id="agent2",
    input="Do task X"
)

# With context preservation
context = HandoffContext(
    handoff_id="chain_1",
    from_agent="agent1",
    to_agent="agent2",
    input="Do task X"
)
result = await handoff_manager.handoff(
    from_agent_id="agent1",
    to_agent_id="agent2",
    input="Do task X",
    context=context,
    return_to_caller=True
)

# Auto-routing
def route_by_keyword(ctx: HandoffContext) -> str:
    if "research" in ctx.input.lower():
        return "research_agent"
    return "writer_agent"

handoff_manager.register_handoff_rule(route_by_keyword)
result = await handoff_manager.auto_handoff(
    from_agent_id="coordinator",
    input="research AI trends"
)
```

**Use Cases:** Simple agent-to-agent task delegation, sequential processing

---

### CrewAI Teams (Role-Based Collaboration)

```python
from agentosx.orchestration import Crew, CrewRole, ExecutionMode

# Create crew
crew = Crew(name="content-team", manager_id="manager")

# Add members with roles
await crew.add_member("manager", manager_agent, CrewRole.MANAGER)
await crew.add_member("researcher", research_agent, CrewRole.WORKER, ["research"])
await crew.add_member("writer", writer_agent, CrewRole.WORKER, ["writing"])
await crew.add_member("editor", editor_agent, CrewRole.REVIEWER, ["review"])

# Add tasks with dependencies
await crew.add_task("Research topic X", priority=2)
await crew.add_task("Write draft", priority=1, dependencies=["task_0_1"])
await crew.add_task("Review content", priority=0, dependencies=["task_1_1"])

# Execute
results = await crew.execute(mode=ExecutionMode.SEQUENTIAL)
# ExecutionMode.SEQUENTIAL - One at a time
# ExecutionMode.PARALLEL - All at once
# ExecutionMode.HIERARCHICAL - Manager delegates

# Access shared memory
memory = await crew.get_shared_memory()
await crew.update_shared_memory("key", "value")
```

**Use Cases:** Team-based work, role-based task distribution, hierarchical delegation

---

### LangGraph Workflows (DAG Execution)

```python
from agentosx.orchestration import WorkflowGraph, NodeType, EdgeCondition

# Create workflow
workflow = WorkflowGraph("content-pipeline", coordinator)

# Define nodes
workflow.add_node("start", NodeType.START)

workflow.add_node("research", NodeType.AGENT, 
    agent_id="research_agent",
    config={
        "input_template": "Research: {topic}",
        "output_key": "research_data"
    },
    retry_config={"max_retries": 3, "retry_delay": 1.0}
)

workflow.add_node("checkpoint1", NodeType.CHECKPOINT)

workflow.add_node("write", NodeType.AGENT,
    agent_id="writer_agent", 
    config={
        "input_template": "Write from: {research_data}",
        "output_key": "draft"
    }
)

workflow.add_node("quality_check", NodeType.CONDITION,
    config={
        "condition": lambda state: state.variables.get("quality", 0) > 0.8,
        "output_key": "passes_quality"
    }
)

workflow.add_node("approve", NodeType.CHECKPOINT,
    config={
        "name": "awaiting_approval",
        "manual_approval": True,
        "timeout": 3600
    }
)

workflow.add_node("parallel_publish", NodeType.PARALLEL,
    config={
        "nodes": ["publish_blog", "publish_social", "publish_email"]
    }
)

workflow.add_node("error_handler", NodeType.ERROR_HANDLER,
    config={
        "retry": True,
        "fallback_node": "start"
    }
)

workflow.add_node("end", NodeType.END)

# Define edges
workflow.add_edge("start", "research", EdgeCondition.ALWAYS)
workflow.add_edge("research", "checkpoint1", EdgeCondition.ON_SUCCESS)
workflow.add_edge("checkpoint1", "write", EdgeCondition.ALWAYS)
workflow.add_edge("write", "quality_check", EdgeCondition.ON_SUCCESS)
workflow.add_edge("quality_check", "approve", EdgeCondition.CONDITIONAL,
    condition_func=lambda state: state.variables.get("passes_quality", False))
workflow.add_edge("quality_check", "write", EdgeCondition.CONDITIONAL,
    condition_func=lambda state: not state.variables.get("passes_quality", True))
workflow.add_edge("approve", "parallel_publish", EdgeCondition.ON_SUCCESS)
workflow.add_edge("parallel_publish", "end", EdgeCondition.ALWAYS)
workflow.add_edge("research", "error_handler", EdgeCondition.ON_FAILURE)

# Execute
state = await workflow.execute(
    input="AI trends 2025",
    initial_state={"author": "AgentOSX", "quality_threshold": 0.8}
)

# Resume from checkpoint
state = await workflow.execute(
    input="AI trends 2025",
    checkpoint_id="checkpoint_123"
)
```

**Use Cases:** Complex multi-step processes, conditional branching, parallel execution, checkpointing

---

### Message Bus (Event-Driven Coordination)

```python
from agentosx.orchestration import MessageBus, MessagePriority

# Create and start bus
bus = MessageBus(name="agent-bus")
await bus.start()

# Subscribe to topics
async def task_handler(message):
    print(f"Received: {message.payload}")

await bus.subscribe("tasks.created", "handler1", task_handler)
await bus.subscribe("tasks.*", "logger", logger_handler)  # Wildcard

# Publish messages
await bus.publish(
    topic="tasks.created",
    sender="agent1",
    payload={"task_id": "123", "description": "Research"},
    priority=MessagePriority.HIGH
)

# Get handler stats
stats = bus.get_handler_stats("handler1")
print(f"Messages handled: {stats['message_count']}")

# Forward to agentOS
bus.enable_agentos_forwarding(agentos_client)

await bus.stop()
```

**Use Cases:** Event-driven coordination, monitoring, decoupled agent communication

---

## Agent Manifest Cheat Sheet

### Minimal Manifest

```yaml
persona:
  name: "My Agent"

llm:
  primary:
    provider: "openai"
    model: "gpt-4"

tools:
  - name: "my_tool"
    schema:
      type: "object"
      properties:
        input: {type: "string"}
    implementation: "tools.my_tool"
```

### Full Manifest Sections

```yaml
persona:           # Agent identity
llm:               # Model configuration
tools:             # Agent capabilities
memory:            # State persistence
workflows:         # Multi-step processes
governance:        # Policies and controls
agentos:           # External system integration
mcp:               # MCP server/client config
env:               # Environment variables
metadata:          # Agent information
```

### Common Tool Schema

```yaml
tools:
  - name: "search"
    description: "Search for information"
    schema:
      type: "object"
      properties:
        query:
          type: "string"
          description: "Search query"
        max_results:
          type: "integer"
          default: 10
      required: ["query"]
    implementation: "tools.search_tool"
    config:
      api_key: "${SEARCH_API_KEY}"
      timeout: 30
```

### Workflow Node Types

```yaml
workflows:
  - name: "my_workflow"
    nodes:
      - id: "start"
        type: "start"            # Entry point
      
      - id: "agent1"
        type: "agent"            # Execute agent
        agent_id: "agent1"
      
      - id: "condition"
        type: "condition"        # Branch based on state
        config:
          condition: "x > 10"
      
      - id: "checkpoint"
        type: "checkpoint"       # Save state
        config:
          manual_approval: true
      
      - id: "parallel"
        type: "parallel"         # Execute concurrently
        config:
          nodes: ["task1", "task2"]
      
      - id: "error"
        type: "error_handler"    # Handle failures
      
      - id: "end"
        type: "end"              # Exit point
```

### Edge Conditions

```yaml
edges:
  - from: "node1"
    to: "node2"
    condition: "always"          # Always follow
  
  - from: "node1"
    to: "node3"
    condition: "on_success"      # Only if success
  
  - from: "node1"
    to: "error"
    condition: "on_failure"      # Only if failed
  
  - from: "condition"
    to: "node4"
    condition: "conditional"     # Custom condition
    condition_func: "lambda state: state.x > 10"
```

---

## Common Code Patterns

### Pattern 1: Simple Agent with Handoff

```python
from agentosx.orchestration import Coordinator, HandoffManager

coordinator = Coordinator()
await coordinator.register_agent("agent1", agent1)
await coordinator.register_agent("agent2", agent2)

handoff = HandoffManager(coordinator)
result = await handoff.handoff("agent1", "agent2", "Do task")
```

### Pattern 2: Team with Shared Memory

```python
from agentosx.orchestration import Crew, CrewRole

crew = Crew("team")
await crew.add_member("worker1", agent1, CrewRole.WORKER)
await crew.add_member("worker2", agent2, CrewRole.WORKER)
await crew.add_task("Task 1")
await crew.add_task("Task 2")

results = await crew.execute()
memory = await crew.get_shared_memory()
```

### Pattern 3: Workflow with Checkpoint

```python
from agentosx.orchestration import WorkflowGraph, NodeType

workflow = WorkflowGraph("flow", coordinator)
workflow.add_node("start", NodeType.START)
workflow.add_node("process", NodeType.AGENT, agent_id="agent1")
workflow.add_node("checkpoint", NodeType.CHECKPOINT)
workflow.add_node("end", NodeType.END)

workflow.add_edge("start", "process")
workflow.add_edge("process", "checkpoint")
workflow.add_edge("checkpoint", "end")

state = await workflow.execute(input="data")
```

### Pattern 4: Event-Driven Coordination

```python
from agentosx.orchestration import MessageBus

bus = MessageBus()
await bus.start()

async def on_task_complete(msg):
    # Trigger next agent
    await next_agent.process(msg.payload)

await bus.subscribe("task.completed", "handler", on_task_complete)
await bus.publish("task.completed", "agent1", {"result": "done"})
```

### Pattern 5: Combined Orchestration

```python
# Use coordinator to manage everything
coordinator = Coordinator()
handoff = HandoffManager(coordinator)
workflow = WorkflowGraph("flow", coordinator)
bus = MessageBus()

# Register orchestrators
await coordinator.register_orchestrator("handoff", handoff)
await coordinator.register_orchestrator("workflow", workflow)

# Subscribe to orchestration events
async def on_handoff(event):
    await bus.publish("agent.handoff", "coord", event)

await coordinator.subscribe("handoff_complete", on_handoff)
```

---

## Decision Matrix

### Choose Swarm Handoffs When:
- ✅ Simple agent-to-agent delegation
- ✅ Sequential processing
- ✅ Need to preserve conversation context
- ✅ Return-to-caller required
- ❌ Complex branching logic
- ❌ Parallel execution needed

### Choose CrewAI Teams When:
- ✅ Role-based collaboration
- ✅ Task queue management
- ✅ Shared memory required
- ✅ Hierarchical delegation
- ✅ Priority-based execution
- ❌ Complex conditional logic
- ❌ State checkpointing needed

### Choose LangGraph Workflows When:
- ✅ Complex multi-step processes
- ✅ Conditional branching
- ✅ Parallel execution
- ✅ State checkpointing required
- ✅ Error recovery with retry
- ✅ Manual approval gates
- ❌ Simple linear processes
- ❌ Overkill for 2-3 steps

### Choose Message Bus When:
- ✅ Decoupled coordination
- ✅ Event-driven architecture
- ✅ Monitoring/logging
- ✅ Multiple subscribers per event
- ✅ Priority-based processing
- ❌ Synchronous response needed
- ❌ Direct agent communication sufficient

---

## Performance Tips

1. **Handoffs**: Use context serialization for persistence across restarts
2. **Crews**: Use PARALLEL mode for independent tasks
3. **Workflows**: Add checkpoints before expensive operations
4. **Message Bus**: Use message filtering to reduce handler overhead
5. **All Patterns**: Enable async logging to avoid blocking

---

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Workflow State

```python
state = await workflow.execute(input="data")
print(f"Variables: {state.variables}")
print(f"History: {state.history}")
print(f"Checkpoints: {state.checkpoints}")
print(f"Error: {state.error}")
```

### Monitor Message Bus

```python
# Subscribe to all messages
await bus.subscribe("*", "debug", lambda m: print(f"[BUS] {m.topic}: {m.payload}"))
```

### Track Crew Progress

```python
results = await crew.execute()
for task in results['tasks']:
    print(f"Task {task['task_id']}: {task['status']}")
```

---

## Examples Location

- **Full orchestration examples**: `examples/orchestration_examples.py`
- **Twitter agent**: `agents/twitter_agent/`
- **Blog agent manifest**: `agents/blog_agent/agent.yaml`
- **Agent template**: `agents/_template/`

---

## Documentation

- **Phase 2 Status**: [PHASE2_COMPLETE.md](PHASE2_COMPLETE.md)
- **Manifest Guide**: [AGENT_MANIFEST_GUIDE.md](AGENT_MANIFEST_GUIDE.md)
- **Project Plan**: [PLAN.md](PLAN.md)
- **Requirements**: [PRD.md](PRD.md)
