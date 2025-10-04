"""
Multi-Agent Orchestration Examples

Demonstrates all orchestration patterns:
1. Swarm-style handoffs
2. CrewAI-style teams
3. LangGraph-style workflows
4. Message bus coordination
"""

import asyncio
import logging
from agentosx.orchestration import (
    Coordinator,
    HandoffManager, HandoffContext,
    Crew, CrewRole,
    WorkflowGraph, NodeType, EdgeCondition,
    MessageBus, MessagePriority
)
from agentosx.agents.base import BaseAgent, ExecutionContext


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Simple Test Agents
# ============================================================================

class ResearchAgent(BaseAgent):
    """Agent that researches topics."""
    
    def __init__(self):
        super().__init__()
        self.name = "research-agent"
    
    async def process(self, input: str, context: ExecutionContext = None) -> str:
        await asyncio.sleep(0.5)  # Simulate work
        return f"Research results for '{input}': [Data gathered]"


class WriterAgent(BaseAgent):
    """Agent that writes content."""
    
    def __init__(self):
        super().__init__()
        self.name = "writer-agent"
    
    async def process(self, input: str, context: ExecutionContext = None) -> str:
        await asyncio.sleep(0.5)
        return f"Written content based on: {input}"


class EditorAgent(BaseAgent):
    """Agent that reviews content."""
    
    def __init__(self):
        super().__init__()
        self.name = "editor-agent"
    
    async def process(self, input: str, context: ExecutionContext = None) -> str:
        await asyncio.sleep(0.3)
        return f"Reviewed and approved: {input}"


# ============================================================================
# Example 1: Swarm-style Handoffs
# ============================================================================

