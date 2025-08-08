"""OpenRouter provider stub."""
from typing import List, Iterator
from ..base import BaseLLM, Message, CompletionResponse, StreamDelta, Role
from ....settings import settings

class OpenRouterProvider(BaseLLM):
    MODELS = ["gpt-4", "claude-3-opus", "llama-3-70b"]
    
    def __init__(self):
        super().__init__("openrouter")
        self.api_key = settings.openrouter.api_key
        self.base_url = settings.openrouter.base_url or "https://openrouter.ai/api/v1"
    
    def generate(self, model: str, messages: List[Message], **kwargs) -> CompletionResponse:
        return CompletionResponse(
            message=Message(role=Role.ASSISTANT, content="OpenRouter stub"),
            model=model, provider=self.provider_name
        )
    
    def stream(self, model: str, messages: List[Message], **kwargs) -> Iterator[StreamDelta]:
        yield StreamDelta(content="OpenRouter stream stub")
    
    def validate_model(self, model: str) -> bool:
        return True  # OpenRouter supports many models
    
    def list_models(self) -> List[str]:
        return self.MODELS.copy()
