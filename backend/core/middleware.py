import json
import logging
from django.utils import timezone
from .models import AuditLog

logger = logging.getLogger('audit')

class AuditLoggingMiddleware:
    """
    Middleware to track access to sensitive health analytics data.
    Logs who viewed what, and when, for HIPAA compliance.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request
        response = self.get_response(request)

        # Only log successful GET/POST requests to the API
        if request.path.startswith('/api/') and response.status_code < 400:
            user = request.user if request.user.is_authenticated else None
            
            # Identify sensitive paths (analytics, restock, etc.)
            sensitive_keywords = ['stats', 'trends', 'restock', 'spike', 'export', 'insights']
            is_sensitive = any(word in request.path for word in sensitive_keywords)

            if is_sensitive:
                self.log_access(request, user)

        return response

    def log_access(self, request, user):
        try:
            # Prepare log data
            params = dict(request.GET.items()) if request.method == 'GET' else {}
            ip = self.get_client_ip(request)
            
            # 1. Log to file for archival
            log_entry = {
                'timestamp': timezone.now().isoformat(),
                'user': user.username if user else 'anonymous',
                'path': request.path,
                'method': request.method,
                'params': params,
                'ip_address': ip
            }
            logger.info(json.dumps(log_entry))
            
            # 2. Log to database for quick audit
            AuditLog.objects.create(
                user=user,
                action=f"ACCESS_{request.method}",
                resource=request.path,
                ip_address=ip,
                metadata={'params': params}
            )
        except Exception as e:
            # Never crash the main request due to logging failure
            logger.warning(f"Audit logging failed: {str(e)}")

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
