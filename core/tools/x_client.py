"""
X/Twitter client with v2 API support and proper OAuth scopes.
Handles posting, media upload, rate limiting, and idempotency.
"""

import base64
import hashlib
import json
import logging
import mimetypes
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import requests
from requests_oauthlib import OAuth2Session

from ...settings import settings

logger = logging.getLogger(__name__)


@dataclass
class XPost:
    """Represents a post to X/Twitter."""
    text: str
    media_ids: List[str] = None
    reply_to_id: Optional[str] = None
    quote_tweet_id: Optional[str] = None
    poll_options: Optional[List[str]] = None
    poll_duration_minutes: Optional[int] = None
    
    def to_v2_payload(self) -> Dict[str, Any]:
        """Convert to v2 API payload."""
        payload = {"text": self.text}
        
        if self.media_ids:
            payload["media"] = {"media_ids": self.media_ids}
        
        if self.reply_to_id:
            payload["reply"] = {"in_reply_to_tweet_id": self.reply_to_id}
        
        if self.quote_tweet_id:
            payload["quote_tweet_id"] = self.quote_tweet_id
        
        if self.poll_options:
            payload["poll"] = {
                "options": self.poll_options,
                "duration_minutes": self.poll_duration_minutes or 60
            }
        
        return payload


class XClient:
    """
    X/Twitter API v2 client with media support.
    Implements proper OAuth2 with required scopes.
    """
    
    V2_BASE_URL = "https://api.twitter.com/2"
    V1_BASE_URL = "https://api.twitter.com/1.1"
    UPLOAD_URL = "https://upload.twitter.com/1.1"
    
    REQUIRED_SCOPES = ["tweet.write", "tweet.read", "users.read", "offline.access"]
    MEDIA_SCOPES = ["tweet.write", "tweet.read", "users.read", "offline.access"]
    
    def __init__(self):
        self.client_id = settings.x.client_id
        self.client_secret = settings.x.client_secret
        self.redirect_uri = settings.x.redirect_uri
        self.access_token = settings.x.access_token
        self.refresh_token = settings.x.refresh_token
        self.bearer_token = settings.x.bearer_token
        
        self._session = None
        self._rate_limit_remaining = {}
        self._rate_limit_reset = {}
    
    @property
    def session(self) -> OAuth2Session:
        """Get or create OAuth2 session."""
        if not self._session and self.access_token:
            self._session = OAuth2Session(
                client_id=self.client_id,
                token={
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                    "token_type": "Bearer"
                }
            )
        return self._session
    
    def get_auth_url(self) -> str:
        """Get OAuth2 authorization URL with required scopes."""
        oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.REQUIRED_SCOPES + self.MEDIA_SCOPES
        )
        auth_url, state = oauth.authorization_url(
            "https://twitter.com/i/oauth2/authorize",
            code_challenge_method="S256",
            code_challenge=self._generate_code_challenge()
        )
        return auth_url
    
    def _generate_code_challenge(self) -> str:
        """Generate PKCE code challenge."""
        verifier = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf-8').rstrip('=')
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode('utf-8').rstrip('=')
        return challenge
    
    def post_tweet(
        self,
        text: str,
        media_paths: Optional[List[str]] = None,
        reply_to_id: Optional[str] = None,
        dry_run: bool = False,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Post a tweet using v2 API with optional media.
        
        Args:
            text: Tweet text (max 280 chars)
            media_paths: List of local media file paths
            reply_to_id: Tweet ID to reply to
            dry_run: If True, validate but don't post
            idempotency_key: Key for idempotent requests
        
        Returns:
            Tweet data from API response
        """
        
        # Check rate limits
        if not self._check_rate_limit("tweets"):
            raise RuntimeError("Rate limit exceeded for tweets")
        
        # Validate text length
        if len(text) > 280:
            raise ValueError(f"Tweet text too long: {len(text)} > 280")
        
        # Upload media if provided
        media_ids = []
        if media_paths:
            for path in media_paths:
                media_id = self.upload_media(path)
                if media_id:
                    media_ids.append(media_id)
        
        # Build post
        post = XPost(
            text=text,
            media_ids=media_ids if media_ids else None,
            reply_to_id=reply_to_id
        )
        
        if dry_run:
            logger.info(f"[DRY RUN] Would post: {post.to_v2_payload()}")
            return {"dry_run": True, "payload": post.to_v2_payload()}
        
        # Make request
        headers = self._get_headers()
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key or str(uuid.uuid4())
        
        try:
            response = requests.post(
                f"{self.V2_BASE_URL}/tweets",
                headers=headers,
                json=post.to_v2_payload(),
                timeout=10
            )
            
            # Update rate limits from headers
            self._update_rate_limits(response.headers, "tweets")
            
            if response.status_code == 201:
                data = response.json()
                logger.info(f"Successfully posted tweet: {data.get('data', {}).get('id')}")
                return data
            elif response.status_code == 429:
                reset_time = response.headers.get("x-rate-limit-reset")
                logger.warning(f"Rate limited. Reset at {reset_time}")
                raise RuntimeError(f"Rate limited until {reset_time}")
            else:
                logger.error(f"Failed to post tweet: {response.status_code} - {response.text}")
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error posting tweet: {e}")
            raise
    
    def upload_media(self, file_path: str) -> Optional[str]:
        """
        Upload media using v1.1 API (still required for media).
        
        Args:
            file_path: Path to media file
        
        Returns:
            Media ID string if successful
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"Media file not found: {file_path}")
            return None
        
        # Get file info
        file_size = file_path.stat().st_size
        media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        
        # Check file size (max 5MB for images, 15MB for GIFs, 512MB for videos)
        max_size = 512 * 1024 * 1024  # 512MB max
        if file_size > max_size:
            logger.error(f"File too large: {file_size} > {max_size}")
            return None
        
        try:
            # INIT
            init_params = {
                "command": "INIT",
                "total_bytes": file_size,
                "media_type": media_type,
                "media_category": "tweet_image" if "image" in media_type else "tweet_video"
            }
            
            init_response = requests.post(
                f"{self.UPLOAD_URL}/media/upload.json",
                headers=self._get_headers(),
                data=init_params,
                timeout=10
            )
            init_response.raise_for_status()
            media_id = init_response.json()["media_id_string"]
            
            # APPEND (chunk upload for large files)
            chunk_size = 5 * 1024 * 1024  # 5MB chunks
            with open(file_path, "rb") as f:
                segment_index = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    append_params = {
                        "command": "APPEND",
                        "media_id": media_id,
                        "segment_index": segment_index
                    }
                    files = {"media": chunk}
                    
                    append_response = requests.post(
                        f"{self.UPLOAD_URL}/media/upload.json",
                        headers=self._get_headers(),
                        data=append_params,
                        files=files,
                        timeout=30
                    )
                    append_response.raise_for_status()
                    segment_index += 1
            
            # FINALIZE
            finalize_params = {
                "command": "FINALIZE",
                "media_id": media_id
            }
            
            finalize_response = requests.post(
                f"{self.UPLOAD_URL}/media/upload.json",
                headers=self._get_headers(),
                data=finalize_params,
                timeout=10
            )
            finalize_response.raise_for_status()
            
            # Check processing status if needed
            finalize_data = finalize_response.json()
            if "processing_info" in finalize_data:
                media_id = self._wait_for_processing(media_id)
            
            logger.info(f"Successfully uploaded media: {media_id}")
            return media_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading media: {e}")
            return None
    
    def _wait_for_processing(self, media_id: str, max_wait: int = 60) -> str:
        """Wait for media processing to complete."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_response = requests.get(
                f"{self.UPLOAD_URL}/media/upload.json",
                headers=self._get_headers(),
                params={"command": "STATUS", "media_id": media_id}
            )
            
            if status_response.status_code == 200:
                data = status_response.json()
                state = data.get("processing_info", {}).get("state")
                
                if state == "succeeded":
                    return media_id
                elif state == "failed":
                    error = data.get("processing_info", {}).get("error")
                    raise RuntimeError(f"Media processing failed: {error}")
                
                # Still processing, wait
                check_after = data.get("processing_info", {}).get("check_after_secs", 1)
                time.sleep(check_after)
            else:
                break
        
        raise RuntimeError(f"Media processing timeout for {media_id}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        if self.access_token:
            return {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        elif self.bearer_token:
            return {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            }
        else:
            raise RuntimeError("No authentication configured")
    
    def _check_rate_limit(self, endpoint: str) -> bool:
        """Check if we're within rate limits."""
        if endpoint in self._rate_limit_remaining:
            if self._rate_limit_remaining[endpoint] <= 0:
                reset_time = self._rate_limit_reset.get(endpoint, 0)
                if time.time() < reset_time:
                    return False
        return True
    
    def _update_rate_limits(self, headers: Dict[str, str], endpoint: str):
        """Update rate limit tracking from response headers."""
        remaining = headers.get("x-rate-limit-remaining")
        reset = headers.get("x-rate-limit-reset")
        
        if remaining:
            self._rate_limit_remaining[endpoint] = int(remaining)
        if reset:
            self._rate_limit_reset[endpoint] = int(reset)
    
    def delete_tweet(self, tweet_id: str) -> bool:
        """Delete a tweet by ID."""
        try:
            response = requests.delete(
                f"{self.V2_BASE_URL}/tweets/{tweet_id}",
                headers=self._get_headers(),
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error deleting tweet {tweet_id}: {e}")
            return False
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user info."""
        try:
            response = requests.get(
                f"{self.V2_BASE_URL}/users/me",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {}
