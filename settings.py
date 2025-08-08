"""
Central configuration management for agentOS.
Reads from environment variables and provides typed access to settings.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class LLMProviderConfig:
    """Configuration for an LLM provider."""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    organization: Optional[str] = None
    enabled: bool = False
    
    def __post_init__(self):
        self.enabled = bool(self.api_key)


@dataclass
class XConfig:
    """X/Twitter API configuration."""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: str = "http://localhost:8080/callback"
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    bearer_token: Optional[str] = None  # For app-only auth
    
    @property
    def has_user_auth(self) -> bool:
        """Check if user authentication is configured."""
        return bool(self.access_token)
    
    @property
    def has_app_auth(self) -> bool:
        """Check if app authentication is configured."""
        return bool(self.bearer_token or (self.client_id and self.client_secret))
    
    @property
    def required_scopes(self) -> list[str]:
        """Required OAuth2 scopes for full functionality."""
        return ["tweet.write", "tweet.read", "users.read", "offline.access"]
    
    @property
    def media_scopes(self) -> list[str]:
        """Additional scopes for media functionality."""
        return ["tweet.write", "tweet.read", "users.read", "offline.access"]


@dataclass
class SocialConfig:
    """Social platform configurations."""
    discord_bot_token: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    
    @property
    def discord_enabled(self) -> bool:
        return bool(self.discord_bot_token)
    
    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token)


@dataclass
class DevelopmentConfig:
    """Development tool configurations."""
    github_token: Optional[str] = None
    
    @property
    def github_enabled(self) -> bool:
        return bool(self.github_token)


@dataclass
class ObservabilityConfig:
    """Observability and monitoring configuration."""
    trace_enabled: bool = True
    metrics_enabled: bool = True
    eval_enabled: bool = True
    redact_pii: bool = True
    trace_sample_rate: float = 1.0
    log_level: str = "INFO"


@dataclass
class PolicyConfig:
    """Policy and governance configuration."""
    approval_required: bool = True
    content_filter_enabled: bool = True
    rate_limit_enabled: bool = True
    dry_run_mode: bool = False
    auto_approve_low_risk: bool = False


@dataclass
class Settings:
    """Main settings container."""
    # LLM Providers
    openai: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    anthropic: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    google: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    grok: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    openrouter: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    together: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    ollama: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    
    # Social Platforms
    x: XConfig = field(default_factory=XConfig)
    social: SocialConfig = field(default_factory=SocialConfig)
    
    # Development
    dev: DevelopmentConfig = field(default_factory=DevelopmentConfig)
    
    # System
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    
    # Runtime
    environment: str = "development"
    debug: bool = False
    plugin_dir: str = "./plugins"
    data_dir: str = "./data"
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls(
            openai=LLMProviderConfig(
                api_key=os.getenv("OPENAI_API_KEY"),
                organization=os.getenv("OPENAI_ORGANIZATION"),
                base_url=os.getenv("OPENAI_BASE_URL")
            ),
            anthropic=LLMProviderConfig(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                base_url=os.getenv("ANTHROPIC_BASE_URL")
            ),
            google=LLMProviderConfig(
                api_key=os.getenv("GOOGLE_API_KEY"),
                base_url=os.getenv("GOOGLE_BASE_URL")
            ),
            grok=LLMProviderConfig(
                api_key=os.getenv("GROK_API_KEY"),
                base_url=os.getenv("GROK_BASE_URL", "https://api.x.ai/v1")
            ),
            openrouter=LLMProviderConfig(
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            ),
            together=LLMProviderConfig(
                api_key=os.getenv("TOGETHER_API_KEY"),
                base_url=os.getenv("TOGETHER_BASE_URL", "https://api.together.xyz/v1")
            ),
            ollama=LLMProviderConfig(
                base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434")
            ),
            x=XConfig(
                client_id=os.getenv("X_CLIENT_ID"),
                client_secret=os.getenv("X_CLIENT_SECRET"),
                redirect_uri=os.getenv("X_REDIRECT_URI", "http://localhost:8080/callback"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                refresh_token=os.getenv("X_REFRESH_TOKEN"),
                bearer_token=os.getenv("X_BEARER_TOKEN")
            ),
            social=SocialConfig(
                discord_bot_token=os.getenv("DISCORD_BOT_TOKEN"),
                telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN")
            ),
            dev=DevelopmentConfig(
                github_token=os.getenv("GITHUB_TOKEN")
            ),
            observability=ObservabilityConfig(
                trace_enabled=os.getenv("TRACE_ENABLED", "true").lower() == "true",
                metrics_enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
                eval_enabled=os.getenv("EVAL_ENABLED", "true").lower() == "true",
                redact_pii=os.getenv("REDACT_PII", "true").lower() == "true",
                trace_sample_rate=float(os.getenv("TRACE_SAMPLE_RATE", "1.0")),
                log_level=os.getenv("LOG_LEVEL", "INFO")
            ),
            policy=PolicyConfig(
                approval_required=os.getenv("APPROVAL_REQUIRED", "true").lower() == "true",
                content_filter_enabled=os.getenv("CONTENT_FILTER_ENABLED", "true").lower() == "true",
                rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
                dry_run_mode=os.getenv("DRY_RUN_MODE", "false").lower() == "true",
                auto_approve_low_risk=os.getenv("AUTO_APPROVE_LOW_RISK", "false").lower() == "true"
            ),
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            plugin_dir=os.getenv("PLUGIN_DIR", "./plugins"),
            data_dir=os.getenv("DATA_DIR", "./data")
        )
    
    def get_enabled_providers(self) -> Dict[str, LLMProviderConfig]:
        """Get all enabled LLM providers."""
        providers = {
            "openai": self.openai,
            "anthropic": self.anthropic,
            "google": self.google,
            "grok": self.grok,
            "openrouter": self.openrouter,
            "together": self.together,
            "ollama": self.ollama
        }
        return {k: v for k, v in providers.items() if v.enabled}
    
    def validate(self) -> list[str]:
        """Validate settings and return list of warnings."""
        warnings = []
        
        # Check if at least one LLM provider is configured
        if not self.get_enabled_providers():
            warnings.append("No LLM providers configured. At least one provider API key is required.")
        
        # Check X/Twitter configuration
        if self.x.has_user_auth and not self.x.access_token:
            warnings.append("X/Twitter user auth configured but no access token provided.")
        
        # Check social platform configuration
        if not self.social.discord_enabled and not self.social.telegram_enabled:
            warnings.append("No social platforms configured. Consider enabling Discord or Telegram.")
        
        # Check observability settings
        if self.environment == "production" and not self.observability.trace_enabled:
            warnings.append("Tracing disabled in production environment. Consider enabling for monitoring.")
        
        return warnings


# Global settings instance
settings = Settings.from_env()

# Validate on import
warnings = settings.validate()
if warnings and settings.debug:
    import sys
    for warning in warnings:
        print(f"[Settings Warning] {warning}", file=sys.stderr)
