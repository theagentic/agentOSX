#!/usr/bin/env python3
"""
Social posting demo showing the complete flow:
1. Generate a post using LLM router
2. Request approval 
3. Post to X/Twitter upon approval
4. Show metrics and denial path
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.social_poster.agent import SocialPosterAgent
from core.policy.approvals import approval_manager, ApprovalStatus
from settings import settings


def main():
    """Run social posting demo."""
    
    print("=" * 60)
    print("AgentOS Social Posting Demo")
    print("=" * 60)
    
    # Check configuration
    if not settings.get_enabled_providers():
        print("\n⚠️  No LLM providers configured!")
        print("Please set at least one provider API key:")
        print("  export OPENAI_API_KEY=sk-...")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        return
    
    # Initialize agent
    print("\n📤 Initializing social poster agent...")
    agent = SocialPosterAgent()
    
    # Generate a post
    print("\n✍️  Generating post about agent frameworks...")
    post_data = agent.generate_post(
        topic="the importance of plugin-based architectures in AI agent frameworks",
        context="We just released agentOS, a production-ready framework inspired by elizaOS"
    )
    
    print(f"\n📝 Generated post ({len(post_data['text'])} chars):")
    print(f"   {post_data['text']}")
    print(f"\n   Model used: {post_data['model_used']}")
    
    # Check if X client is configured
    if not settings.x.has_user_auth:
        print("\n⚠️  X/Twitter not configured. Showing approval flow only.")
        print("To enable posting, set:")
        print("  export X_ACCESS_TOKEN=...")
        print("  export X_CLIENT_ID=...")
    
    # Request approval
    print("\n🔐 Requesting approval to post...")
    result = agent.post_with_approval(
        text=post_data['text'],
        auto_approve=False  # Force approval flow
    )
    
    if "approval_request" in result:
        request_id = result["approval_request"]
        print(f"\n⏳ Approval pending: {request_id}")
        print("\nTo approve this post, you would normally:")
        print("  1. Receive notification in Discord/Telegram")
        print("  2. Review the content")
        print("  3. Reply with /approve or /deny")
        
        # Simulate approval decision
        print("\n[DEMO] Simulating approval decision...")
        time.sleep(2)
        
        # Show both paths
        print("\n--- Path 1: Approval ---")
        approval_manager.approve(request_id, approver="demo_user", reason="Content looks good")
        
        # Get the approved request
        request = approval_manager.get_request(request_id)
        if request and request.status == ApprovalStatus.APPROVED:
            print(f"✅ Approved by: {request.decided_by}")
            print(f"   Reason: {request.decision_reason}")
            
            # Now actually post (if X is configured)
            if settings.x.has_user_auth:
                print("\n📮 Posting to X...")
                post_result = agent.post_with_approval(
                    text=post_data['text'],
                    auto_approve=True  # Already approved
                )
                
                if "error" not in post_result:
                    print(f"✅ Successfully posted!")
                    if "dry_run" in post_result:
                        print("   (DRY RUN MODE - no actual post)")
                else:
                    print(f"❌ Error: {post_result['error']}")
        
        # Show denial path
        print("\n--- Path 2: Denial (Alternative) ---")
        # Create another request for denial demo
        denial_result = agent.post_with_approval(
            text="This post contains banned content about politics",
            auto_approve=False
        )
        
        if "approval_request" in denial_result:
            denial_id = denial_result["approval_request"]
            approval_manager.deny(denial_id, approver="demo_user", reason="Contains banned topics")
            
            denied_request = approval_manager.get_request(denial_id)
            if denied_request and denied_request.status == ApprovalStatus.DENIED:
                print(f"❌ Denied by: {denied_request.decided_by}")
                print(f"   Reason: {denied_request.decision_reason}")
    
    elif "error" in result:
        print(f"\n❌ Error: {result['error']}")
    
    elif result.get("dry_run"):
        print("\n✅ Post validated (DRY RUN MODE)")
        print(f"   Would post: {result['payload']}")
    
    # Show statistics
    print("\n📊 Statistics:")
    
    # Agent stats
    agent_stats = agent.get_stats()
    print(f"   Total posts: {agent_stats['total_posts']}")
    print(f"   Agent persona: {agent_stats['persona']}")
    
    # Approval stats
    approval_stats = approval_manager.get_stats()
    if approval_stats:
        print(f"\n   Approval requests: {approval_stats.get('total_requests', 0)}")
        print(f"   Approval rate: {approval_stats.get('approval_rate', 0):.1%}")
        print(f"   Auto-approval rate: {approval_stats.get('auto_approval_rate', 0):.1%}")
    
    # Router stats
    if hasattr(agent.router, 'get_route_stats'):
        route_stats = agent.router.get_route_stats()
        if route_stats:
            print(f"\n   Router requests: {route_stats.get('total_requests', 0)}")
            print(f"   Success rate: {route_stats.get('success_rate', 0):.1%}")
            print(f"   Avg latency: {route_stats.get('avg_latency_ms', 0):.0f}ms")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
