"""
AgentOS REST API Client

Provides a Python wrapper around the agentOS Flask backend API with
authentication, retry logic, and connection management.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx
import socketio

logger = logging.getLogger(__name__)


class AgentOSClient:
    """
    REST API client for agentOS platform.
    
    Provides methods to interact with agentOS Flask backend, including:
    - Command execution via POST /command
    - Status checking via GET /debug/status
    - WebSocket connections for real-time events
    - Authentication handling (JWT/OAuth)
    - Automatic retry with exponential backoff
    
    Example:
        ```python
        client = AgentOSClient("http://localhost:5000", api_key="...")
        
        # Execute a command
        result = await client.execute_command("twitter post Hello World!")
        
        # Check system status
        status = await client.get_system_status()
        
        # Connect to real-time events
        await client.connect_websocket()
        ```
    """
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:5000",
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0,
    ):
        """
        Initialize AgentOS client.
        
        Args:
            base_url: Base URL of agentOS backend (default: http://127.0.0.1:5000)
            api_key: API key for authentication (optional)
            client_id: Client ID for message queuing (optional, auto-generated if None)
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Initial retry delay in seconds (default: 1.0)
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client_id = client_id or f"agentosx-{int(time.time())}"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # HTTP client with connection pooling
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
        
        # WebSocket client
        self.sio: Optional[socketio.AsyncClient] = None
        self._ws_connected = False
        
        logger.info(f"Initialized AgentOS client for {base_url}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close all connections."""
        await self.http_client.aclose()
        if self.sio and self._ws_connected:
            await self.sio.disconnect()
        logger.info("Closed AgentOS client connections")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "X-Client-ID": self.client_id,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> httpx.Response:
        """
        Make HTTP request with exponential backoff retry.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            **kwargs: Additional arguments passed to httpx request
            
        Returns:
            HTTP response
            
        Raises:
            httpx.HTTPError: If all retries fail
        """
        url = urljoin(self.base_url, endpoint)
        kwargs.setdefault("headers", self._get_headers())
        
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = await self.http_client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Request failed after {self.max_retries} attempts: {e}")
        
        raise last_exception  # type: ignore
    
    async def execute_command(
        self,
        command: str,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a command on agentOS.
        
        Sends command to POST /command endpoint for processing by AgentRouter.
        
        Args:
            command: Command string (e.g., "twitter post Hello World!")
            verbose: Enable verbose output
            
        Returns:
            Response dict with keys: status, message, spoke, data, agent, agent_id
            
        Example:
            ```python
            result = await client.execute_command("autoblog generate")
            if result["status"] == "success":
                print(result["spoke"])
            ```
        """
        response = await self._request_with_retry(
            "POST",
            "/command",
            json={"command": command, "verbose": verbose},
        )
        return response.json()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get system diagnostics and status.
        
        Queries GET /debug/status for system health information.
        
        Returns:
            Status dict with system diagnostics
        """
        response = await self._request_with_retry("GET", "/debug/status")
        return response.json()
    
    async def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """
        Get status of a specific agent.
        
        Args:
            agent_name: Name of the agent (e.g., "twitter_bot")
            
        Returns:
            Agent status dict
        """
        response = await self._request_with_retry(
            "GET",
            f"/{agent_name}/status",
        )
        return response.json()
    
    async def register_client(self) -> Dict[str, Any]:
        """
        Register client for message polling.
        
        Registers client ID with agentOS for message queue.
        
        Returns:
            Registration response
        """
        response = await self._request_with_retry(
            "POST",
            "/register",
            json={"client_id": self.client_id},
        )
        return response.json()
    
    async def poll_messages(self) -> List[Dict[str, Any]]:
        """
        Poll for queued messages.
        
        Retrieves messages from the client's message queue.
        
        Returns:
            List of message dicts
        """
        response = await self._request_with_retry("GET", "/poll")
        data = response.json()
        return data.get("messages", [])
    
    async def stream_updates(self) -> Dict[str, Any]:
        """
        Get ongoing agent updates.
        
        Retrieves real-time updates from agents with message queues.
        
        Returns:
            Dict with message_count and messages list
        """
        response = await self._request_with_retry("GET", "/stream_updates")
        return response.json()
    
    async def get_nlp_model_info(self) -> Dict[str, Any]:
        """
        Get NLP model configuration.
        
        Queries natural language agent for current model settings.
        
        Returns:
            Model info dict with provider, model, available models
        """
        response = await self._request_with_retry(
            "GET",
            "/api/natural_language/model_info",
        )
        return response.json()
    
    async def set_nlp_provider(self, provider: str) -> Dict[str, Any]:
        """
        Set NLP model provider.
        
        Args:
            provider: Provider name ("gemini" or "ollama")
            
        Returns:
            Response dict
        """
        response = await self._request_with_retry(
            "POST",
            "/api/natural_language/set_provider",
            json={"provider": provider},
        )
        return response.json()
    
    async def set_nlp_model(self, model_name: str) -> Dict[str, Any]:
        """
        Set NLP model.
        
        Args:
            model_name: Model name (e.g., "gemini-2.0-flash-lite", "llama3.2:1b")
            
        Returns:
            Response dict
        """
        response = await self._request_with_retry(
            "POST",
            "/api/natural_language/set_model",
            json={"model_name": model_name},
        )
        return response.json()
    
    async def nlp_health_check(self) -> Dict[str, Any]:
        """
        Check NLP agent health.
        
        Returns:
            Health status dict
        """
        response = await self._request_with_retry(
            "GET",
            "/api/natural_language/health_check",
        )
        return response.json()
    
    # ============================================================================
    # WebSocket Methods
    # ============================================================================
    
    async def connect_websocket(
        self,
        on_connect: Optional[callable] = None,
        on_disconnect: Optional[callable] = None,
        on_execution_log: Optional[callable] = None,
        on_message: Optional[callable] = None,
    ) -> None:
        """
        Connect to agentOS WebSocket for real-time events.
        
        Establishes Socket.IO connection to receive:
        - execution_log: Real-time command execution logs
        - Agent-specific events
        
        Args:
            on_connect: Callback for connection event
            on_disconnect: Callback for disconnection event
            on_execution_log: Callback for execution logs (receives dict)
            on_message: Callback for generic messages (receives dict)
            
        Example:
            ```python
            def handle_log(data):
                print(f"[{data['agent']}] {data['message']}")
            
            await client.connect_websocket(on_execution_log=handle_log)
            ```
        """
        self.sio = socketio.AsyncClient(logger=False, engineio_logger=False)
        
        @self.sio.on("connect")
        async def _on_connect():
            self._ws_connected = True
            logger.info("Connected to agentOS WebSocket")
            if on_connect:
                await on_connect()
        
        @self.sio.on("disconnect")
        async def _on_disconnect():
            self._ws_connected = False
            logger.info("Disconnected from agentOS WebSocket")
            if on_disconnect:
                await on_disconnect()
        
        @self.sio.on("execution_log")
        async def _on_execution_log(data):
            logger.debug(f"Execution log: {data}")
            if on_execution_log:
                await on_execution_log(data)
        
        @self.sio.on("message")
        async def _on_message(data):
            logger.debug(f"Message: {data}")
            if on_message:
                await on_message(data)
        
        # Connect to WebSocket
        await self.sio.connect(self.base_url)
        logger.info(f"WebSocket connected to {self.base_url}")
    
    async def disconnect_websocket(self) -> None:
        """Disconnect from WebSocket."""
        if self.sio and self._ws_connected:
            await self.sio.disconnect()
            self._ws_connected = False
            logger.info("Disconnected from WebSocket")
    
    async def emit_websocket_event(
        self,
        event: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit an event to WebSocket.
        
        Args:
            event: Event name
            data: Event data (optional)
        """
        if not self.sio or not self._ws_connected:
            raise RuntimeError("WebSocket not connected. Call connect_websocket() first.")
        
        await self.sio.emit(event, data or {})
    
    @property
    def is_websocket_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._ws_connected
