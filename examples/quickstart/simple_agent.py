"""
Simple Agent Example

A minimal agent that echoes input with enthusiasm.
"""

import asyncio
from agentosx.agents.base import Agent


class SimpleAgent(Agent):
    """A simple echo agent with enthusiasm."""
    
    name = "simple-agent"
    
    async def process(self, input_text: str) -> str:
        """Process input and return enthusiastic response."""
        return f"You said: {input_text}! That's awesome! 🎉"
    
    async def stream(self, input_text: str):
        """Stream response word by word."""
        words = f"You said: {input_text}! That's awesome! 🎉".split()
        
        for word in words:
            yield {
                "type": "text",
                "text": word + " "
            }
            await asyncio.sleep(0.1)  # Simulate typing


async def main():
    """Run the simple agent."""
    agent = SimpleAgent()
    await agent.start()
    
    # Process some inputs
    inputs = [
        "Hello!",
        "This is a test",
        "AgentOSX is cool"
    ]
    
    for user_input in inputs:
        print(f"\n[User] {user_input}")
        
        # Non-streaming response
        result = await agent.process(user_input)
        print(f"[Agent] {result}")
        
        # Streaming response
        print("[Agent] ", end="", flush=True)
        async for chunk in agent.stream(user_input):
            print(chunk["text"], end="", flush=True)
        print()
    
    await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
