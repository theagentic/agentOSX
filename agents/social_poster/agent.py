"""
Social poster agent that manages social media presence.
Integrates with X/Twitter, Discord, and Telegram.
"""

import yaml
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

from ...core.llm.router import Router
from ...core.llm.base import Message, Role
from ...core.tools.x_client import XClient
from ...core.policy.approvals import approval_manager, RiskLevel, ApprovalStatus
from ...settings import settings


class SocialPosterAgent:
    """
    Agent for managing social media posts with approval workflow.
    """
    
    def __init__(self, persona_path: Optional[str] = None):
        # Load persona
        persona_path = Path(persona_path or Path(__file__).parent / "persona.yaml")
        with open(persona_path) as f:
            self.persona = yaml.safe_load(f)
        
        # Initialize components
        self.router = Router()
        self.x_client = XClient() if settings.x.has_user_auth else None
        
        # Build system prompt
        self.system_prompt = self._build_system_prompt()
        
        # Track posting history
        self.post_history = []
    
    def _build_system_prompt(self) -> str:
        """Build system prompt from persona."""
        prompt = self.persona["system_prompt"]
        
        # Substitute variables
        prompt = prompt.replace("{name}", self.persona["name"])
        prompt = prompt.replace("{style_guide}", str(self.persona["style_guide"]))
        prompt = prompt.replace("{banned_topics}", str(self.persona["topic_filters"]["banned"]))
        
        return prompt
    
    def generate_post(
        self,
        topic: Optional[str] = None,
        context: Optional[str] = None,
        media_paths: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a social media post.
        
        Args:
            topic: Topic to post about
            context: Additional context
            media_paths: Paths to media files
        
        Returns:
            Generated post data
        """
        # Build prompt
        messages = []
        
        if topic:
            prompt = f"Generate a social media post about: {topic}"
            if context:
                prompt += f"\n\nContext: {context}"
        else:
            prompt = "Generate an engaging social media post about our latest updates or a relevant technical topic."
        
        messages.append(Message(role=Role.USER, content=prompt))
        
        # Generate with router
        response = self.router.generate(
            messages=messages,
            task_tag="creative_posting",
            system_prompt=self.system_prompt,
            max_tokens=300,
            temperature=0.9
        )
        
        post_text = response.message.content
        
        # Validate length
        if len(post_text) > 280:
            # Truncate intelligently
            post_text = self._truncate_post(post_text)
        
        return {
            "text": post_text,
            "media_paths": media_paths,
            "generated_at": time.time(),
            "model_used": f"{response.provider}:{response.model}"
        }
    
    def post_with_approval(
        self,
        text: str,
        media_paths: Optional[List[str]] = None,
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """
        Post to X with approval workflow.
        
        Args:
            text: Post text
            media_paths: Media file paths
            auto_approve: Skip approval if True
        
        Returns:
            Post result
        """
        if not self.x_client:
            return {"error": "X client not configured"}
        
        # Determine risk level
        risk_level = self._assess_risk(text)
        
        # Check if approval needed
        if not auto_approve and settings.policy.approval_required:
            # Request approval
            request = approval_manager.request_approval(
                action_type="post_tweet",
                description=f"Post to X: {text[:100]}...",
                risk_level=risk_level,
                requester="social_poster",
                payload={
                    "text": text,
                    "media_paths": media_paths
                },
                ttl_seconds=3600
            )
            
            # For demo, we'll check status
            if request.status == ApprovalStatus.AUTO_APPROVED:
                print(f"Post auto-approved: {request.id}")
            else:
                print(f"Approval requested: {request.id}")
                print(f"Waiting for approval... (timeout in 1 hour)")
                
                # In real implementation, this would be async
                # For demo, we'll just return the request
                return {
                    "approval_request": request.id,
                    "status": "pending_approval",
                    "text": text
                }
        
        # Post to X
        try:
            # Generate idempotency key
            idempotency_key = str(uuid.uuid4())
            
            # Post with rate limiting and retries
            result = self.x_client.post_tweet(
                text=text,
                media_paths=media_paths,
                idempotency_key=idempotency_key,
                dry_run=settings.policy.dry_run_mode
            )
            
            # Track in history
            self.post_history.append({
                "text": text,
                "result": result,
                "timestamp": time.time()
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    def _assess_risk(self, text: str) -> RiskLevel:
        """Assess risk level of post content."""
        # Check for banned topics
        banned = self.persona["topic_filters"]["banned"]
        text_lower = text.lower()
        
        for topic in banned:
            if topic.lower() in text_lower:
                return RiskLevel.HIGH
        
        # Check for sensitive patterns
        sensitive_patterns = ["api", "key", "secret", "password", "token"]
        for pattern in sensitive_patterns:
            if pattern in text_lower:
                return RiskLevel.CRITICAL
        
        # Default to medium for public posts
        return RiskLevel.MEDIUM
    
    def _truncate_post(self, text: str, max_length: int = 277) -> str:
        """Truncate post intelligently to fit length limit."""
        if len(text) <= max_length:
            return text
        
        # Try to break at sentence boundary
        sentences = text.split(". ")
        truncated = ""
        
        for sentence in sentences:
            if len(truncated) + len(sentence) + 3 <= max_length:  # +3 for "..."
                truncated += sentence + ". "
            else:
                break
        
        if truncated:
            return truncated.rstrip() + "..."
        
        # Fallback to simple truncation
        return text[:max_length] + "..."
    
    def schedule_post(
        self,
        text: str,
        schedule_time: float,
        media_paths: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Schedule a post for later.
        
        Args:
            text: Post text
            schedule_time: Unix timestamp for posting
            media_paths: Media file paths
        
        Returns:
            Schedule confirmation
        """
        # This would integrate with a scheduler service
        # For now, just return confirmation
        return {
            "scheduled": True,
            "text": text,
            "schedule_time": schedule_time,
            "media_paths": media_paths
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get posting statistics."""
        return {
            "total_posts": len(self.post_history),
            "recent_posts": self.post_history[-5:],
            "persona": self.persona["name"]
        }
