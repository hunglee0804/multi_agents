import json
from typing import Any, Optional
from app.core.redis_client import redis_client

# Thời gian sống của cache (Ví dụ: 1 giờ = 3600 giây)
CACHE_TTL = 3600 

def get_cache(key: str) -> Optional[Any]:
    """Lấy dữ liệu từ Redis Cache"""
    cached_data = redis_client.get(key)
    if cached_data:
        return json.loads(cached_data)
    return None

def set_cache(key: str, data: Any, ttl: int = CACHE_TTL):
    """Lưu dữ liệu vào Redis Cache"""
    # Nếu data là danh sách các Pydantic model hoặc dict, ta cần chuyển thành JSON
    redis_client.set(key, json.dumps(data), ex=ttl)

def delete_cache(key: str):
    """Xóa 1 key cụ thể"""
    redis_client.delete(key)

def delete_keys_by_pattern(pattern: str):
    """Xóa nhiều keys dựa trên pattern (Ví dụ xóa toàn bộ cache list khi có cập nhật)"""
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)