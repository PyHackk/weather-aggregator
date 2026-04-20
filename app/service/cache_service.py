# app/services/cache_service.py
"""
Redis caching operations.
"""
import json
from app import redis_client
from flask import current_app


class CacheService:
    """Handles all Redis caching operations."""
    
    @staticmethod
    def get(key: str):
        """Get cached value."""
        data = redis_client.get(key)
        return json.loads(data) if data else None
    
    @staticmethod
    def set(key: str, value: dict, ttl: int = None):
        """Set cached value with TTL."""
        if ttl is None:
            ttl = current_app.config['CACHE_TTL']
        redis_client.setex(key, ttl, json.dumps(value))
    
    @staticmethod
    def delete(key: str):
        """Delete cached value."""
        redis_client.delete(key)
    
    @staticmethod
    def increment_rate_limit(ip: str) -> int:
        """Increment rate limit counter. Returns current count."""
        key = f"rate_limit:{ip}"
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, 3600)  # 1 hour
        return count