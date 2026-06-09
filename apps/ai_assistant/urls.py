from django.urls import path

from apps.ai_assistant.views import admin_chat_send, chat_clear, chat_send

app_name = "ai_assistant"

urlpatterns = [
    path("assistant/chat/", chat_send, name="chat"),
    path("assistant/clear/", chat_clear, name="clear"),
    path("admin/assistant/chat/", admin_chat_send, name="admin_chat"),
]
