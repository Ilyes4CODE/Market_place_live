"""
WSGI config for MarketPlace project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from ws4redis.wsgi_server import WebsocketWSGIServer
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MarketPlace.settings')

application = get_wsgi_application()
websocket_wsgi_server = WebsocketWSGIServer(application)