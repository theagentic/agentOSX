"""
Agent State Management.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class StateSnapshot:
    """Snapshot of agent state at a point in time."""
    timestamp: datetime
    context: Dict[str, Any]
    memory: Dict[str, Any]
    metadata: Dict[str, Any]


class StateManager:
    """
    Manager for agent state with checkpointing support.
    
    Provides state persistence, versioning, and rollback capabilities.
    """
    
    def __init__(self):
        """Initialize state manager."""
        self.current_state: Dict[str, Any] = {}
        self._snapshots: List[StateSnapshot] = []
        self._max_snapshots = 10
    
    def update(self, key: str, value: Any):
        """
        Update state value.
        
        Args:
            key: State key
            value: State value
        """
        self.current_state[key] = value
        logger.debug(f"Updated state: {key}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get state value.
        
        Args:
            key: State key
            default: Default value if key not found
            
        Returns:
            State value
        """
        return self.current_state.get(key, default)
    
    def snapshot(self):
        """Create a state snapshot."""
        snapshot = StateSnapshot(
            timestamp=datetime.now(),
            context=self.current_state.copy(),
            memory={},
            metadata={}
        )
        
        self._snapshots.append(snapshot)
        
        # Limit snapshots
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots.pop(0)
        
        logger.debug("Created state snapshot")
    
    def restore(self, index: int = -1):
        """
        Restore state from snapshot.
        
        Args:
            index: Snapshot index (-1 for most recent)
        """
        if not self._snapshots:
            raise ValueError("No snapshots available")
        
        snapshot = self._snapshots[index]
        self.current_state = snapshot.context.copy()
        
        logger.info(f"Restored state from snapshot: {snapshot.timestamp}")
    
    def clear(self):
        """Clear all state."""
        self.current_state.clear()
        self._snapshots.clear()
        logger.debug("Cleared agent state")
