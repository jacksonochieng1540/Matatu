"""
ASGI config for matatu_booking project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

# Import your routing after initializing Django
# from core import routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # Uncomment when you add WebSocket routing
    # "websocket": AuthMiddlewareStack(
    #     URLRouter(
    #         routing.websocket_urlpatterns
    #     )
    # ),
})