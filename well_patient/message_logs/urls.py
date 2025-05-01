from django.urls import path
from . import views

urlpatterns = [
    # API endpoint for sending messages
    path('api/send_message/<int:user_id>/', views.send_message, name='send_message'),

    # API endpoint for ending chat
    path('api/end_chat/', views.end_chat, name='end_chat'),
]