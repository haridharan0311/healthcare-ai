from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Custom exception handler for Django REST Framework.
    Standardizes error responses and prevents 500 crashes from returning HTML.
    """
    # Call REST framework's default exception handler first to get the standard error response.
    response = exception_handler(exc, context)

    # If an unexpected exception occurs (unhandled by DRF), 'response' will be None.
    if response is None:
        view = context.get('view')
        view_name = view.__class__.__name__ if view else "UnknownView"
        
        # Log the full traceback for developers
        logger.error(f"Unhandled Exception in {view_name}: {str(exc)}", exc_info=True)

        return Response(
            {
                'success': False,
                'error': 'An internal server error occurred.',
                'detail': str(exc) if hasattr(exc, '__str__') else 'Critical analytical failure.',
                'code': 'internal_server_error'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Enhance standard DRF error responses
    response.data = {
        'success': False,
        'error': response.data.get('detail', 'Validation or processing error.'),
        'details': response.data,
        'code': getattr(exc, 'default_code', 'error')
    }

    return response
