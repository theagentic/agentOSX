#!/usr/bin/env python3
"""
Quick test script to verify agentOS installation and configuration.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all core modules can be imported."""
    print("Testing imports...")
    
    try:
        import agentos
        print(f"✓ agentOS version: {agentos.__version__}")
        
        from agentos import settings
        print("✓ Settings module loaded")
        
        from agentos.core.llm import Router, Message, Role
        print("✓ LLM modules loaded")
        
        from agentos.core.policy import approval_manager
        print("✓ Policy modules loaded")
        
        from agentos.core.tools import XClient
        print("✓ Tools modules loaded")
        
        from agentos.agents import SocialPosterAgent
        print("✓ Agents loaded")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_configuration():
    """Test configuration and show status."""
    print("\nConfiguration Status:")
    
    from agentos import settings
    
    # Check LLM providers
    providers = settings.get_enabled_providers()
    if providers:
        print(f"✓ LLM Providers configured: {', '.join(providers.keys())}")
    else:
        print("✗ No LLM providers configured")
        print("  Set at least one: OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.")
    
    # Check X/Twitter
    if settings.x.has_user_auth:
        print("✓ X/Twitter user auth configured")
    elif settings.x.has_app_auth:
        print("○ X/Twitter app auth configured (limited functionality)")
    else:
        print("○ X/Twitter not configured (optional)")
    
    # Check social platforms
    if settings.social.discord_enabled:
        print("✓ Discord bot configured")
    else:
        print("○ Discord not configured (optional)")
    
    if settings.social.telegram_enabled:
        print("✓ Telegram bot configured")
    else:
        print("○ Telegram not configured (optional)")
    
    # Check policies
    print(f"\nPolicy Settings:")
    print(f"  Approval required: {settings.policy.approval_required}")
    print(f"  Content filtering: {settings.policy.content_filter_enabled}")
    print(f"  Rate limiting: {settings.policy.rate_limit_enabled}")
    print(f"  Dry run mode: {settings.policy.dry_run_mode}")
    
    # Show warnings
    warnings = settings.validate()
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  ⚠ {warning}")
    
    return len(providers) > 0


def test_basic_functionality():
    """Test basic functionality."""
    print("\nTesting basic functionality...")
    
    from agentos import settings
    
    if not settings.get_enabled_providers():
        print("⚠ Skipping functionality tests - no LLM providers configured")
        return False
    
    try:
        # Test router initialization
        from agentos.core.llm import Router
        router = Router()
        print("✓ Router initialized")
        
        # Test approval manager
        from agentos.core.policy import approval_manager
        stats = approval_manager.get_stats()
        print(f"✓ Approval manager working ({stats.get('total_requests', 0)} requests)")
        
        # Test agent initialization
        from agentos.agents import SocialPosterAgent
        agent = SocialPosterAgent()
        print("✓ Social poster agent initialized")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("agentOS Setup Test")
    print("=" * 60)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
        print("\n❌ Import test failed. Check your Python path and dependencies.")
        print("   Try: pip install -r requirements.txt")
        return 1
    
    # Test configuration
    if not test_configuration():
        print("\n⚠ Configuration incomplete. Copy .env.example to .env and add your keys.")
    
    # Test functionality
    test_basic_functionality()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Basic setup complete!")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and add your API keys")
        print("2. Run the social posting demo: python examples/social_post_demo.py")
        print("3. Check the README for more information")
    else:
        print("❌ Setup issues detected. Please check the errors above.")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
