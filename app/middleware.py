"""
Middleware for Document Sorter Application
Includes rate limiting, performance monitoring, and security enhancements
"""

import time
import hashlib
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
from werkzeug.exceptions import TooManyRequests

from .monitoring import get_logger
from .production_config import config_manager

logger = get_logger('middleware')


class RateLimiter:
    """Token bucket rate limiter with per-IP tracking"""

    def __init__(self):
        self.config = config_manager.config
        self.buckets = defaultdict(lambda: {
            'tokens': self.config.rate_limit_burst,
            'last_update': time.time()
        })
        self.request_history = defaultdict(deque)

    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed for given IP"""
        now = time.time()
        bucket = self.buckets[client_ip]

        # Calculate tokens to add based on time passed
        time_passed = now - bucket['last_update']
        tokens_to_add = time_passed * (self.config.rate_limit_per_minute / 60.0)

        # Update bucket
        bucket['tokens'] = min(
            self.config.rate_limit_burst,
            bucket['tokens'] + tokens_to_add
        )
        bucket['last_update'] = now

        # Check if request is allowed
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            return True

        return False

    def get_rate_limit_info(self, client_ip: str) -> dict:
        """Get rate limit information for client"""
        bucket = self.buckets[client_ip]
        return {
            'remaining': int(bucket['tokens']),
            'limit': self.config.rate_limit_burst,
            'reset_time': bucket['last_update'] + 60
        }

    def cleanup_old_entries(self):
        """Clean up old rate limit entries"""
        now = time.time()
        cutoff = now - 3600  # Clean entries older than 1 hour

        old_keys = [
            ip for ip, bucket in self.buckets.items()
            if bucket['last_update'] < cutoff
        ]

        for key in old_keys:
            del self.buckets[key]

        logger.debug(f"Cleaned up {len(old_keys)} old rate limit entries")


class PerformanceMonitor:
    """Performance monitoring middleware"""

    def __init__(self):
        self.request_times = deque(maxlen=1000)
        self.slow_requests = deque(maxlen=100)
        self.error_count = defaultdict(int)

    def record_request(self, path: str, method: str, duration: float, status_code: int):
        """Record request performance metrics"""
        now = time.time()

        # Record general metrics
        self.request_times.append({
            'path': path,
            'method': method,
            'duration': duration,
            'status_code': status_code,
            'timestamp': now
        })

        # Track slow requests (>2 seconds)
        if duration > 2.0:
            self.slow_requests.append({
                'path': path,
                'method': method,
                'duration': duration,
                'timestamp': now
            })

        # Track errors
        if status_code >= 400:
            self.error_count[f"{status_code}"] += 1

    def get_performance_stats(self) -> dict:
        """Get current performance statistics"""
        if not self.request_times:
            return {
                'avg_response_time': 0,
                'slow_request_count': 0,
                'total_requests': 0,
                'error_rate': 0
            }

        # Calculate average response time
        recent_times = [r['duration'] for r in self.request_times]
        avg_time = sum(recent_times) / len(recent_times)

        # Calculate error rate
        total_requests = len(self.request_times)
        error_requests = sum(1 for r in self.request_times if r['status_code'] >= 400)
        error_rate = (error_requests / total_requests) * 100 if total_requests > 0 else 0

        return {
            'avg_response_time': round(avg_time, 3),
            'slow_request_count': len(self.slow_requests),
            'total_requests': total_requests,
            'error_rate': round(error_rate, 2),
            'p95_response_time': self._calculate_percentile(recent_times, 95),
            'p99_response_time': self._calculate_percentile(recent_times, 99)
        }

    def _calculate_percentile(self, values: list, percentile: int) -> float:
        """Calculate percentile of response times"""
        if not values:
            return 0

        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return round(sorted_values[min(index, len(sorted_values) - 1)], 3)


class SecurityMiddleware:
    """Security enhancements middleware"""

    def __init__(self):
        self.suspicious_ips = set()
        self.blocked_ips = set()

    def check_security_headers(self, response):
        """Add security headers to response"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        return ip in self.blocked_ips

    def block_ip(self, ip: str, reason: str):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        logger.warning(f"IP blocked: {ip}", reason=reason)

    def validate_request_size(self, request) -> bool:
        """Validate request content length"""
        max_size = config_manager.config.max_file_size_mb * 1024 * 1024
        content_length = request.content_length

        if content_length and content_length > max_size:
            return False

        return True


