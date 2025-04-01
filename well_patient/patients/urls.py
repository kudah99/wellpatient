from django.urls import path
from .views import whatsapp_webhook,cancel_broadcast

urlpatterns = [
    path("webhook/", whatsapp_webhook, name="whatsapp_webhook"),
    path("cancel-broadcast/<int:pk>/", cancel_broadcast, name="cancel_broadcast"),
]