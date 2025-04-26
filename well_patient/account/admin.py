from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from unfold.admin import ModelAdmin

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(CustomUser)
class CustomUserAdmin(ModelAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'whatsapp_number', 'sms_number', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('email', 'whatsapp_number', 'sms_number')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'whatsapp_number', 'sms_number', 'password', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('username', 'email', 'whatsapp_number', 'sms_number')
    ordering = ('username',)

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new user
            obj.set_password(obj.password)
        else:
            # If updating existing user and password was changed manually
            if 'password' in form.changed_data:
                obj.set_password(obj.password)
        obj.save()
