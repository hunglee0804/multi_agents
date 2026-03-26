import json
from typing import Any, Optional
from app.core.redis_client import redis_client

# Cache lifetime (Example: 1 hour = 3600 seconds)
CACHE_TTL = 3600 

def get_cache(key: str) -> Optional[Any]:
    """Retrieving data from Redis Cache"""
    cached_data = redis_client.get(key)
    if cached_data:
        return json.loads(cached_data)
    return None

def set_cache(key: str, data: Any, ttl: int = CACHE_TTL):
    """Save data to Redis Cache"""
    # Nếu data là danh sách các Pydantic model hoặc dict, ta cần chuyển thành JSON
    redis_client.set(key, json.dumps(data), ex=ttl)

def delete_cache(key: str):
    """Delete a specific key"""
    redis_client.delete(key)

def delete_keys_by_pattern(pattern: str):
    """Delete multiple keys based on a pattern (e.g., delete the entire cache list when an update occurs)."""
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)