# Global middleware instances
rate_limiter = RateLimiter()
performance_monitor = PerformanceMonitor()
security_middleware = SecurityMiddleware()


def register_middleware(app):
    """Register all middleware with Flask app"""

    @app.before_request
    def before_request():
        """Pre-request middleware"""
        g.start_time = time.time()
        client_ip = request.remote_addr

        # Security checks
        if security_middleware.is_ip_blocked(client_ip):
            logger.warning("Blocked IP attempted access", ip=client_ip)
            return jsonify({'error': 'Access denied'}), 403

        # Validate request size
        if not security_middleware.validate_request_size(request):
            logger.warning("Request too large", ip=client_ip, size=request.content_length)
            return jsonify({'error': 'Request too large'}), 413

        # Rate limiting (only for API endpoints)
        if request.path.startswith('/api/'):
            if not rate_limiter.is_allowed(client_ip):
                rate_info = rate_limiter.get_rate_limit_info(client_ip)
                logger.warning("Rate limit exceeded", ip=client_ip, path=request.path)

                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.',
                    'retry_after': 60
                })
                response.headers['X-RateLimit-Limit'] = str(config_manager.config.rate_limit_burst)
                response.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                response.headers['X-RateLimit-Reset'] = str(int(rate_info['reset_time']))
                return response, 429

    @app.after_request
    def after_request(response):
        """Post-request middleware"""
        # Calculate request duration
        duration = time.time() - g.get('start_time', time.time())

        # Record performance metrics
        performance_monitor.record_request(
            request.path,
            request.method,
            duration,
            response.status_code
        )

        # Add rate limit headers for API requests
        if request.path.startswith('/api/'):
            rate_info = rate_limiter.get_rate_limit_info(request.remote_addr)
            response.headers['X-RateLimit-Limit'] = str(config_manager.config.rate_limit_burst)
            response.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
            response.headers['X-RateLimit-Reset'] = str(int(rate_info['reset_time']))

        # Add security headers
        response = security_middleware.check_security_headers(response)

        # Add performance headers
        response.headers['X-Response-Time'] = f"{duration:.3f}s"

        return response

    # Periodic cleanup task (runs every hour)
    def cleanup_middleware():
        """Clean up old middleware data"""
        rate_limiter.cleanup_old_entries()
        logger.info("Middleware cleanup completed")

    # Schedule cleanup (in production, this would be handled by a scheduler)
    # For now, we'll clean up periodically during requests
    cleanup_counter = getattr(app, '_cleanup_counter', 0)
    app._cleanup_counter = cleanup_counter + 1

    if app._cleanup_counter % 1000 == 0:  # Clean up every 1000 requests
        cleanup_middleware()


def rate_limit(per_minute: int = None, burst: int = None):
    """Decorator for additional rate limiting on specific endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr

            # Use custom limits if provided, otherwise use global config
            limit_per_minute = per_minute or config_manager.config.rate_limit_per_minute
            limit_burst = burst or config_manager.config.rate_limit_burst

            # Create custom rate limiter for this endpoint
            endpoint_key = f"{client_ip}:{request.endpoint}"

            # Simple check (in production, use Redis or similar)
            if hasattr(f, '_rate_limit_cache'):
                cache = f._rate_limit_cache
            else:
                cache = f._rate_limit_cache = {}

            now = time.time()
            if endpoint_key not in cache:
                cache[endpoint_key] = {
                    'requests': deque(),
                    'tokens': limit_burst
                }

            endpoint_data = cache[endpoint_key]
            requests = endpoint_data['requests']

            # Remove old requests (older than 1 minute)
            minute_ago = now - 60
            while requests and requests[0] < minute_ago:
                requests.popleft()

            # Check if rate limit exceeded
            if len(requests) >= limit_per_minute:
                raise TooManyRequests("Rate limit exceeded for this endpoint")

            # Record this request
            requests.append(now)

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def performance_critical(max_duration: float = 5.0):
    """Decorator to monitor performance-critical endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()

            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time

                if duration > max_duration:
                    logger.warning(f"Performance critical endpoint exceeded threshold",
                                 endpoint=request.endpoint,
                                 duration=duration,
                                 threshold=max_duration)

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Performance critical endpoint failed",
                           endpoint=request.endpoint,
                           duration=duration,
                           exception=e)
                raise

        return decorated_function
    return decorator