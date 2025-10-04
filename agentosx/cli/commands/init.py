"""
Init Command - Create new agents from templates
"""

import shutil
from pathlib import Path
from typing import Optional
from rich.progress import track
import yaml

from agentosx.cli.utils import console, success, error, info, print_panel


TEMPLATES = {
    "basic": "Basic agent with simple tools",
    "twitter": "Twitter bot with posting capabilities",
    "blog": "Blog generation agent with workflows",
    "crew": "Multi-agent crew with orchestration",
}


def init_agent(name: str, template: str, path: Optional[Path] = None):
    """
    Create a new agent from template.
    
    Args:
        name: Agent name
        template: Template type
        path: Target directory
    """
    # Validate template
    if template not in TEMPLATES:
        error(f"Unknown template '{template}'. Available: {', '.join(TEMPLATES.keys())}")
    
    # Determine target path
    if path is None:
        path = Path.cwd() / "agents" / name
    else:
        path = path / name
    
    # Check if path exists
    if path.exists():
        error(f"Directory already exists: {path}")
    
    info(f"Creating agent '{name}' from template '{template}'...")
    
    # Create directory structure
    path.mkdir(parents=True, exist_ok=True)
    
    # Copy template files
    template_path = Path(__file__).parent.parent / "templates" / template
    
    if template_path.exists():
        # Copy from existing template
        for item in track(list(template_path.rglob("*")), description="Copying files..."):
            if item.is_file():
                rel_path = item.relative_to(template_path)
                target = path / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                
                # Process template variables
                content = item.read_text()
                content = content.replace("{{AGENT_NAME}}", name)
                content = content.replace("{{AGENT_NAME_SNAKE}}", name.replace("-", "_"))
                content = content.replace("{{AGENT_NAME_PASCAL}}", _to_pascal_case(name))
                
                target.write_text(content)
    else:
        # Generate basic template
        _generate_basic_template(path, name)
    
    # Create additional directories
    (path / "tools").mkdir(exist_ok=True)
    (path / "tests").mkdir(exist_ok=True)
    (path / "prompts").mkdir(exist_ok=True)
    
    success(f"Agent '{name}' created at {path}")
    
    # Print next steps
    print_panel(
        f"""[bold]Next steps:[/bold]

1. Navigate to your agent:
   [cyan]cd {path}[/cyan]

2. Edit the agent manifest:
   [cyan]code agent.yaml[/cyan]

3. Implement agent logic:
   [cyan]code agent.py[/cyan]

4. Start development server:
   [cyan]agentosx dev {name}[/cyan]

5. Test your agent:
   [cyan]agentosx test {name}[/cyan]

[dim]Documentation: https://docs.agentosx.dev/getting-started[/dim]
""",
        title="🚀 Agent Created",
        style="green"
    )


def _generate_basic_template(path: Path, name: str):
    """Generate basic agent template."""
    
    # Create agent.yaml
    manifest = {
        "persona": {
            "name": name.replace("-", " ").title(),
            "description": f"A helpful {name} agent",
            "system_prompt": "You are a helpful AI assistant.",
            "tone": "professional",
        },
        "llm": {
            "primary": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
            }
        },
        "tools": [],
        "memory": {
            "buffer": {
                "type": "sliding_window",
                "max_messages": 50,
            }
        },
        "metadata": {
            "version": "1.0.0",
            "author": "Your Name",
        }
    }
    
    with open(path / "agent.yaml", "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
    
    # Create agent.py
    agent_code = f'''"""
{name.replace("-", " ").title()} Agent

A helpful AI assistant.
"""

import asyncio
from typing import Any, AsyncIterator
from agentosx.agents.base import BaseAgent, ExecutionContext
from agentosx.agents.decorators import agent, tool, hook
from agentosx.streaming.events import StreamEvent, TextStreamEvent


@agent(
    name="{name}",
    version="1.0.0",
    description="A helpful {name} agent"
)
class {_to_pascal_case(name)}Agent(BaseAgent):
    """Main agent class."""
    
    def __init__(self):
        super().__init__()
        self.name = "{name}"
    
    @hook("init")
    async def on_init(self):
        """Called when agent is initialized."""
        self.logger.info("Agent initialized")
    
    @hook("start")
    async def on_start(self):
        """Called when agent starts."""
        self.logger.info("Agent started")
    
    async def process(self, input: str, context: ExecutionContext = None) -> str:
        """
        Process user input.
        
        Args:
            input: User input text
            context: Execution context
            
        Returns:
            Agent response
        """
        self.logger.info(f"Processing: {{input}}")
        
        # TODO: Implement your agent logic here
        response = f"Received: {{input}}"
        
        return response
    
    @tool(
        name="example_tool",
        description="An example tool"
    )
    async def example_tool(self, query: str) -> str:
        """
        Example tool implementation.
        
        Args:
            query: Query string
            
        Returns:
            Tool result
        """
        return f"Tool result for: {{query}}"


# For direct execution
if __name__ == "__main__":
    async def main():
        agent = {_to_pascal_case(name)}Agent()
        await agent.start()
        
        result = await agent.process("Hello!")
        print(result)
        
        await agent.stop()
    
    asyncio.run(main())
'''
    
    (path / "agent.py").write_text(agent_code)
    
    # Create README.md
    readme = f"""# {name.replace("-", " ").title()}

A helpful AI assistant built with AgentOSX.

## Features

- TODO: List your agent's features

## Usage

### Development

```bash
# Start development server
agentosx dev {name}

# Run locally
agentosx run {name} --input="Hello"

# Run tests
agentosx test {name}
```

### Deployment

```bash
# Deploy to production
agentosx deploy {name}
```

## Configuration

Edit `agent.yaml` to configure:
- Persona and behavior
- LLM settings
- Tools and capabilities
- Memory configuration

## Tools

TODO: Document your agent's tools

## License

MIT
"""
    
    (path / "README.md").write_text(readme)
    
    # Create .gitignore
    gitignore = """__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env
.venv
*.log
.agentosx/
"""
    
    (path / ".gitignore").write_text(gitignore)


def _to_pascal_case(name: str) -> str:
    """Convert kebab-case to PascalCase."""
    return "".join(word.capitalize() for word in name.replace("_", "-").split("-"))
