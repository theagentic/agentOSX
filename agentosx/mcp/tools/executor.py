"""
MCP Tool Executor.

Handles tool execution with streaming support and error handling.
"""

import asyncio
import logging
from typing import Any, Dict, AsyncIterator, Optional

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executor for MCP tools with streaming and error handling.
    
    Provides advanced execution features like timeouts, retries,
    and progress streaming.
    """
    
    def __init__(
        self,
        default_timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize tool executor.
        
        Args:
            default_timeout: Default execution timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.default_timeout = default_timeout
        self.max_retries = max_retries
    
    async def execute(
        self,
        tool_func: Any,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None,
        retry: bool = True,
    ) -> Any:
        """
        Execute tool with timeout and retry logic.
        
        Args:
            tool_func: Tool function to execute
            arguments: Tool arguments
            timeout: Execution timeout (uses default if not specified)
            retry: Enable retry on failure
            
        Returns:
            Tool result
            
        Raises:
            TimeoutError: If execution times out
            Exception: If execution fails
        """
        timeout = timeout or self.default_timeout
        attempts = 0
        last_error = None
        
        while attempts < self.max_retries:
            attempts += 1
            
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    tool_func(**arguments),
                    timeout=timeout
                )
                
                logger.debug(f"Tool executed successfully (attempt {attempts})")
                return result
            
            except asyncio.TimeoutError:
                logger.warning(f"Tool execution timeout (attempt {attempts})")
                last_error = TimeoutError(f"Tool execution timed out after {timeout}s")
                
                if not retry or attempts >= self.max_retries:
                    raise last_error
            
            except Exception as e:
                logger.error(f"Tool execution error (attempt {attempts}): {e}")
                last_error = e
                
                if not retry or attempts >= self.max_retries:
                    raise
            
            # Exponential backoff before retry
            if attempts < self.max_retries:
                await asyncio.sleep(2 ** (attempts - 1))
        
        # Should not reach here, but just in case
        raise last_error or Exception("Tool execution failed")
    
    async def execute_streaming(
        self,
        tool_func: Any,
        arguments: Dict[str, Any],
    ) -> AsyncIterator[Any]:
        """
        Execute tool with streaming results.
        
        Args:
            tool_func: Async generator tool function
            arguments: Tool arguments
            
        Yields:
            Streamed results
        """
        try:
            async for chunk in tool_func(**arguments):
                yield chunk
        
        except Exception as e:
            logger.error(f"Streaming execution error: {e}", exc_info=True)
            raise
