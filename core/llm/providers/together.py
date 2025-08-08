"""Together AI provider stub."""
from typing import List, Iterator
from ..base import BaseLLM, Message, CompletionResponse, StreamDelta, Role
from ....settings import settings

class TogetherProvider(BaseLLM):
    MODELS = ["mixtral-8x7b", "llama-3-70b", "codellama-34b"]
    
    def __init__(self):
        super().__init__("together")
        self.api_key = settings.together.api_key
        self.base_url = settings.together.base_url or "https://api.together.xyz/v1"
    
    def generate(self, model: str, messages: List[Message], **kwargs) -> CompletionResponse:
        return CompletionResponse(
            message=Message(role=Role.ASSISTANT, content="Together stub"),
            model=model, provider=self.provider_name
        )
    
    def stream(self, model: str, messages: List[Message], **kwargs) -> Iterator[StreamDelta]:
        yield StreamDelta(content="Together stream stub")
    
    def validate_model(self, model: str) -> bool:
        return True
    
    def list_models(self) -> List[str]:
        return self.MODELS.copy()
