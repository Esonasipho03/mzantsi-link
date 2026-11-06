from django.urls import path
from .views import conversation_view, inbox_view, messages_since_view

urlpatterns = [
    path("", inbox_view, name="inbox"),
    path("with/<int:user_id>/", conversation_view, name="conversation"),
    path("with/<int:user_id>/messages/", messages_since_view, name="conversation_messages"),
]
