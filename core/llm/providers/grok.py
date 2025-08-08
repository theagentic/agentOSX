"""Grok provider stub."""
from typing import List, Iterator
from ..base import BaseLLM, Message, CompletionResponse, StreamDelta, Role
from ....settings import settings

class GrokProvider(BaseLLM):
    MODELS = ["grok-1", "grok-2"]
    
    def __init__(self):
        super().__init__("grok")
        self.api_key = settings.grok.api_key
        self.base_url = settings.grok.base_url or "https://api.x.ai/v1"
    
    def generate(self, model: str, messages: List[Message], **kwargs) -> CompletionResponse:
        return CompletionResponse(
            message=Message(role=Role.ASSISTANT, content="Grok stub"),
            model=model, provider=self.provider_name
        )
    
    def stream(self, model: str, messages: List[Message], **kwargs) -> Iterator[StreamDelta]:
        yield StreamDelta(content="Grok stream stub")
    
    def validate_model(self, model: str) -> bool:
        return model in self.MODELS
    
    def list_models(self) -> List[str]:
        return self.MODELS.copy()
