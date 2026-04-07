"""
Optimization Decorators for Analytics APIs

Provides performance monitoring and optimization utilities:
1. Query Counting Decorator - ensures query count limits
2. Caching Decorator - reduces redundant queries
3. Performance Monitoring - logs execution time

Layer: Utils (Utilities)
Usage:
    from analytics.utils.decorators import (
        limit_queries, cache_api_response, monitor_performance
    )
    
    @limit_queries(max_queries=50)
    @cache_api_response(timeout=30)
    def my_view(request):
        return Response(data)
"""

import functools
import time
from typing import Callable, Any, Optional
from django.core.cache import cache
from django.db import connection, reset_queries
from django.conf import settings
from rest_framework.response import Response

from .logger import get_logger

logger = get_logger(__name__)


def limit_queries(max_queries: int = 50, warn_at: Optional[int] = None) -> Callable:
    """
    ═══════════════════════════════════════════════════════════════════════════
    OPTIMIZATION: Query Count Limiter - Requirement 7 (Optimization)
    ═══════════════════════════════════════════════════════════════════════════
    
    Decorator to limit the number of database queries per API endpoint.
    Ensures efficient query performance and prevents N+1 problems.
    
    Default limits:
    - Warning threshold: 80% of max_queries
    - Hard limit: max_queries parameter
    
    For new users: 
        Use this on high-traffic endpoints to catch performance regressions.
        When limit is exceeded, returns HTTP 503 Service Unavailable.
    
    Example:
        @limit_queries(max_queries=50, warn_at=40)
        def my_expensive_view(request):
            # If this endpoint makes >50 queries, it fails
            # If it makes >40 queries, it logs a warning
            return Response(data)
    
    Args:
        max_queries: Maximum allowed queries (default: 50)
        warn_at: Warning threshold (default: 80% of max_queries)
    
    Returns:
        Decorated view function with query counting
    """
    warn_threshold = warn_at or int(max_queries * 0.8)
    
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(*args, **kwargs) -> Any:
            # Reset query tracking
            reset_queries()
            
            # Call the view
            result = view_func(*args, **kwargs)
            
            # Check query count
            query_count = len(connection.queries)
            
            if query_count > warn_threshold:
                logger.warning(
                    f"High query count in {view_func.__name__}: "
                    f"{query_count} queries (warn at {warn_threshold})",
                    extra={
                        'view': view_func.__name__,
                        'query_count': query_count,
                        'threshold': warn_threshold,
                        'queries': connection.queries if settings.DEBUG else []
                    }
                )
            
            if query_count > max_queries:
                logger.error(
                    f"Query limit exceeded in {view_func.__name__}: "
                    f"{query_count} > {max_queries}",
                    extra={
                        'view': view_func.__name__,
                        'query_count': query_count,
                        'max_queries': max_queries
                    }
                )
                return Response(
                    {'error': 'Service temporarily unavailable due to high load'},
                    status=503
                )
            
            # Add query count to response headers if it's a Response object
            if isinstance(result, Response):
                result['X-DB-Queries'] = query_count
            
            return result
        
        return wrapper
    return decorator


