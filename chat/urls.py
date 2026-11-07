from django.urls import path
from .views import conversation_view, inbox_view, messages_since_view, unread_count_view

urlpatterns = [
    path("", inbox_view, name="inbox"),
    path("unread/", unread_count_view, name="chat_unread"),
    path("with/<int:user_id>/", conversation_view, name="conversation"),
    path("with/<int:user_id>/messages/", messages_since_view, name="conversation_messages"),
]
