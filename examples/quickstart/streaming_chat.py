"""
Streaming Chat Example

Demonstrates streaming responses for better UX.
"""

import asyncio
from agentosx.agents.base import Agent
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

console = Console()


class ChatAgent(Agent):
    """A conversational agent with streaming."""
    
    name = "chat-agent"
    
    def __init__(self):
        super().__init__()
        self.conversation_history = []
    
    async def process(self, input_text: str) -> str:
        """Process input (non-streaming)."""
        self.conversation_history.append(f"User: {input_text}")
        
        # Generate response (simplified)
        response = f"Thanks for your message! You said: '{input_text}'. How can I help further?"
        
        self.conversation_history.append(f"Assistant: {response}")
        return response
    
    async def stream(self, input_text: str):
        """Stream response for better UX."""
        self.conversation_history.append(f"User: {input_text}")
        
        # Simulate LLM streaming
        response_words = [
            "Thanks", "for", "your", "message!", "You", "said:",
            f"'{input_text}'.", "How", "can", "I", "help", "further?"
        ]
        
        full_response = ""
        
        for word in response_words:
            chunk = word + " "
            full_response += chunk
            
            yield {
                "type": "text",
                "text": chunk
            }
            
            await asyncio.sleep(0.1)  # Simulate network delay
        
        self.conversation_history.append(f"Assistant: {full_response.strip()}")


async def main():
    """Run an interactive streaming chat."""
    agent = ChatAgent()
    await agent.start()
    
    console.print("[bold cyan]Streaming Chat Demo[/bold cyan]")
    console.print("[dim]Type 'quit' to exit[/dim]\n")
    
    while True:
        # Get user input
        user_input = console.input("[bold green]You:[/bold green] ")
        
        if user_input.lower() in ["quit", "exit"]:
            break
        
        # Stream response
        console.print("[bold blue]Agent:[/bold blue] ", end="")
        
        full_response = ""
        async for chunk in agent.stream(user_input):
            console.print(chunk["text"], end="", highlight=False)
            full_response += chunk["text"]
        
        console.print()  # New line after response
    
    console.print("\n[dim]Goodbye![/dim]")
    await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
