"""
Token bucket rate limiter per client and per agent.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class TokenBucket:
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(default=0)
    last_refill: float = field(default_factory=time.time)

    def allow(self, tokens: int = 1) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiter:
    def __init__(self):
        self.buckets: Dict[Tuple[str, str], TokenBucket] = {}

    def configure(self, client: str, agent: str, capacity: int, per_seconds: int):
        key = (client, agent)
        self.buckets[key] = TokenBucket(capacity=capacity, refill_rate=capacity / per_seconds, tokens=capacity)

    def check(self, client: str, agent: str, cost: int = 1) -> bool:
        key = (client, agent)
        if key not in self.buckets:
            # default: 60 per minute
            self.configure(client, agent, capacity=60, per_seconds=60)
        return self.buckets[key].allow(cost)

