"""
Approval system for high-impact actions.
Queues actions for human review and tracks decisions.
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from threading import Lock

from ...settings import settings

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ApprovalRequest:
    """Represents an action requiring approval."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ""
    description: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    requester: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    decided_at: Optional[float] = None
    decided_by: Optional[str] = None
    decision_reason: Optional[str] = None
    expires_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["risk_level"] = self.risk_level.value
        data["status"] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalRequest":
        """Create from dictionary."""
        data["risk_level"] = RiskLevel(data["risk_level"])
        data["status"] = ApprovalStatus(data["status"])
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if request has expired."""
        if self.expires_at and time.time() > self.expires_at:
            return True
        return False


class ApprovalManager:
    """
    Manages approval queue and decisions.
    Integrates with Discord/Telegram for interactive approvals.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "./data/approvals.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.requests: Dict[str, ApprovalRequest] = {}
        self._lock = Lock()
        self._callbacks: Dict[str, Callable] = {}
        
        # Load existing requests
        self._load_requests()
    
    def request_approval(
        self,
        action_type: str,
        description: str,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        requester: str = "system",
        payload: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = 3600,
        callback: Optional[Callable] = None
    ) -> ApprovalRequest:
        """
        Request approval for an action.
        
        Args:
            action_type: Type of action (e.g., "post_tweet", "push_code")
            description: Human-readable description
            risk_level: Risk level of the action
            requester: Who/what is requesting
            payload: Action-specific data
            ttl_seconds: Time to live in seconds
            callback: Function to call when decision is made
        
        Returns:
            ApprovalRequest object
        """
        with self._lock:
            # Check auto-approval policy
            if self._should_auto_approve(action_type, risk_level):
                return self._create_auto_approved(
                    action_type, description, risk_level, requester, payload
                )
            
            # Create request
            request = ApprovalRequest(
                action_type=action_type,
                description=description,
                risk_level=risk_level,
                requester=requester,
                payload=payload or {},
                expires_at=time.time() + ttl_seconds if ttl_seconds else None
            )
            
            # Store request
            self.requests[request.id] = request
            
            # Register callback if provided
            if callback:
                self._callbacks[request.id] = callback
            
            # Persist
            self._save_requests()
            
            # Notify approvers (would integrate with Discord/Telegram)
            self._notify_approvers(request)
            
            return request
    
    def approve(
        self,
        request_id: str,
        approver: str = "human",
        reason: Optional[str] = None
    ) -> bool:
        """Approve a request."""
        return self._make_decision(
            request_id, 
            ApprovalStatus.APPROVED,
            approver,
            reason
        )
    
    def deny(
        self,
        request_id: str,
        approver: str = "human",
        reason: Optional[str] = None
    ) -> bool:
        """Deny a request."""
        return self._make_decision(
            request_id,
            ApprovalStatus.DENIED,
            approver,
            reason
        )
    
    def _make_decision(
        self,
        request_id: str,
        status: ApprovalStatus,
        approver: str,
        reason: Optional[str]
    ) -> bool:
        """Make a decision on a request."""
        with self._lock:
            request = self.requests.get(request_id)
            if not request:
                return False
            
            if request.status != ApprovalStatus.PENDING:
                return False
            
            # Update request
            request.status = status
            request.decided_at = time.time()
            request.decided_by = approver
            request.decision_reason = reason
            
            # Persist
            self._save_requests()
            
            # Execute callback if registered
            if request_id in self._callbacks:
                callback = self._callbacks.pop(request_id)
                try:
                    callback(request)
                except Exception as e:
                    # Log but don't fail
                    print(f"Callback error: {e}")
            
            return True
    
    def get_pending(self) -> List[ApprovalRequest]:
        """Get all pending requests."""
        with self._lock:
            # Clean up expired requests
            self._expire_old_requests()
            
            return [
                r for r in self.requests.values()
                if r.status == ApprovalStatus.PENDING
            ]
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a specific request."""
        return self.requests.get(request_id)
    
    def _should_auto_approve(self, action_type: str, risk_level: RiskLevel) -> bool:
        """Check if action should be auto-approved."""
        if not settings.policy.auto_approve_low_risk:
            return False
        
        # Auto-approve low risk actions
        if risk_level == RiskLevel.LOW:
            return True
        
        # Add more sophisticated logic here
        # e.g., check action type, time of day, etc.
        
        return False
    
    def _create_auto_approved(
        self,
        action_type: str,
        description: str,
        risk_level: RiskLevel,
        requester: str,
        payload: Optional[Dict[str, Any]]
    ) -> ApprovalRequest:
        """Create an auto-approved request."""
        request = ApprovalRequest(
            action_type=action_type,
            description=description,
            risk_level=risk_level,
            requester=requester,
            payload=payload or {},
            status=ApprovalStatus.AUTO_APPROVED,
            decided_at=time.time(),
            decided_by="system",
            decision_reason="Auto-approved per policy"
        )
        
        # Store for audit
        self.requests[request.id] = request
        self._save_requests()
        
        return request
    
    def _expire_old_requests(self):
        """Mark expired requests."""
        now = time.time()
        for request in self.requests.values():
            if (request.status == ApprovalStatus.PENDING and 
                request.is_expired()):
                request.status = ApprovalStatus.EXPIRED
    
    def _notify_approvers(self, request: ApprovalRequest):
        """Notify approvers of new request."""
        # This would integrate with Discord/Telegram
        # For now, just print
        print(f"\n[APPROVAL REQUIRED] {request.id}")
        print(f"Type: {request.action_type}")
        print(f"Risk: {request.risk_level.value}")
        print(f"Description: {request.description}")
        print(f"Approve: approval_manager.approve('{request.id}')")
        print(f"Deny: approval_manager.deny('{request.id}')\n")
    
    def _save_requests(self):
        """Persist requests to disk."""
        try:
            data = {
                rid: r.to_dict() 
                for rid, r in self.requests.items()
            }
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving approvals: {e}")
    
    def _load_requests(self):
        """Load requests from disk."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path) as f:
                data = json.load(f)
            
            self.requests = {
                rid: ApprovalRequest.from_dict(rdata)
                for rid, rdata in data.items()
            }
        except Exception as e:
            print(f"Error loading approvals: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get approval statistics."""
        with self._lock:
            total = len(self.requests)
            if total == 0:
                return {}
            
            status_counts = {}
            risk_counts = {}
            
            for request in self.requests.values():
                status_counts[request.status.value] = status_counts.get(request.status.value, 0) + 1
                risk_counts[request.risk_level.value] = risk_counts.get(request.risk_level.value, 0) + 1
            
            return {
                "total_requests": total,
                "by_status": status_counts,
                "by_risk": risk_counts,
                "approval_rate": status_counts.get("approved", 0) / total if total > 0 else 0,
                "auto_approval_rate": status_counts.get("auto_approved", 0) / total if total > 0 else 0
            }


# Global approval manager instance
approval_manager = ApprovalManager()
