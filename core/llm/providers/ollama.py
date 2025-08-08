"""Ollama local provider stub."""
from typing import List, Iterator
from ..base import BaseLLM, Message, CompletionResponse, StreamDelta, Role
from ....settings import settings

class OllamaProvider(BaseLLM):
    MODELS = ["llama3", "mistral", "phi3", "gemma"]
    
    def __init__(self):
        super().__init__("ollama")
        self.base_url = settings.ollama.base_url or "http://localhost:11434"
    
    def generate(self, model: str, messages: List[Message], **kwargs) -> CompletionResponse:
        return CompletionResponse(
            message=Message(role=Role.ASSISTANT, content="Ollama stub"),
            model=model, provider=self.provider_name
        )
    
    def stream(self, model: str, messages: List[Message], **kwargs) -> Iterator[StreamDelta]:
        yield StreamDelta(content="Ollama stream stub")
    
    def validate_model(self, model: str) -> bool:
        return True  # Ollama can run many models
    
    def list_models(self) -> List[str]:
        return self.MODELS.copy()
