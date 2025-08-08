"""Google Gemini provider stub."""
from typing import List, Iterator
from ..base import BaseLLM, Message, CompletionResponse, StreamDelta, Role
from ....settings import settings

class GoogleProvider(BaseLLM):
    MODELS = ["gemini-pro", "gemini-pro-vision"]
    
    def __init__(self):
        super().__init__("google")
        self.api_key = settings.google.api_key
    
    def generate(self, model: str, messages: List[Message], **kwargs) -> CompletionResponse:
        return CompletionResponse(
            message=Message(role=Role.ASSISTANT, content="Google Gemini stub"),
            model=model, provider=self.provider_name
        )
    
    def stream(self, model: str, messages: List[Message], **kwargs) -> Iterator[StreamDelta]:
        yield StreamDelta(content="Gemini stream stub")
    
    def validate_model(self, model: str) -> bool:
        return model in self.MODELS
    
    def list_models(self) -> List[str]:
        return self.MODELS.copy()
