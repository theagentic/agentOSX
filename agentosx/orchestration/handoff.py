"""
Swarm-style Agent Handoffs

Lightweight agent-to-agent delegation with context preservation.
Inspired by OpenAI Swarm pattern for dynamic agent routing.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class HandoffStatus(Enum):
    """Handoff execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class HandoffContext:
    """
    Context transferred between agents during handoff.
    Preserves conversation history and execution state.
    """
    handoff_id: str
    from_agent: str
    to_agent: str
    input: str
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    shared_memory: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add a message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
    
    def get_last_message(self) -> Optional[Dict[str, Any]]:
        """Get the last message from history."""
        return self.conversation_history[-1] if self.conversation_history else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HandoffContext":
        """Create from dictionary."""
        if isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)
    
    def serialize(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def deserialize(cls, json_str: str) -> "HandoffContext":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class HandoffResult:
    """Result of a handoff execution."""
    handoff_id: str
    status: HandoffStatus
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    returned_to_caller: bool = False
    final_agent: str = None
    

class HandoffManager:
    """
    Manages agent-to-agent handoffs with context preservation.
    
    Supports:
    - Direct handoff: Agent A -> Agent B
    - Conditional handoff: Based on input/context
    - Return control: Agent B -> Agent A (original caller)
    - Chain handoffs: Agent A -> B -> C
    """
    
    def __init__(self, coordinator=None):
        """
        Initialize handoff manager.
        
        Args:
            coordinator: Central coordinator instance
        """
        self.coordinator = coordinator
        self._handoff_history: Dict[str, HandoffContext] = {}
        self._active_handoffs: Dict[str, HandoffContext] = {}
        self._handoff_rules: List[Callable] = []
        self._lock = asyncio.Lock()
    
    def register_handoff_rule(self, rule: Callable[[HandoffContext], Optional[str]]):
        """
        Register a handoff rule for automatic routing.
        
        Args:
            rule: Function that takes HandoffContext and returns target agent ID or None
        """
        self._handoff_rules.append(rule)
        logger.info(f"Registered handoff rule: {rule.__name__}")
    
    async def handoff(
        self,
        from_agent_id: str,
        to_agent_id: str,
        input: str,
        context: HandoffContext = None,
        return_to_caller: bool = False
    ) -> HandoffResult:
        """
        Execute a handoff from one agent to another.
        
        Args:
            from_agent_id: Source agent ID
            to_agent_id: Target agent ID
            input: Input for target agent
            context: Existing context or None to create new
            return_to_caller: Whether to return control to original caller
            
        Returns:
            HandoffResult with execution details
        """
        start_time = asyncio.get_event_loop().time()
        
        # Create or update context
        if context is None:
            handoff_id = f"handoff_{from_agent_id}_to_{to_agent_id}_{int(datetime.now().timestamp())}"
            context = HandoffContext(
                handoff_id=handoff_id,
                from_agent=from_agent_id,
                to_agent=to_agent_id,
                input=input
            )
        else:
            # Update context for new handoff
            context.from_agent = from_agent_id
            context.to_agent = to_agent_id
            context.input = input
        
        # Add handoff message to history
        context.add_message(
            "system",
            f"Handoff from {from_agent_id} to {to_agent_id}",
            {"return_to_caller": return_to_caller}
        )
        
        async with self._lock:
            self._active_handoffs[context.handoff_id] = context
        
        logger.info(f"Executing handoff: {from_agent_id} -> {to_agent_id}")
        
        try:
            # Get target agent
            if self.coordinator:
                target_agent = self.coordinator.get_agent(to_agent_id)
            else:
                raise ValueError("No coordinator available")
            
            if not target_agent:
                raise ValueError(f"Target agent not found: {to_agent_id}")
            
            # Execute target agent with context
            from agentosx.agents.base import ExecutionContext
            exec_context = ExecutionContext(
                input=input,
                session_id=context.handoff_id,
                metadata={
                    "handoff_context": context.to_dict(),
                    "return_to_caller": return_to_caller
                }
            )
            
            # Add context to target agent
            target_agent.set_context(exec_context)
            
            # Execute
            result = await target_agent.process(input, exec_context)
            
            # Add result to context
            context.add_message("assistant", str(result), {"agent": to_agent_id})
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Store in history
            async with self._lock:
                self._handoff_history[context.handoff_id] = context
                if context.handoff_id in self._active_handoffs:
                    del self._active_handoffs[context.handoff_id]
            
            # Handle return to caller
            final_agent = to_agent_id
            if return_to_caller and len(context.conversation_history) > 1:
                # Find original caller
                for msg in context.conversation_history:
                    if msg.get("role") == "system" and "Handoff from" in msg.get("content", ""):
                        parts = msg["content"].split("from ")[1].split(" to ")
                        original_caller = parts[0]
                        if original_caller != from_agent_id:
                            # Return control
                            logger.info(f"Returning control to original caller: {original_caller}")
                            final_agent = original_caller
                            break
            
            return HandoffResult(
                handoff_id=context.handoff_id,
                status=HandoffStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                returned_to_caller=return_to_caller,
                final_agent=final_agent
            )
            
        except Exception as e:
            logger.error(f"Handoff failed: {e}")
            
            async with self._lock:
                if context.handoff_id in self._active_handoffs:
                    del self._active_handoffs[context.handoff_id]
            
            return HandoffResult(
                handoff_id=context.handoff_id,
                status=HandoffStatus.FAILED,
                error=str(e),
                execution_time=asyncio.get_event_loop().time() - start_time
            )
    
    async def auto_handoff(
        self,
        from_agent_id: str,
        input: str,
        context: HandoffContext = None
    ) -> HandoffResult:
        """
        Automatically determine target agent based on rules.
        
        Args:
            from_agent_id: Source agent ID
            input: Input text
            context: Optional existing context
            
        Returns:
            HandoffResult
        """
        # Create temporary context for rule evaluation
        temp_context = context or HandoffContext(
            handoff_id="temp",
            from_agent=from_agent_id,
            to_agent="",
            input=input
        )
        
        # Apply rules
        for rule in self._handoff_rules:
            try:
                target_agent_id = rule(temp_context)
                if target_agent_id:
                    logger.info(f"Auto-handoff rule matched: {from_agent_id} -> {target_agent_id}")
                    return await self.handoff(
                        from_agent_id=from_agent_id,
                        to_agent_id=target_agent_id,
                        input=input,
                        context=context
                    )
            except Exception as e:
                logger.error(f"Error in handoff rule: {e}")
        
        # No rule matched
        return HandoffResult(
            handoff_id="none",
            status=HandoffStatus.FAILED,
            error="No handoff rule matched"
        )
    
    def get_handoff_history(self, handoff_id: str) -> Optional[HandoffContext]:
        """Get handoff context from history."""
        return self._handoff_history.get(handoff_id)
    
    def get_active_handoffs(self) -> List[HandoffContext]:
        """Get all active handoffs."""
        return list(self._active_handoffs.values())
    
    async def cancel_handoff(self, handoff_id: str) -> bool:
        """
        Cancel an active handoff.
        
        Args:
            handoff_id: Handoff to cancel
            
        Returns:
            True if cancelled, False if not found
        """
        async with self._lock:
            if handoff_id in self._active_handoffs:
                del self._active_handoffs[handoff_id]
                logger.info(f"Cancelled handoff: {handoff_id}")
                return True
        return False
