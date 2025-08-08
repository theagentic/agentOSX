"""
Content filters using regexes and simple category rules.
Blocks unsafe or banned topics before posting.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class FilterRule:
    pattern: str
    description: str
    category: str


class ContentFilter:
    """Simple content filter implementation."""

    def __init__(self, banned_topics: List[str] | None = None):
        self.rules: List[FilterRule] = []
        # Default patterns
        defaults = [
            (r"(?i)(api[_-]?key|secret|token)[=:]\s*[A-Za-z0-9-_]{8,}", "Secrets leakage", "secrets"),
            (r"(?i)password\s*[:=]", "Password leakage", "secrets"),
            (r"(?i)politic(s|al)", "Politics banned", "policy"),
            (r"(?i)religion|religious", "Religion banned", "policy"),
            (r"(?i)adult|nsfw|porn", "Adult content banned", "policy"),
        ]
        for pat, desc, cat in defaults:
            self.rules.append(FilterRule(pattern=pat, description=desc, category=cat))
        
        # Add topic-specific bans
        if banned_topics:
            for topic in banned_topics:
                self.rules.append(FilterRule(pattern=rf"(?i){re.escape(topic)}", description=f"Banned topic: {topic}", category="topic"))

    def check(self, text: str) -> Tuple[bool, List[FilterRule]]:
        """Return (allowed, violations)."""
        violations: List[FilterRule] = []
        for rule in self.rules:
            if re.search(rule.pattern, text):
                violations.append(rule)
        return (len(violations) == 0, violations)

