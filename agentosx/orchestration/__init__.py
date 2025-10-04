"""
Multi-Agent Orchestration System

Provides multiple patterns for agent coordination:
- Swarm-style handoffs for lightweight delegation
- CrewAI-style teams for role-based collaboration
- LangGraph-style workflows for DAG-based execution
- Message bus for event-driven coordination
"""

from .coordinator import Coordinator
from .handoff import HandoffManager, HandoffContext
from .crew import Crew, CrewMember, TaskQueue
from .graph import WorkflowGraph, WorkflowNode, WorkflowEdge
from .message_bus import MessageBus, Message, MessageHandler

__all__ = [
    "Coordinator",
    "HandoffManager",
    "HandoffContext",
    "Crew",
    "CrewMember",
    "TaskQueue",
    "WorkflowGraph",
    "WorkflowNode",
    "WorkflowEdge",
    "MessageBus",
    "Message",
    "MessageHandler",
]
