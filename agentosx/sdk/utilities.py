"""
Utility Functions for AgentOSX SDK.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_id(prefix: str = "", length: int = 8) -> str:
    """
    Generate a unique ID.
    
    Args:
        prefix: ID prefix
        length: Hash length
        
    Returns:
        Unique ID string
    """
    timestamp = str(datetime.now().timestamp())
    hash_obj = hashlib.sha256(timestamp.encode())
    hash_str = hash_obj.hexdigest()[:length]
    
    if prefix:
        return f"{prefix}_{hash_str}"
    return hash_str


def safe_json_dumps(obj: Any) -> str:
    """
    Safely serialize object to JSON.
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON string
    """
    try:
        return json.dumps(obj, default=str, indent=2)
    except Exception as e:
        logger.error(f"JSON serialization error: {e}")
        return "{}"


def safe_json_loads(json_str: str) -> Dict[str, Any]:
    """
    Safely deserialize JSON string.
    
    Args:
        json_str: JSON string
        
    Returns:
        Parsed dictionary
    """
    try:
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"JSON deserialization error: {e}")
        return {}


async def retry_async(
    func: callable,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
):
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_attempts: Maximum retry attempts
        delay: Initial delay in seconds
        backoff: Backoff multiplier
        
    Returns:
        Function result
        
    Raises:
        Exception: If all retries fail
    """
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            return await func()
        except Exception as e:
            last_error = e
            if attempt < max_attempts - 1:
                wait_time = delay * (backoff ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
    
    raise last_error


def validate_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Validate data against a JSON Schema.
    
    Args:
        data: Data to validate
        schema: JSON Schema
        
    Returns:
        True if valid
    """
    # Basic validation - could use jsonschema library for full validation
    required = schema.get("required", [])
    
    for field in required:
        if field not in data:
            logger.warning(f"Missing required field: {field}")
            return False
    
    return True


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries.
    
    Args:
        base: Base configuration
        override: Override configuration
        
    Returns:
        Merged configuration
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"