async def example_swarm_handoffs():
    """Demonstrate lightweight agent-to-agent handoffs."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Swarm-style Handoffs")
    print("="*80 + "\n")
    
    # Setup
    coordinator = Coordinator()
    handoff_manager = HandoffManager(coordinator)
    
    # Register agents
    research_agent = ResearchAgent()
    writer_agent = WriterAgent()
    editor_agent = EditorAgent()
    
    await coordinator.register_agent("research", research_agent, ["research", "analysis"])
    await coordinator.register_agent("writer", writer_agent, ["writing", "content"])
    await coordinator.register_agent("editor", editor_agent, ["review", "editing"])
    
    print("✓ Registered 3 agents with coordinator\n")
    
    # Example 1a: Simple handoff
    print("1a. Simple handoff: research -> writer")
    result = await handoff_manager.handoff(
        from_agent_id="research",
        to_agent_id="writer",
        input="AI trends 2025"
    )
    print(f"   Result: {result.result}")
    print(f"   Status: {result.status.value}")
    print(f"   Time: {result.execution_time:.2f}s\n")
    
    # Example 1b: Chain handoffs with context preservation
    print("1b. Chain handoffs: research -> writer -> editor")
    
    # First handoff with context
    context = HandoffContext(
        handoff_id="chain_1",
        from_agent="research",
        to_agent="writer",
        input="AI trends 2025"
    )
    
    result1 = await handoff_manager.handoff(
        from_agent_id="research",
        to_agent_id="writer",
        input="AI trends 2025",
        context=context
    )
    print(f"   Step 1 (research->writer): {result1.status.value}")
    
    # Second handoff using same context
    result2 = await handoff_manager.handoff(
        from_agent_id="writer",
        to_agent_id="editor",
        input=str(result1.result),
        context=context
    )
    print(f"   Step 2 (writer->editor): {result2.status.value}")
    print(f"   Final result: {result2.result}")
    print(f"   Context history entries: {len(context.conversation_history)}\n")
    
    # Example 1c: Conditional handoff with rules
    print("1c. Conditional handoff with routing rules")
    
    def route_by_keyword(context: HandoffContext) -> str:
        """Route based on input keywords."""
        if "research" in context.input.lower():
            return "research"
        elif "write" in context.input.lower():
            return "writer"
        return None
    
    handoff_manager.register_handoff_rule(route_by_keyword)
    
    result = await handoff_manager.auto_handoff(
        from_agent_id="coordinator",
        input="research quantum computing"
    )
    print(f"   Auto-routed to: {result.final_agent}")
    print(f"   Result: {result.result}\n")
    
    await coordinator.shutdown()


# ============================================================================
# Example 2: CrewAI-style Teams
# ============================================================================

async def example_crew_teams():
    """Demonstrate role-based team collaboration."""
    print("\n" + "="*80)
    print("EXAMPLE 2: CrewAI-style Teams")
    print("="*80 + "\n")
    
    # Create crew
    crew = Crew(name="content-crew", manager_id="manager")
    
    # Add members with roles
    manager_agent = BaseAgent()
    manager_agent.name = "manager"
    research_agent = ResearchAgent()
    writer_agent = WriterAgent()
    editor_agent = EditorAgent()
    
    await crew.add_member("manager", manager_agent, CrewRole.MANAGER)
    await crew.add_member("research", research_agent, CrewRole.WORKER, ["research"])
    await crew.add_member("writer", writer_agent, CrewRole.WORKER, ["writing"])
    await crew.add_member("editor", editor_agent, CrewRole.REVIEWER, ["review"])
    
    print("✓ Created crew with 4 members (1 manager, 2 workers, 1 reviewer)\n")
    
    # Add tasks
    print("Adding tasks to queue...")
    await crew.add_task("Research AI trends", priority=2)
    await crew.add_task("Write blog post", priority=1, dependencies=["task_0_1"])
    await crew.add_task("Review content", priority=0, dependencies=["task_1_1"])
    print("✓ Added 3 tasks with dependencies\n")
    
    # Execute sequentially
    print("Executing tasks sequentially...")
    from agentosx.orchestration.crew import ExecutionMode
    results = await crew.execute(mode=ExecutionMode.SEQUENTIAL)
    
    print(f"\n✓ Execution complete!")
    print(f"   Status: {results['status']}")
    print(f"   Duration: {results['duration']:.2f}s")
    print(f"   Tasks completed: {len([t for t in results['tasks'] if t['status'] == 'completed'])}")
    
    # Show shared memory
    memory = await crew.get_shared_memory()
    print(f"   Shared memory entries: {len(memory)}\n")


# ============================================================================
# Example 3: LangGraph-style Workflows
# ============================================================================

async def example_workflow_graph():
    """Demonstrate DAG-based workflow execution."""
    print("\n" + "="*80)
    print("EXAMPLE 3: LangGraph-style Workflows")
    print("="*80 + "\n")
    
    # Setup coordinator
    coordinator = Coordinator()
    research_agent = ResearchAgent()
    writer_agent = WriterAgent()
    editor_agent = EditorAgent()
    
    await coordinator.register_agent("research", research_agent)
    await coordinator.register_agent("writer", writer_agent)
    await coordinator.register_agent("editor", editor_agent)
    
    # Build workflow graph
    workflow = WorkflowGraph("content-pipeline", coordinator)
    
    # Define nodes
    workflow.add_node("start", NodeType.START)
    workflow.add_node("research", NodeType.AGENT, agent_id="research",
                     config={"input_template": "Research: {input}", "output_key": "research_data"})
    workflow.add_node("checkpoint", NodeType.CHECKPOINT)
    workflow.add_node("write", NodeType.AGENT, agent_id="writer",
                     config={"input_template": "Write from: {research_data}", "output_key": "draft"})
    workflow.add_node("review", NodeType.AGENT, agent_id="editor",
                     config={"input_template": "Review: {draft}", "output_key": "final"})
    workflow.add_node("end", NodeType.END)
    
    # Define edges
    workflow.add_edge("start", "research", EdgeCondition.ALWAYS)
    workflow.add_edge("research", "checkpoint", EdgeCondition.ON_SUCCESS)
    workflow.add_edge("checkpoint", "write", EdgeCondition.ALWAYS)
    workflow.add_edge("write", "review", EdgeCondition.ON_SUCCESS)
    workflow.add_edge("review", "end", EdgeCondition.ALWAYS)
    
    print("✓ Built workflow graph with 6 nodes and 5 edges\n")
    
    # Execute workflow
    print("Executing workflow...")
    state = await workflow.execute(
        input="AI trends 2025",
        initial_state={"author": "AgentOSX"}
    )
    
    print(f"\n✓ Workflow execution complete!")
    print(f"   Steps: {len(state.history)}")
    print(f"   Checkpoints: {len(state.checkpoints)}")
    print(f"   Final variables: {list(state.variables.keys())}")
    print(f"   Status: {'Success' if not state.error else 'Failed'}\n")
    
    # Show execution history
    print("Execution trace:")
    for i, entry in enumerate(state.history, 1):
        print(f"   {i}. {entry['node_id']}")
    
    await coordinator.shutdown()


# ============================================================================
# Example 4: Message Bus Coordination
# ============================================================================

async def example_message_bus():
    """Demonstrate event-driven coordination."""
    print("\n" + "="*80)
    print("EXAMPLE 4: Message Bus Coordination")
    print("="*80 + "\n")
    
    # Create message bus
    bus = MessageBus(name="agent-bus")
    await bus.start()
    print("✓ Started message bus\n")
    
    # Create handlers
    research_messages = []
    writer_messages = []
    
    async def research_handler(message):
        research_messages.append(message)
        print(f"   [Research] Received: {message.payload.get('task')}")
    
    async def writer_handler(message):
        writer_messages.append(message)
        print(f"   [Writer] Received: {message.payload.get('task')}")
    
    # Subscribe to topics
    await bus.subscribe("tasks.research", "research_agent", research_handler)
    await bus.subscribe("tasks.write", "writer_agent", writer_handler)
    await bus.subscribe("tasks.*", "logger", lambda m: print(f"   [Logger] {m.topic}: {m.payload}"))
    
    print("✓ Subscribed 3 handlers to topics\n")
    
    # Publish messages
    print("Publishing messages...")
    await bus.publish(
        topic="tasks.research",
        sender="coordinator",
        payload={"task": "Research AI trends"},
        priority=MessagePriority.HIGH
    )
    
    await bus.publish(
        topic="tasks.write",
        sender="coordinator",
        payload={"task": "Write blog post"},
        priority=MessagePriority.NORMAL
    )
    
    await bus.publish(
        topic="tasks.research",
        sender="coordinator",
        payload={"task": "Analyze data"},
        priority=MessagePriority.LOW
    )
    
    # Give handlers time to process
    await asyncio.sleep(0.5)
    
    print(f"\n✓ Messages processed!")
    print(f"   Research agent handled: {len(research_messages)} messages")
    print(f"   Writer agent handled: {len(writer_messages)} messages")
    
    # Show statistics
    stats = bus.get_handler_stats("research_agent")
    print(f"   Research agent stats: {stats['message_count']} messages\n")
    
    await bus.stop()


# ============================================================================
# Example 5: Combined Orchestration
# ============================================================================

async def example_combined_orchestration():
    """Demonstrate using multiple patterns together."""
    print("\n" + "="*80)
    print("EXAMPLE 5: Combined Orchestration Patterns")
    print("="*80 + "\n")
    
    # Setup
    coordinator = Coordinator()
    handoff_manager = HandoffManager(coordinator)
    message_bus = MessageBus("orchestration-bus")
    await message_bus.start()
    
    # Register agents
    research_agent = ResearchAgent()
    writer_agent = WriterAgent()
    
    await coordinator.register_agent("research", research_agent)
    await coordinator.register_agent("writer", writer_agent)
    
    # Subscribe to events
    events = []
    async def event_logger(message):
        events.append(message)
        print(f"   [Event] {message.topic}: {message.payload.get('action')}")
    
    await message_bus.subscribe("agent.*", "logger", event_logger)
    
    print("✓ Setup complete with coordinator, handoff manager, and message bus\n")
    
    # Scenario: Research task with event notifications
    print("Executing combined workflow...")
    
    # Publish start event
    await message_bus.publish(
        "agent.task.started",
        "coordinator",
        {"action": "Starting research task", "task_id": "task_1"}
    )
    
    # Execute handoff
    result = await handoff_manager.handoff(
        from_agent_id="coordinator",
        to_agent_id="research",
        input="Research quantum computing"
    )
    
    # Publish completion event
    await message_bus.publish(
        "agent.task.completed",
        "research",
        {"action": "Research completed", "task_id": "task_1", "result": str(result.result)}
    )
    
    await asyncio.sleep(0.3)
    
    print(f"\n✓ Combined orchestration complete!")
    print(f"   Handoff status: {result.status.value}")
    print(f"   Events published: {len(events)}\n")
    
    await message_bus.stop()
    await coordinator.shutdown()


# ============================================================================
# Main
# ============================================================================

async def main():
    """Run all orchestration examples."""
    print("\n" + "="*80)
    print("AGENTOSX MULTI-AGENT ORCHESTRATION EXAMPLES")
    print("="*80)
    
    # Run examples
    await example_swarm_handoffs()
    await example_crew_teams()
    await example_workflow_graph()
    await example_message_bus()
    await example_combined_orchestration()
    
    print("\n" + "="*80)
    print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
