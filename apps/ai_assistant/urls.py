from django.urls import path

from apps.ai_assistant.views import chat_send

app_name = "ai_assistant"

urlpatterns = [
    path("assistant/chat/", chat_send, name="chat"),
]
