"""
LLM Router with cost/latency/capability-aware routing and fallback logic.
"""

import time
import yaml
import logging
from typing import Optional, List, Dict, Any, Iterator, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import random

from .base import BaseLLM, Message, Tool, CompletionResponse, StreamDelta, Usage
from ...settings import settings

logger = logging.getLogger(__name__)


@dataclass
class RoutePolicy:
    """Routing policy for a task tag."""
    primary: str
    fallbacks: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def temperature_range(self) -> Tuple[float, float]:
        """Get temperature constraints."""
        temp = self.constraints.get("temperature", "0.7")
        if isinstance(temp, str) and "-" in temp:
            low, high = temp.split("-")
            return float(low), float(high)
        return float(temp), float(temp)
    
    @property
    def max_tokens(self) -> Optional[int]:
        """Get max tokens constraint."""
        return self.constraints.get("max_tokens")


@dataclass
class RouterConfig:
    """Router configuration."""
    policies: Dict[str, RoutePolicy] = field(default_factory=dict)
    failure_policy: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, path: str) -> "RouterConfig":
        """Load configuration from YAML file."""
        config_path = Path(path)
        if not config_path.exists():
            # Return default config if file doesn't exist
            return cls.default()
        
        with open(config_path) as f:
            data = yaml.safe_load(f)
        
        policies = {}
        for tag, policy_data in data.items():
            if tag == "failure_policy":
                continue
            policies[tag] = RoutePolicy(
                primary=policy_data["primary"],
                fallbacks=policy_data.get("fallbacks", []),
                constraints=policy_data.get("constraints", {})
            )
        
        return cls(
            policies=policies,
            failure_policy=data.get("failure_policy", {})
        )
    
    @classmethod
    def default(cls) -> "RouterConfig":
        """Get default router configuration."""
        return cls(
            policies={
                "creative_posting": RoutePolicy(
                    primary="openai:gpt-4",
                    fallbacks=["anthropic:claude-3-opus", "openrouter:gpt-4"],
                    constraints={"temperature": "0.9-1.2", "max_tokens": 300}
                ),
                "planning": RoutePolicy(
                    primary="anthropic:claude-3-opus",
                    fallbacks=["openai:gpt-4"],
                    constraints={"temperature": "0.2-0.6", "max_tokens": 600}
                ),
                "local_only": RoutePolicy(
                    primary="ollama:llama3",
                    fallbacks=[],
                    constraints={"temperature": "0.7"}
                ),
                "default": RoutePolicy(
                    primary="openai:gpt-3.5-turbo",
                    fallbacks=["anthropic:claude-3-haiku", "ollama:llama3"],
                    constraints={"temperature": "0.7", "max_tokens": 500}
                )
            },
            failure_policy={
                "escalate_to_human_approval": True,
                "max_retries": 3,
                "retry_delay": 1.0
            }
        )


