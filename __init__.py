"""
agentOS: Production-ready Python agent framework.

A plugin-first, multi-provider agent runtime with social integrations,
policy governance, workflows, and observability.
"""

__version__ = "0.1.0"
__author__ = "AgentOS Team"

# Core exports
from .settings import settings
from .core.llm.base import Message, Role, Tool, ToolCall
from .core.llm.router import Router
from .core.policy.approvals import approval_manager, ApprovalStatus, RiskLevel

__all__ = [
    "settings",
    "Message",
    "Role", 
    "Tool",
    "ToolCall",
    "Router",
    "approval_manager",
    "ApprovalStatus",
    "RiskLevel",
]
