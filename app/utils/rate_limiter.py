# app/utils/rate_limiter.py
"""
Rate limiting decorator.
"""
from functools import wraps
from flask import request, jsonify, current_app
from app.services.cache_service import CacheService


def rate_limit(f):
    """Rate limit decorator - 100 req/hour per IP."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        count = CacheService.increment_rate_limit(ip)
        limit = current_app.config['RATE_LIMIT_PER_HOUR']
        
        if count > limit:
            return jsonify({
                'error': 'Rate limit exceeded',
                'limit': limit,
                'retry_after': '1 hour'
            }), 429
        
        return f(*args, **kwargs)
    return decorated_function