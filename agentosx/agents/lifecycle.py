"""
Agent Lifecycle Management.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class LifecyclePhase(Enum):
    """Lifecycle phases."""
    INITIALIZING = "initializing"
    READY = "ready"
    STARTING = "starting"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class LifecycleManager:
    """
    Manager for agent lifecycle.
    
    Coordinates state transitions and lifecycle hooks.
    """
    
    def __init__(self):
        """Initialize lifecycle manager."""
        self.phase = LifecyclePhase.INITIALIZING
        self._transition_handlers: dict[str, List[Callable]] = {}
    
    def register_transition_handler(
        self,
        from_phase: LifecyclePhase,
        to_phase: LifecyclePhase,
        handler: Callable
    ):
        """
        Register a handler for phase transitions.
        
        Args:
            from_phase: Source phase
            to_phase: Target phase
            handler: Handler function
        """
        key = f"{from_phase.value}->{to_phase.value}"
        if key not in self._transition_handlers:
            self._transition_handlers[key] = []
        self._transition_handlers[key].append(handler)
    
    async def transition(self, to_phase: LifecyclePhase):
        """
        Transition to a new phase.
        
        Args:
            to_phase: Target phase
        """
        from_phase = self.phase
        key = f"{from_phase.value}->{to_phase.value}"
        
        # Run transition handlers
        for handler in self._transition_handlers.get(key, []):
            try:
                await handler()
            except Exception as e:
                logger.error(f"Transition handler error: {e}", exc_info=True)
        
        self.phase = to_phase
        logger.info(f"Transitioned: {from_phase.value} -> {to_phase.value}")
