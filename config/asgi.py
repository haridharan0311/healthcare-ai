"""
ASGI config for config project with WebSocket support.

Enables both HTTP and WebSocket protocols using Django Channels.
Requirement 6: Live Updates - WebSocket support for real-time data streaming.

For more information: https://channels.readthedocs.io/

Run with:
    daphne -b 0.0.0.0 -p 8000 config.asgi:application
    
Or for development:
    python manage.py runserver
    (Django's development server supports Channels)
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application early to ensure app registry is ready
django_asgi_app = get_asgi_application()

# Import WebSocket routing after Django is initialized
from analytics.routing import websocket_urlpatterns

# ─── Protocol Router: HTTP vs WebSocket ─────────────────────────────────────
# Routes incoming connections to appropriate handler based on protocol
application = ProtocolTypeRouter({
    # HTTP protocol - uses standard Django views
    "http": django_asgi_app,
    
    # WebSocket protocol - uses channel consumers
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})

"""
WebSocket Endpoints Available:
    - ws://localhost:8000/ws/disease-trends/ - Real-time disease trends
    - ws://localhost:8000/ws/spike-alerts/ - Spike detection alerts
    - ws://localhost:8000/ws/restock/ - Restock suggestions

Example Client Connection (JavaScript):
    const ws = new WebSocket('ws://localhost:8000/ws/disease-trends/');
    
    ws.onopen = () => {
        console.log('Connected!');
        ws.send(JSON.stringify({action: 'subscribe'}));
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received:', data.type, data.data);
    };
    
    ws.onclose = () => {
        console.log('Disconnected!');
    };

Production Deployment:
    Use Daphne ASGI server:
    
    $ pip install daphne
    $ daphne -b 0.0.0.0 -p 8000 config.asgi:application
    
    Or with Gunicorn + Eventlet:
    
    $ pip install gunicorn eventlet
    $ gunicorn -k eventlet -w 1 config.asgi:application
    
    For multi-process with Redis channel layer:
    
    1. Install Redis:
       $ redis-server
    
    2. Update settings.py CHANNEL_LAYERS:
       'BACKEND': 'channels_redis.core.RedisChannelLayer',
       'CONFIG': {
           'hosts': [('127.0.0.1', 6379)],
       }
    
    3. Run with Daphne:
       $ daphne -b 0.0.0.0 -p 8000 config.asgi:application
"""
