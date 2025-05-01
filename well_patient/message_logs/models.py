from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _


class MessageLog(models.Model):
    user = models.ForeignKey("account.CustomUser", on_delete=models.CASCADE)
    platform = models.CharField(max_length=50)
    is_reply = models.BooleanField(_("is chatbot reply"), default=False)
    message = models.TextField()
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        return f"Message from {self.user} on {self.platform} at {self.timestamp}"


class ErrorLog(models.Model):
    ERROR_LEVELS = (
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("CRITICAL", "Critical"),
    )

    error_message = models.TextField()
    error_level = models.CharField(max_length=10, choices=ERROR_LEVELS, default="INFO")
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.error_level} Error at {self.timestamp}"