def cache_api_response(timeout: int = 30) -> Callable:
    """
    ═══════════════════════════════════════════════════════════════════════════
    OPTIMIZATION: Response Caching - Requirement 6 (Live Updates - Cache Strategy)
    ═══════════════════════════════════════════════════════════════════════════
    
    Decorator to cache API responses.
    Syncs with frontend 30-second refresh interval (requirement 6).
    
    For new users:
        Caches expensive computation results. Cache expires and fetches fresh
        data on next request after timeout expires.
    
    Cache key strategy:
        - View class name + query parameters
        - Different params = different cache entries
        - Supports ?days=, ?district=, ?disease= etc.
    
    Example:
        @cache_api_response(timeout=30)
        def disease_trends(request):
            # First request: computes & caches for 30 seconds
            # Within 30 seconds: returns cached result
            # After 30 seconds: recomputes
            return Response(data)
    
    Args:
        timeout: Cache duration in seconds (default: 30)
    
    Returns:
        Decorated view function with caching
    """
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(self, request, *args, **kwargs) -> Response:
            # Generate cache key from view name + query params
            cache_key = f"{self.__class__.__name__}:{request.GET.urlencode()}"
            
            # Try to get from cache
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(
                    f"Cache hit for {self.__class__.__name__}",
                    extra={'cache_key': cache_key}
                )
                response = Response(cached)
                response['X-Cache'] = 'HIT'
                return response
            
            logger.debug(
                f"Cache miss for {self.__class__.__name__}",
                extra={'cache_key': cache_key}
            )
            
            # Call the original view
            response = view_func(self, request, *args, **kwargs)
            
            # Cache the response data
            if response.status_code == 200:
                cache.set(cache_key, response.data, timeout)
                response['X-Cache'] = 'MISS'
                response['X-Cache-Timeout'] = timeout
            
            return response
        
        return wrapper
    return decorator


def monitor_performance(threshold_ms: float = 1000.0) -> Callable:
    """
    ═══════════════════════════════════════════════════════════════════════════
    OPTIMIZATION: Performance Monitoring - Requirement 7 (Optimization)
    ═══════════════════════════════════════════════════════════════════════════
    
    Decorator to monitor and log API endpoint performance.
    Logs execution time and alerts on slow endpoints.
    
    For new users:
        Automatically tracks how long each API takes. Alerts when response
        time exceeds threshold. Helps identify performance bottlenecks.
    
    Example:
        @monitor_performance(threshold_ms=500)
        def slow_endpoint(request):
            # If this takes >500ms, logs a warning
            return Response(data)
    
    Args:
        threshold_ms: Warn if execution exceeds this time in milliseconds
    
    Returns:
        Decorated view function with performance monitoring
    """
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            result = view_func(*args, **kwargs)
            elapsed_ms = (time.time() - start_time) * 1000
            
            log_level = 'warning' if elapsed_ms > threshold_ms else 'debug'
            logger.log(
                log_level,
                f"API {view_func.__name__} took {elapsed_ms:.2f}ms",
                extra={
                    'view': view_func.__name__,
                    'execution_time_ms': elapsed_ms,
                    'threshold_ms': threshold_ms
                }
            )
            
            # Add timing header to response
            if isinstance(result, Response):
                result['X-Response-Time-Ms'] = elapsed_ms
            
            return result
        
        return wrapper
    return decorator


def combine_optimizations(
    max_queries: int = 50,
    cache_timeout: int = 30,
    perf_threshold_ms: float = 1000.0
) -> Callable:
    """
    ═══════════════════════════════════════════════════════════════════════════
    CONVENIENCE: Combined Optimization Decorator
    ═══════════════════════════════════════════════════════════════════════════
    
    Applies all optimization decorators in optimal order.
    Combines query limiting + caching + performance monitoring.
    
    For new users:
        Use this on critical endpoints to get all benefits at once:
        - Prevents excessive queries
        - Caches results  
        - Monitors performance
    
    Example:
        @combine_optimizations(max_queries=40, cache_timeout=30)
        def critical_endpoint(request):
            return Response(data)
    
    Args:
        max_queries: Maximum allowed queries
        cache_timeout: Cache duration in seconds
        perf_threshold_ms: Performance warning threshold
    
    Returns:
        Decorator applying all optimizations
    """
    def decorator(view_func: Callable) -> Callable:
        # Apply in this order for best performance:
        # 1. Caching (first line of defense)
        # 2. Query limiting (catches N+1 problems)
        # 3. Performance monitoring (observability)
        return (
            monitor_performance(threshold_ms=perf_threshold_ms)(
                limit_queries(max_queries=max_queries)(
                    cache_api_response(timeout=cache_timeout)(view_func)
                )
            )
        )
    return decorator
