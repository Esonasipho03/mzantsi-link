from django.urls import path
from .views import conversation_view, inbox_view

urlpatterns = [
    path("", inbox_view, name="inbox"),
    path("with/<int:user_id>/", conversation_view, name="conversation"),
]