class Router:
    """
    LLM Router with intelligent routing and fallback logic.
    Routes requests based on task tags, cost, latency, and capabilities.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = RouterConfig.from_yaml(config_path) if config_path else RouterConfig.default()
        self.providers: Dict[str, BaseLLM] = {}
        self._init_providers()
        self._route_history: List[Dict[str, Any]] = []
    
    def _init_providers(self):
        """Initialize available providers based on settings."""
        # Import providers lazily to avoid circular imports
        from .providers import (
            OpenAIProvider, AnthropicProvider, GoogleProvider,
            GrokProvider, OpenRouterProvider, TogetherProvider, OllamaProvider
        )
        
        if settings.openai.enabled:
            self.providers["openai"] = OpenAIProvider()
        if settings.anthropic.enabled:
            self.providers["anthropic"] = AnthropicProvider()
        if settings.google.enabled:
            self.providers["google"] = GoogleProvider()
        if settings.grok.enabled:
            self.providers["grok"] = GrokProvider()
        if settings.openrouter.enabled:
            self.providers["openrouter"] = OpenRouterProvider()
        if settings.together.enabled:
            self.providers["together"] = TogetherProvider()
        if settings.ollama.base_url:
            self.providers["ollama"] = OllamaProvider()
    
    def generate(
        self,
        messages: List[Message],
        task_tag: str = "default",
        tools: Optional[List[Tool]] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False,
        timeout: Optional[int] = None,
        **kwargs
    ) -> CompletionResponse:
        """
        Generate completion with intelligent routing and fallback.
        
        Args:
            messages: Conversation history
            task_tag: Task tag for routing policy selection
            tools: Available tools
            system_prompt: System instruction
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            json_mode: Force JSON output
            timeout: Request timeout
            **kwargs: Additional provider-specific parameters
        
        Returns:
            CompletionResponse from successful provider
        """
        # Get routing policy
        policy = self.config.policies.get(task_tag, self.config.policies["default"])
        
        # Apply policy constraints if not explicitly set
        if temperature is None:
            temp_range = policy.temperature_range
            temperature = random.uniform(temp_range[0], temp_range[1])
        if max_tokens is None:
            max_tokens = policy.max_tokens
        
        # Build candidate list
        candidates = self._build_candidate_list(policy)
        
        # Try each candidate with fallback
        last_error = None
        for provider_spec, model in candidates:
            provider = self.providers.get(provider_spec)
            if not provider:
                logger.warning(f"Provider {provider_spec} not available")
                continue
            
            try:
                # Log route decision
                self._log_route(task_tag, provider_spec, model, "attempt")
                
                # Make request
                start_time = time.time()
                response = provider.generate(
                    model=model,
                    messages=messages,
                    tools=tools,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_mode=json_mode,
                    timeout=timeout,
                    **kwargs
                )
                
                # Add routing metadata
                response.latency_ms = (time.time() - start_time) * 1000
                response.provider = provider_spec
                response.model = model
                response.metadata["task_tag"] = task_tag
                response.metadata["route"] = f"{provider_spec}:{model}"
                
                # Log success
                self._log_route(task_tag, provider_spec, model, "success", response.latency_ms)
                
                return response
                
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider_spec}:{model} failed: {e}")
                self._log_route(task_tag, provider_spec, model, "failed", error=str(e))
                
                # Apply retry delay
                if self.config.failure_policy.get("retry_delay"):
                    time.sleep(self.config.failure_policy["retry_delay"])
                
                continue
        
        # All providers failed
        if self.config.failure_policy.get("escalate_to_human_approval"):
            logger.error(f"All providers failed for task {task_tag}, escalating to human approval")
            # This would integrate with the approval system
            raise RuntimeError(f"All providers failed, human approval required: {last_error}")
        
        raise RuntimeError(f"All providers failed: {last_error}")
    
    def stream(
        self,
        messages: List[Message],
        task_tag: str = "default",
        tools: Optional[List[Tool]] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False,
        timeout: Optional[int] = None,
        **kwargs
    ) -> Iterator[StreamDelta]:
        """
        Stream completion with intelligent routing and fallback.
        
        Similar to generate but returns an iterator of deltas.
        """
        # Get routing policy
        policy = self.config.policies.get(task_tag, self.config.policies["default"])
        
        # Apply policy constraints
        if temperature is None:
            temp_range = policy.temperature_range
            temperature = random.uniform(temp_range[0], temp_range[1])
        if max_tokens is None:
            max_tokens = policy.max_tokens
        
        # Build candidate list
        candidates = self._build_candidate_list(policy)
        
        # Try each candidate
        last_error = None
        for provider_spec, model in candidates:
            provider = self.providers.get(provider_spec)
            if not provider:
                continue
            
            try:
                # Log route decision
                self._log_route(task_tag, provider_spec, model, "stream_attempt")
                
                # Stream request
                for delta in provider.stream(
                    model=model,
                    messages=messages,
                    tools=tools,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_mode=json_mode,
                    timeout=timeout,
                    **kwargs
                ):
                    yield delta
                
                # Log success
                self._log_route(task_tag, provider_spec, model, "stream_success")
                return
                
            except Exception as e:
                last_error = e
                logger.warning(f"Stream provider {provider_spec}:{model} failed: {e}")
                self._log_route(task_tag, provider_spec, model, "stream_failed", error=str(e))
                continue
        
        # All providers failed
        raise RuntimeError(f"All stream providers failed: {last_error}")
    
    def _build_candidate_list(self, policy: RoutePolicy) -> List[Tuple[str, str]]:
        """Build list of (provider, model) candidates from policy."""
        candidates = []
        
        # Parse primary
        if ":" in policy.primary:
            provider, model = policy.primary.split(":", 1)
            candidates.append((provider, model))
        
        # Parse fallbacks
        for fallback in policy.fallbacks:
            if ":" in fallback:
                provider, model = fallback.split(":", 1)
                candidates.append((provider, model))
        
        return candidates
    
    def _log_route(
        self,
        task_tag: str,
        provider: str,
        model: str,
        status: str,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None
    ):
        """Log routing decision for observability."""
        entry = {
            "timestamp": time.time(),
            "task_tag": task_tag,
            "provider": provider,
            "model": model,
            "status": status,
            "latency_ms": latency_ms,
            "error": error
        }
        self._route_history.append(entry)
        
        # Keep history bounded
        if len(self._route_history) > 1000:
            self._route_history = self._route_history[-500:]
    
    def get_route_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        if not self._route_history:
            return {}
        
        stats = {
            "total_requests": len([e for e in self._route_history if "attempt" in e["status"]]),
            "success_rate": 0,
            "avg_latency_ms": 0,
            "provider_stats": {}
        }
        
        successes = [e for e in self._route_history if e["status"] == "success"]
        if successes:
            stats["success_rate"] = len(successes) / stats["total_requests"]
            latencies = [e["latency_ms"] for e in successes if e["latency_ms"]]
            if latencies:
                stats["avg_latency_ms"] = sum(latencies) / len(latencies)
        
        # Per-provider stats
        for entry in self._route_history:
            provider = entry["provider"]
            if provider not in stats["provider_stats"]:
                stats["provider_stats"][provider] = {
                    "attempts": 0,
                    "successes": 0,
                    "failures": 0
                }
            
            if "attempt" in entry["status"]:
                stats["provider_stats"][provider]["attempts"] += 1
            elif entry["status"] == "success":
                stats["provider_stats"][provider]["successes"] += 1
            elif "failed" in entry["status"]:
                stats["provider_stats"][provider]["failures"] += 1
        
        return stats
