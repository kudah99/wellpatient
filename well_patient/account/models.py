from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, EmailValidator
from django.db import models


# Zimbabwean phone number validator
zimbabwe_phone_validator = RegexValidator(
    regex=r'^(?:\+263|0)?7[1-9]\d{7}$',
    message="Enter a valid Zimbabwean phone number starting with +263 or 0."
)


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    whatsapp_number = models.CharField(
        max_length=15,
        validators=[zimbabwe_phone_validator],
        blank=False,
        null=False,
        help_text="Enter a valid Zimbabwean WhatsApp number."
    )
    sms_number = models.CharField(
        max_length=15,
        validators=[zimbabwe_phone_validator],
        blank=False,
        null=False,
        help_text="Enter a valid Zimbabwean SMS number."
    )

    REQUIRED_FIELDS = ['email', 'whatsapp_number', 'sms_number'] 
    # username and password still required normally

    def __str__(self):
        return self.username
