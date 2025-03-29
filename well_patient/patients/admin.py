from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from django.contrib.auth.models import User, Group

from .models import (
    Patient, Location, Medication, PatientMedication,
    NotificationLog, NotificationType, BroadcastMessage
)
from .resources import PatientResource
from .forms import BroadcastMessageForm

from import_export.admin import ImportExportModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm, SelectableFieldsExportForm


# Unregister default User and Group admin
admin.site.unregister(User)
admin.site.unregister(Group)

# Register User admin with Unfold styling
@admin.register(User)
class UnfoldUserAdmin(ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ('username', 'first_name', 'last_name', 'is_staff')
    search_fields = ('first_name', 'last_name',)
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    ordering = ('username',)


# Register Group admin with Unfold styling
@admin.register(Group)
class UnfoldGroupAdmin(ModelAdmin):
    search_fields = ('name',)
    ordering = ('name',)
    filter_horizontal = ('permissions',)


@admin.register(Location)
class LocationAdmin(ModelAdmin):
    list_display = ('name', 'city',)
    list_filter = ('city', 'name')
    search_fields = ('name', 'city')
    
    def patient_count(self, obj):
        count = obj.patients.count()
        return format_html('<span class="badge bg-info">{}</span>', count)
    
    patient_count.short_description = 'Patients'


@admin.register(Medication)
class MedicationAdmin(ModelAdmin):
    list_display = ('name', 'refill_period_days', 'patient_count')
    search_fields = ('name',)
    list_filter = ('refill_period_days',)
    
    def patient_count(self, obj):
        count = PatientMedication.objects.filter(medication=obj).count()
        return format_html('<span class="badge bg-info">{}</span>', count)
    
    patient_count.short_description = 'Patients'


class PatientMedicationInline(admin.TabularInline):
    model = PatientMedication
    extra = 1
    fields = ('medication', 'dosage', 'start_date', 'next_refill_date', 'is_active')


@admin.register(Patient)
class PatientAdmin(ModelAdmin, ImportExportModelAdmin):
    import_form_class = ImportForm
    export_form_class = ExportForm
    resource_class = PatientResource
    list_display = ('get_full_name', 'phone_number', 'location', 'notification_preference', 'is_active')
    list_filter = ('location__city', 'location__name',  'notification_preference', 'is_active')
    search_fields = ('first_name', 'last_name', 'phone_number')
    inlines = [PatientMedicationInline]
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', )
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'address', 'location')
        }),
        ('Notification Settings', {
            'fields': ('notification_preference', 'is_active')
        }),
    )


@admin.register(PatientMedication)
class PatientMedicationAdmin(ModelAdmin):
    list_display = ('patient', 'medication', 'dosage', 'start_date', 'next_refill_date', 'is_active')
    list_filter = ('is_active', 'medication', 'start_date', 'next_refill_date')
    search_fields = ('patient__first_name', 'patient__last_name', 'medication__name')
    date_hierarchy = 'next_refill_date'
    actions = ['update_refill_dates']
    
    def update_refill_dates(self, request, queryset):
        for patient_med in queryset:
            patient_med.update_next_refill_date()
        self.message_user(request, f"Updated refill dates for {queryset.count()} medications.")
    
    update_refill_dates.short_description = "Update next refill dates"


@admin.register(NotificationType)
class NotificationTypeAdmin(ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(NotificationLog)
class NotificationLogAdmin(ModelAdmin):
    list_display = ('patient', 'notification_type', 'channel', 'status', 'scheduled_time', 'sent_time')
    list_filter = ('status', 'channel', 'notification_type', 'scheduled_time')
    search_fields = ('patient__first_name', 'patient__last_name', 'message')
    date_hierarchy = 'scheduled_time'
    readonly_fields = ('patient', 'notification_type', 'channel', 'message', 'scheduled_time', 'sent_time', 'status', 'status_message')


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(ModelAdmin):
    form = BroadcastMessageForm
    list_display = ('title', 'broadcast_type', 'status', 'scheduled_time', 'created_by', 'created_at')
    list_filter = ('status', 'broadcast_type', 'send_sms', 'send_whatsapp', 'scheduled_time')
    search_fields = ('title', 'message')
    filter_horizontal = ('locations',)
    readonly_fields = ('created_by', 'created_at', 'updated_at')
    actions = ['schedule_broadcast', 'cancel_broadcast']
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set created_by for new instances
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def schedule_broadcast(self, request, queryset):
        for broadcast in queryset.filter(status='DRAFT'):
            if not broadcast.scheduled_time:
                broadcast.scheduled_time = timezone.now()
            broadcast.status = 'SCHEDULED'
            broadcast.save()
        self.message_user(request, f"Scheduled {queryset.filter(status='DRAFT').count()} broadcasts.")
    
    schedule_broadcast.short_description = "Schedule selected broadcasts"
    
    def cancel_broadcast(self, request, queryset):
        updates = queryset.filter(status__in=['DRAFT', 'SCHEDULED']).update(status='CANCELLED')
        self.message_user(request, f"Cancelled {updates} broadcasts.")
    
    cancel_broadcast.short_description = "Cancel selected broadcasts"
