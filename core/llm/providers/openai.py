"""
OpenAI provider implementation.
Uses the OpenAI API (or compatible endpoints).
"""

import json
import time
import logging
from typing import Optional, List, Dict, Any, Iterator
import requests

from ..base import (
    BaseLLM, Message, Tool, CompletionResponse, 
    StreamDelta, Usage, Role, ToolCall
)
from ....settings import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLM):
    """OpenAI LLM provider."""
    
    MODELS = [
        "gpt-4-turbo-preview",
        "gpt-4",
        "gpt-4-32k",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
    ]
    
    def __init__(self):
        super().__init__("openai")
        self.api_key = settings.openai.api_key
        self.base_url = settings.openai.base_url or "https://api.openai.com/v1"
        self.organization = settings.openai.organization
    
    def generate(
        self,
        model: str,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False,
        timeout: Optional[int] = None,
        **kwargs
    ) -> CompletionResponse:
        """Generate completion using OpenAI API."""
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Build request
        request_messages = self._build_messages(messages, system_prompt)
        request_data = {
            "model": model,
            "messages": request_messages,
            "temperature": temperature or 0.7,
            "max_tokens": max_tokens or 500,
        }
        
        if tools:
            request_data["tools"] = [t.to_dict() for t in tools]
            request_data["tool_choice"] = "auto"
        
        if json_mode:
            request_data["response_format"] = {"type": "json_object"}
        
        # Add any extra kwargs
        request_data.update(kwargs)
        
        # Make request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=request_data,
                timeout=timeout or 30
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            choice = data["choices"][0]
            message_data = choice["message"]
            
            # Build message
            message = Message(
                role=Role.ASSISTANT,
                content=message_data.get("content")
            )
            
            # Parse tool calls if present
            if "tool_calls" in message_data:
                for tc in message_data["tool_calls"]:
                    message.tool_calls.append(ToolCall(
                        id=tc["id"],
                        name=tc["function"]["name"],
                        arguments=json.loads(tc["function"]["arguments"])
                    ))
            
            # Parse usage
            usage = None
            if "usage" in data:
                usage = Usage(
                    prompt_tokens=data["usage"]["prompt_tokens"],
                    completion_tokens=data["usage"]["completion_tokens"],
                    total_tokens=data["usage"]["total_tokens"]
                )
            
            return CompletionResponse(
                message=message,
                usage=usage,
                model=model,
                provider=self.provider_name,
                metadata={"finish_reason": choice.get("finish_reason")}
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def stream(
        self,
        model: str,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False,
        timeout: Optional[int] = None,
        **kwargs
    ) -> Iterator[StreamDelta]:
        """Stream completion using OpenAI API."""
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Build request
        request_messages = self._build_messages(messages, system_prompt)
        request_data = {
            "model": model,
            "messages": request_messages,
            "temperature": temperature or 0.7,
            "max_tokens": max_tokens or 500,
            "stream": True
        }
        
        if tools:
            request_data["tools"] = [t.to_dict() for t in tools]
            request_data["tool_choice"] = "auto"
        
        if json_mode:
            request_data["response_format"] = {"type": "json_object"}
        
        request_data.update(kwargs)
        
        # Make streaming request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=request_data,
                timeout=timeout or 30,
                stream=True
            )
            response.raise_for_status()
            
            # Parse SSE stream
            for line in response.iter_lines():
                if not line:
                    continue
                    
                line = line.decode('utf-8')
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(data_str)
                        choice = data["choices"][0]
                        delta = choice.get("delta", {})
                        
                        # Build stream delta
                        stream_delta = StreamDelta()
                        
                        if "content" in delta:
                            stream_delta.content = delta["content"]
                        
                        if "tool_calls" in delta:
                            # Handle tool call streaming (simplified)
                            tc = delta["tool_calls"][0]
                            if "function" in tc:
                                stream_delta.tool_call = ToolCall(
                                    id=tc.get("id", ""),
                                    name=tc["function"].get("name", ""),
                                    arguments=json.loads(tc["function"].get("arguments", "{}"))
                                )
                        
                        stream_delta.finish_reason = choice.get("finish_reason")
                        
                        yield stream_delta
                        
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse SSE data: {data_str}")
                        continue
                        
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
    
    def _build_messages(
        self, 
        messages: List[Message], 
        system_prompt: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Build OpenAI-compatible message list."""
        result = []
        
        # Add system prompt if provided
        if system_prompt:
            result.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Convert messages
        for msg in messages:
            result.append(msg.to_dict())
        
        return result
    
    def validate_model(self, model: str) -> bool:
        """Check if model is supported."""
        return model in self.MODELS or model.startswith("gpt-")
    
    def list_models(self) -> List[str]:
        """List available models."""
        return self.MODELS.copy()
    
    def estimate_cost(self, usage: Usage, model: str) -> float:
        """Estimate cost for OpenAI models."""
        # Simplified pricing (actual prices vary by model)
        pricing = {
            "gpt-4": (0.03, 0.06),  # (input, output) per 1K tokens
            "gpt-4-32k": (0.06, 0.12),
            "gpt-3.5-turbo": (0.0015, 0.002),
            "gpt-3.5-turbo-16k": (0.003, 0.004)
        }
        
        # Find matching pricing
        input_price, output_price = pricing.get("gpt-3.5-turbo", (0.002, 0.002))
        for model_prefix, prices in pricing.items():
            if model.startswith(model_prefix):
                input_price, output_price = prices
                break
        
        return (usage.prompt_tokens * input_price + 
                usage.completion_tokens * output_price) / 1000
