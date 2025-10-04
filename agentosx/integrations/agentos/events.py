"""
AgentOS Event Subscription

Subscribe to agentOS platform events for real-time notifications,
user triggers, and system events.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set

from .client import AgentOSClient

logger = logging.getLogger(__name__)


class EventSubscriber:
    """
    Subscribe to agentOS platform events.
    
    Provides event subscription and handling for:
    - User triggers (commands, queries)
    - Agent events (start, stop, error)
    - System notifications (deployment, health)
    - Execution events (logs, traces)
    
    Example:
        ```python
        client = AgentOSClient("http://localhost:5000")
        subscriber = EventSubscriber(client)
        
        # Subscribe to execution logs
        @subscriber.on("execution_log")
        async def handle_log(data):
            print(f"[{data['agent']}] {data['message']}")
        
        # Subscribe to agent errors
        @subscriber.on("agent_error")
        async def handle_error(data):
            logger.error(f"Agent error: {data}")
        
        # Start event loop
        await subscriber.start()
        ```
    """
    
    def __init__(
        self,
        client: AgentOSClient,
    ):
        """
        Initialize event subscriber.
        
        Args:
            client: AgentOS client for WebSocket connection
        """
        self.client = client
        
        # Event handlers
        self._handlers: Dict[str, List[Callable]] = {}
        
        # Event filters
        self._filters: Dict[str, List[Callable]] = {}
        
        # Running state
        self._running = False
        self._event_task: Optional[asyncio.Task] = None
        
        logger.info("Initialized EventSubscriber")
    
    def on(self, event: str) -> Callable:
        """
        Decorator to register event handler.
        
        Args:
            event: Event name to handle
            
        Returns:
            Decorator function
            
        Example:
            ```python
            @subscriber.on("execution_log")
            async def handle_log(data):
                print(data)
            ```
        """
        def decorator(func: Callable) -> Callable:
            self.add_handler(event, func)
            return func
        return decorator
    
    def add_handler(
        self,
        event: str,
        handler: Callable,
    ) -> None:
        """
        Add event handler.
        
        Args:
            event: Event name
            handler: Async callable to handle event (receives data dict)
        """
        if event not in self._handlers:
            self._handlers[event] = []
        
        self._handlers[event].append(handler)
        logger.info(f"Added handler for event: {event}")
    
    def remove_handler(
        self,
        event: str,
        handler: Callable,
    ) -> None:
        """
        Remove event handler.
        
        Args:
            event: Event name
            handler: Handler to remove
        """
        if event in self._handlers:
            self._handlers[event].remove(handler)
            logger.info(f"Removed handler for event: {event}")
    
    def add_filter(
        self,
        event: str,
        filter_func: Callable[[Dict[str, Any]], bool],
    ) -> None:
        """
        Add event filter.
        
        Filters allow selective event handling based on event data.
        
        Args:
            event: Event name
            filter_func: Function that returns True if event should be handled
            
        Example:
            ```python
            # Only handle logs from specific agent
            subscriber.add_filter(
                "execution_log",
                lambda data: data.get("agent") == "twitter_bot"
            )
            ```
        """
        if event not in self._filters:
            self._filters[event] = []
        
        self._filters[event].append(filter_func)
        logger.info(f"Added filter for event: {event}")
    
    async def _dispatch_event(
        self,
        event: str,
        data: Dict[str, Any],
    ) -> None:
        """
        Dispatch event to registered handlers.
        
        Args:
            event: Event name
            data: Event data
        """
        # Apply filters
        if event in self._filters:
            for filter_func in self._filters[event]:
                if not filter_func(data):
                    return  # Event filtered out
        
        # Dispatch to handlers
        if event in self._handlers:
            for handler in self._handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event}: {e}")
    
    async def start(self) -> None:
        """
        Start event subscription.
        
        Connects to agentOS WebSocket and begins processing events.
        """
        if self._running:
            logger.warning("Event subscriber already running")
            return
        
        self._running = True
        
        # Connect to WebSocket with event handlers
        await self.client.connect_websocket(
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
            on_execution_log=lambda data: asyncio.create_task(
                self._dispatch_event("execution_log", data)
            ),
            on_message=lambda data: asyncio.create_task(
                self._dispatch_event("message", data)
            ),
        )
        
        # Start polling for updates
        self._event_task = asyncio.create_task(self._event_loop())
        
        logger.info("Started event subscription")
    
    async def stop(self) -> None:
        """Stop event subscription."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel event loop
        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect WebSocket
        await self.client.disconnect_websocket()
        
        logger.info("Stopped event subscription")
    
    async def _on_connect(self) -> None:
        """Handle WebSocket connection."""
        logger.info("WebSocket connected")
        await self._dispatch_event("connect", {})
    
    async def _on_disconnect(self) -> None:
        """Handle WebSocket disconnection."""
        logger.info("WebSocket disconnected")
        await self._dispatch_event("disconnect", {})
    
    async def _event_loop(self) -> None:
        """
        Event loop for polling updates.
        
        Polls /stream_updates endpoint for agent messages.
        """
        while self._running:
            try:
                # Poll for updates
                updates = await self.client.stream_updates()
                
                # Dispatch messages
                for message in updates.get("messages", []):
                    event_type = message.get("status", "message")
                    await self._dispatch_event(event_type, message)
                
            except Exception as e:
                logger.error(f"Error in event loop: {e}")
            
            # Wait before next poll
            await asyncio.sleep(1)
    
    # ============================================================================
    # Convenience Methods
    # ============================================================================
    
    async def subscribe_to_agent(
        self,
        agent_id: str,
        handler: Callable,
    ) -> None:
        """
        Subscribe to all events from a specific agent.
        
        Args:
            agent_id: Agent ID
            handler: Event handler
        """
        def agent_filter(data: Dict[str, Any]) -> bool:
            return data.get("agent") == agent_id or data.get("agent_id") == agent_id
        
        # Add filter for each event type
        for event in ["execution_log", "message", "progress"]:
            self.add_filter(event, agent_filter)
            self.add_handler(event, handler)
        
        logger.info(f"Subscribed to agent: {agent_id}")
    
    async def subscribe_to_user_triggers(
        self,
        handler: Callable,
    ) -> None:
        """
        Subscribe to user trigger events.
        
        User triggers are commands initiated by users.
        
        Args:
            handler: Event handler
        """
        self.add_handler("user_trigger", handler)
        logger.info("Subscribed to user triggers")
    
    async def subscribe_to_system_notifications(
        self,
        handler: Callable,
    ) -> None:
        """
        Subscribe to system notification events.
        
        System notifications include deployment, health, and error events.
        
        Args:
            handler: Event handler
        """
        for event in ["deployment", "health_check", "system_error"]:
            self.add_handler(event, handler)
        
        logger.info("Subscribed to system notifications")
