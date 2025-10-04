"""
Template Agent Implementation

Example agent demonstrating best practices for AgentOSX framework.
Use this as a starting point for creating new agents.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from agentosx.agents.base import BaseAgent, ExecutionContext
from agentosx.agents.decorators import agent, tool, hook, streaming
from agentosx.streaming.events import StreamEvent, TextEvent, AgentCompleteEvent


logger = logging.getLogger(__name__)


@agent(
    name="example-agent",
    version="1.0.0",
    description="Example agent demonstrating AgentOSX capabilities"
)
class ExampleAgent(BaseAgent):
    """
    Example agent with full lifecycle management, tools, and streaming.
    
    This template demonstrates:
    - Lifecycle hooks
    - Tool definitions with decorators
    - Streaming responses
    - State management
    - MCP integration
    """
    
    def __init__(self):
        """Initialize the agent."""
        super().__init__()
        self.name = "example-agent"
        self.version = "1.0.0"
        self.description = "Example agent template"
        
        # Agent-specific state
        self.request_count = 0
        self.last_request_time = None
    
    # =========================================================================
    # Lifecycle Hooks
    # =========================================================================
    
    @hook("init")
    async def on_init(self):
        """Called after agent initialization."""
        logger.info(f"Agent {self.name} initialized")
        self.update_state(metadata={"initialized_at": "now"})
    
    @hook("start")
    async def on_start(self):
        """Called when agent starts."""
        logger.info(f"Agent {self.name} started")
    
    @hook("stop")
    async def on_stop(self):
        """Called before agent stops."""
        logger.info(f"Agent {self.name} stopping - processed {self.request_count} requests")
    
    @hook("message")
    async def on_message(self, message: str):
        """Called on each message."""
        self.request_count += 1
        logger.debug(f"Processing message #{self.request_count}")
    
    @hook("tool_call")
    async def on_tool_call(self, tool_name: str, arguments: dict):
        """Called before tool execution."""
        logger.info(f"Calling tool: {tool_name}")
    
    @hook("tool_result")
    async def on_tool_result(self, tool_name: str, result: Any):
        """Called after tool execution."""
        logger.info(f"Tool {tool_name} completed")
    
    @hook("error")
    async def on_error(self, error: Exception):
        """Called on errors."""
        logger.error(f"Agent error: {error}")
    
    # =========================================================================
    # Core Processing
    # =========================================================================
    
    async def process(self, input: str, context: ExecutionContext = None) -> str:
        """
        Process input and return response.
        
        Args:
            input: User input
            context: Execution context
            
        Returns:
            Agent response
        """
        # Trigger message hook
        await self.on_message(input)
        
        # Update context
        if context:
            self.set_context(context)
        
        # Simple command routing (replace with LLM in production)
        input_lower = input.lower()
        
        if "search" in input_lower:
            # Extract query (simple example)
            query = input.replace("search", "").strip()
            result = await self.search_web(query)
            return f"Search results: {result}"
        
        elif "analyze" in input_lower:
            # Example analysis
            data = [1, 2, 3, 4, 5]
            result = await self.analyze_data(data, "statistical")
            return f"Analysis complete: {result}"
        
        elif "status" in input_lower:
            return self.get_status()
        
        else:
            return (
                f"Hello! I'm {self.name}. I can help you with:\n"
                "- Searching the web\n"
                "- Analyzing data\n"
                "- Checking status\n\n"
                "Try: 'search quantum computing' or 'analyze data'"
            )
    
    # =========================================================================
    # Streaming Support
    # =========================================================================
    
    @streaming
    async def stream(self, input: str, context: ExecutionContext = None):
        """
        Stream response as events.
        
        Args:
            input: User input
            context: Execution context
            
        Yields:
            StreamEvent instances
        """
        # Simulate thinking
        yield TextEvent(
            agent_id=self.name,
            data="Thinking about your request..."
        )
        await asyncio.sleep(0.5)
        
        # Process
        result = await self.process(input, context)
        
        # Stream result in chunks
        words = result.split()
        for i, word in enumerate(words):
            yield TextEvent(
                agent_id=self.name,
                data=word + " "
            )
            await asyncio.sleep(0.05)  # Simulate typing
        
        # Complete
        yield AgentCompleteEvent(
            agent_id=self.name,
            data={"status": "completed", "word_count": len(words)}
        )
    
    # =========================================================================
    # Tools
    # =========================================================================
    
    @tool(
        name="search_web",
        description="Search the web for information",
        schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    )
    async def search_web(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Search the web (mock implementation).
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of search results
        """
        # Trigger tool call hook
        await self.on_tool_call("search_web", {"query": query, "num_results": num_results})
        
        # Mock implementation - replace with actual search
        results = [
            {
                "title": f"Result {i+1} for '{query}'",
                "url": f"https://example.com/result{i+1}",
                "snippet": f"This is a mock search result for {query}"
            }
            for i in range(num_results)
        ]
        
        # Trigger tool result hook
        await self.on_tool_result("search_web", results)
        
        return results
    
    @tool(
        name="analyze_data",
        description="Analyze a dataset",
        schema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "Data to analyze"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["statistical", "trend", "correlation"],
                    "description": "Type of analysis"
                }
            },
            "required": ["data", "analysis_type"]
        }
    )
    async def analyze_data(self, data: List[float], analysis_type: str) -> Dict[str, Any]:
        """
        Analyze data (mock implementation).
        
        Args:
            data: Data to analyze
            analysis_type: Type of analysis
            
        Returns:
            Analysis results
        """
        await self.on_tool_call("analyze_data", {"analysis_type": analysis_type})
        
        # Mock analysis
        if analysis_type == "statistical":
            result = {
                "mean": sum(data) / len(data),
                "min": min(data),
                "max": max(data),
                "count": len(data)
            }
        elif analysis_type == "trend":
            result = {
                "trend": "upward" if data[-1] > data[0] else "downward",
                "change": data[-1] - data[0]
            }
        else:
            result = {
                "correlation": 0.85,
                "p_value": 0.001
            }
        
        await self.on_tool_result("analyze_data", result)
        return result
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def get_status(self) -> str:
        """Get agent status."""
        return (
            f"Agent Status:\n"
            f"- Name: {self.name}\n"
            f"- Version: {self.version}\n"
            f"- Status: {self.status.value}\n"
            f"- Requests Processed: {self.request_count}\n"
        )


# Example usage
async def main():
    """Example usage of the template agent."""
    agent = ExampleAgent()
    
    # Initialize and start
    await agent.initialize()
    await agent.start()
    
    # Process some requests
    print("=== Standard Processing ===")
    response = await agent.process("search quantum computing")
    print(response)
    
    print("\n=== Streaming Response ===")
    async for event in agent.stream("analyze data"):
        print(event.data, end="", flush=True)
    print("\n")
    
    # Use as MCP server
    print("\n=== MCP Server ===")
    mcp_server = agent.to_mcp_server()
    print(f"Created MCP server: {mcp_server.name}")
    
    # Stop agent
    await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
