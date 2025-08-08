"""Anthropic provider stub implementation."""

from typing import Optional, List, Iterator
from ..base import BaseLLM, Message, Tool, CompletionResponse, StreamDelta, Role, Usage
from ....settings import settings


class AnthropicProvider(BaseLLM):
    """Anthropic Claude provider."""
    
    MODELS = ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku", "claude-2.1", "claude-instant"]
    
    def __init__(self):
        super().__init__("anthropic")
        self.api_key = settings.anthropic.api_key
        self.base_url = settings.anthropic.base_url or "https://api.anthropic.com/v1"
    
    def generate(self, model: str, messages: List[Message], **kwargs) -> CompletionResponse:
        # Stub implementation - would call Anthropic API
        return CompletionResponse(
            message=Message(role=Role.ASSISTANT, content="Anthropic response stub"),
            model=model,
            provider=self.provider_name
        )
    
    def stream(self, model: str, messages: List[Message], **kwargs) -> Iterator[StreamDelta]:
        yield StreamDelta(content="Anthropic streaming stub")
    
    def validate_model(self, model: str) -> bool:
        return model in self.MODELS
    
    def list_models(self) -> List[str]:
        return self.MODELS.copy()
