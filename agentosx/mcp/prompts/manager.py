"""
MCP Prompt Manager.

Manages prompt templates with dynamic variable substitution.
"""

import logging
from typing import Any, Dict, List, Optional
import re

from ..protocol import PromptDefinition

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manager for MCP prompt templates.
    
    Supports template variables, conditional sections, and composition.
    """
    
    def __init__(self):
        """Initialize prompt manager."""
        self._prompts: Dict[str, Dict[str, Any]] = {}
    
    def register_prompt(
        self,
        name: str,
        description: Optional[str] = None,
        template: Optional[str] = None,
        arguments: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Register a prompt template.
        
        Args:
            name: Prompt name
            description: Prompt description
            template: Prompt template string with {{variable}} placeholders
            arguments: List of argument definitions
        """
        self._prompts[name] = {
            "name": name,
            "description": description,
            "template": template or "",
            "arguments": arguments or [],
        }
        
        logger.debug(f"Registered prompt: {name}")
    
    def unregister_prompt(self, name: str):
        """Unregister a prompt template."""
        if name in self._prompts:
            del self._prompts[name]
            logger.debug(f"Unregistered prompt: {name}")
    
    def list_prompts(self) -> List[PromptDefinition]:
        """
        List all registered prompts.
        
        Returns:
            List of prompt definitions
        """
        return [
            PromptDefinition(
                name=prompt["name"],
                description=prompt["description"],
                arguments=prompt["arguments"],
            )
            for prompt in self._prompts.values()
        ]
    
    async def get_prompt(self, name: str, arguments: Dict[str, Any]) -> str:
        """
        Get rendered prompt with variable substitution.
        
        Args:
            name: Prompt name
            arguments: Variable values
            
        Returns:
            Rendered prompt text
            
        Raises:
            ValueError: If prompt not found
        """
        if name not in self._prompts:
            raise ValueError(f"Prompt not found: {name}")
        
        prompt = self._prompts[name]
        template = prompt["template"]
        
        # Simple variable substitution
        rendered = template
        for key, value in arguments.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value))
        
        # Check for any remaining unsubstituted variables
        remaining = re.findall(r"\{\{(\w+)\}\}", rendered)
        if remaining:
            logger.warning(f"Unsubstituted variables in prompt '{name}': {remaining}")
        
        return rendered
