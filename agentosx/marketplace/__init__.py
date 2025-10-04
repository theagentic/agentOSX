"""
AgentOSX Marketplace

Provides infrastructure for publishing, discovering, and installing agents
from the agentOS marketplace.
"""

from .registry import RegistryClient
from .publisher import AgentPublisher
from .installer import AgentInstaller
from .versioning import VersionManager

__all__ = [
    "RegistryClient",
    "AgentPublisher",
    "AgentInstaller",
    "VersionManager",
]
