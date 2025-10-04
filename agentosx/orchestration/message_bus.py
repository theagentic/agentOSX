"""
Event-Driven Message Bus

Pub/sub pattern for inter-agent communication and coordination.
Integrates with agentOS event system.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Message:
    """Message passed through the bus."""
    message_id: str
    topic: str
    sender: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "topic": self.topic,
            "sender": self.sender,
            "payload": self.payload,
            "priority": self.priority.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if isinstance(data.get("priority"), int):
            data["priority"] = MessagePriority(data["priority"])
        return cls(**data)


class MessageHandler:
    """Handler for messages on a topic."""
    
    def __init__(
        self,
        handler_id: str,
        callback: Callable,
        filter_func: Optional[Callable[[Message], bool]] = None
    ):
        """
        Initialize handler.
        
        Args:
            handler_id: Unique handler identifier
            callback: Async function to handle messages
            filter_func: Optional filter function
        """
        self.handler_id = handler_id
        self.callback = callback
        self.filter_func = filter_func
        self.message_count = 0
        self.error_count = 0
        self.last_message_at: Optional[datetime] = None
    
    async def handle(self, message: Message) -> bool:
        """
        Handle a message.
        
        Args:
            message: Message to handle
            
        Returns:
            True if handled successfully
        """
        # Apply filter if present
        if self.filter_func and not self.filter_func(message):
            return False
        
        try:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(message)
            else:
                self.callback(message)
            
            self.message_count += 1
            self.last_message_at = datetime.now()
            return True
        
        except Exception as e:
            self.error_count += 1
            logger.error(f"Handler {self.handler_id} error: {e}")
            return False


class MessageBus:
    """
    Event-driven message bus for agent coordination.
    
    Supports:
    - Pub/sub pattern
    - Topic-based routing
    - Message filtering
    - Priority queuing
    - Integration with agentOS events
    """
    
    def __init__(self, name: str = "default"):
        """
        Initialize message bus.
        
        Args:
            name: Bus name
        """
        self.name = name
        self._topics: Dict[str, Set[str]] = {}  # topic -> handler_ids
        self._handlers: Dict[str, MessageHandler] = {}  # handler_id -> handler
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._message_history: List[Message] = []
        self._max_history = 1000
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start the message bus worker."""
        if self._running:
            logger.warning("Message bus already running")
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(self._process_messages())
        logger.info(f"Started message bus: {self.name}")
    
    async def stop(self):
        """Stop the message bus worker."""
        if not self._running:
            return
        
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Stopped message bus: {self.name}")
    
    async def subscribe(
        self,
        topic: str,
        handler_id: str,
        callback: Callable,
        filter_func: Optional[Callable[[Message], bool]] = None
    ):
        """
        Subscribe to a topic.
        
        Args:
            topic: Topic to subscribe to
            handler_id: Unique handler identifier
            callback: Handler function
            filter_func: Optional filter function
        """
        async with self._lock:
            # Create handler
            handler = MessageHandler(handler_id, callback, filter_func)
            self._handlers[handler_id] = handler
            
            # Register topic
            if topic not in self._topics:
                self._topics[topic] = set()
            self._topics[topic].add(handler_id)
        
        logger.info(f"Subscribed {handler_id} to topic: {topic}")
    
    async def unsubscribe(self, topic: str, handler_id: str):
        """
        Unsubscribe from a topic.
        
        Args:
            topic: Topic to unsubscribe from
            handler_id: Handler identifier
        """
        async with self._lock:
            if topic in self._topics and handler_id in self._topics[topic]:
                self._topics[topic].remove(handler_id)
                if not self._topics[topic]:
                    del self._topics[topic]
            
            if handler_id in self._handlers:
                del self._handlers[handler_id]
        
        logger.info(f"Unsubscribed {handler_id} from topic: {topic}")
    
    async def publish(
        self,
        topic: str,
        sender: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Publish a message to a topic.
        
        Args:
            topic: Topic to publish to
            sender: Sender identifier
            payload: Message payload
            priority: Message priority
            metadata: Optional metadata
            
        Returns:
            Message ID
        """
        message_id = f"msg_{topic}_{int(datetime.now().timestamp() * 1000)}"
        
        message = Message(
            message_id=message_id,
            topic=topic,
            sender=sender,
            payload=payload,
            priority=priority,
            metadata=metadata or {}
        )
        
        # Add to queue with priority
        await self._message_queue.put((priority.value, message))
        
        # Add to history
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history.pop(0)
        
        logger.debug(f"Published message {message_id} to topic: {topic}")
        return message_id
    
    async def _process_messages(self):
        """Worker task to process message queue."""
        logger.info("Message bus worker started")
        
        while self._running:
            try:
                # Get message with timeout
                priority, message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                
                # Get handlers for topic
                handler_ids = self._topics.get(message.topic, set())
                
                if not handler_ids:
                    logger.debug(f"No handlers for topic: {message.topic}")
                    continue
                
                # Dispatch to all handlers
                for handler_id in handler_ids:
                    handler = self._handlers.get(handler_id)
                    if handler:
                        asyncio.create_task(handler.handle(message))
            
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
        
        logger.info("Message bus worker stopped")
    
    def get_topics(self) -> List[str]:
        """Get all registered topics."""
        return list(self._topics.keys())
    
    def get_subscribers(self, topic: str) -> List[str]:
        """Get all subscribers to a topic."""
        return list(self._topics.get(topic, set()))
    
    def get_message_history(self, topic: str = None, limit: int = 100) -> List[Message]:
        """
        Get message history.
        
        Args:
            topic: Filter by topic (None for all)
            limit: Maximum messages to return
            
        Returns:
            List of messages
        """
        messages = self._message_history
        
        if topic:
            messages = [m for m in messages if m.topic == topic]
        
        return messages[-limit:]
    
    def get_handler_stats(self, handler_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a handler."""
        handler = self._handlers.get(handler_id)
        if not handler:
            return None
        
        return {
            "handler_id": handler.handler_id,
            "message_count": handler.message_count,
            "error_count": handler.error_count,
            "last_message_at": handler.last_message_at.isoformat() if handler.last_message_at else None
        }
    
    async def forward_to_agentos(self, agentos_event_handler: Callable):
        """
        Forward all messages to agentOS event system.
        
        Args:
            agentos_event_handler: agentOS event handler function
        """
        async def forward_handler(message: Message):
            """Forward message to agentOS."""
            try:
                event_data = {
                    "type": f"agent.{message.topic}",
                    "source": message.sender,
                    "data": message.payload,
                    "timestamp": message.timestamp.isoformat()
                }
                await agentos_event_handler(event_data)
            except Exception as e:
                logger.error(f"Error forwarding to agentOS: {e}")
        
        # Subscribe to all topics with wildcard
        await self.subscribe(
            topic="*",
            handler_id="agentos_forwarder",
            callback=forward_handler
        )
        
        logger.info("Enabled agentOS event forwarding")
    
    def clear_history(self):
        """Clear message history."""
        self._message_history.clear()
        logger.info("Cleared message history")
