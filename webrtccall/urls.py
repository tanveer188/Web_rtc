from django.urls import path, include, re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from videochat.consumers import VideoCallConsumer
from django.core.asgi import get_asgi_application

websocket_urlpatterns = [
    re_path(r'ws/video-call/$', VideoCallConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': URLRouter(websocket_urlpatterns),
})

urlpatterns = [
    path('videochat/', include('videochat.urls')),
]
