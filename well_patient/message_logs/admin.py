from django.contrib import admin
from django.urls import path
from django.utils.translation import gettext_lazy as _
from .models import MessageLog
from .views import ChatDashboardView


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "is_reply", "message", "timestamp")
    list_filter = ("platform", "is_reply", "timestamp")
    search_fields = ("user__username", "message")
    readonly_fields = ("timestamp",)
    
    def get_urls(self):
        # Add custom URLs for the admin interface
        custom_urls = [
            # path(
            #     "platform-users/",
            #     self.admin_site.admin_view(ListOfPlatiform.as_view(model_admin=self)),
            #     name="platform_users",
            # ),
            # path(
            #     "platform-users/<int:user_id>/",
            #     self.admin_site.admin_view(PlatiformChat.as_view(model_admin=self)),
            #     name="platform_chat",
            # ),
            # path(
            #     "platform-users/<int:user_id>/",
            #     self.admin_site.admin_view(PlatiformChat.as_view(model_admin=self)),
            #     name="platform_chat",
            # ),
            path('platform-chat/', self.admin_site.admin_view(ChatDashboardView.as_view(model_admin=self)), name='platform_users'),
            path('platform-chat/<int:user_id>/',self.admin_site.admin_view(ChatDashboardView.as_view(model_admin=self)), name='platform_chat'),
        ]
        return custom_urls + super().get_urls()