"""
Analytics utilities layer - contains helpers and infrastructure.

Modules:
    - logger.py: Centralized logging system with 5 log levels
    - validators.py: Input validation & data sanitization
    - decorators.py: Query limiting, caching, & performance monitoring
    - query_optimization.py: Optimized querysets with prefetch_related

Key Exports:
    from analytics.utils.decorators import (
        limit_queries, cache_api_response, monitor_performance, combine_optimizations
    )
    
    from analytics.utils.query_optimization import (
        get_appointments_optimized, get_prescription_lines_optimized,
        get_drugs_optimized, count_queries_in_operation
    )
    
    from analytics.utils.logger import get_logger
    from analytics.utils.validators import validate_date_range
"""
