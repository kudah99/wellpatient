from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from django.contrib.auth.models import User, Group
from django.urls import path
from unfold.admin import ModelAdmin
from django.shortcuts import redirect
from patients.forms import BroadcastMessageForm
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.http import HttpRequest
from unfold.decorators import action
from patients.views import BroadcastListView,BroadcastMessageView,ImportPatientsView
from .models import (
    Patient, Location, Medication, PatientMedication,
    NotificationLog, NotificationType,BroadcastMessage
)
from .resources import PatientResource

from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from django_celery_beat.admin import ClockedScheduleAdmin as BaseClockedScheduleAdmin
from django_celery_beat.admin import CrontabScheduleAdmin as BaseCrontabScheduleAdmin
from django_celery_beat.admin import PeriodicTaskAdmin as BasePeriodicTaskAdmin
from django_celery_beat.admin import PeriodicTaskForm, TaskSelectWidget
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget


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
class PatientAdmin(ModelAdmin):

    actions_list = ["changelist_action"]
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
    def get_urls(self):
        # IMPORTANT: model_admin is required
        custom_patients_import = self.admin_site.admin_view(
            ImportPatientsView.as_view(model_admin=self)
        )
        return super().get_urls() + [
            path(
                "custom-patients-import", custom_patients_import, name="custom_patients_import"
            ),
        ]

    @action(description=_("Bulk import"), url_path="changelist-action", permissions=["changelist_action"])
    def changelist_action(self, request: HttpRequest):
        return redirect(
          reverse_lazy("admin:custom_patients_import")
        )
    def has_changelist_action_permission(self, request: HttpRequest):
        # Write your own bussiness logic. Code below will always display an action.
        return True

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

    def get_urls(self):
        # IMPORTANT: model_admin is required
        broadcast_messages_list = self.admin_site.admin_view(
            BroadcastListView.as_view(model_admin=self)
        )
        broadcast_messages_create = self.admin_site.admin_view(
           BroadcastMessageView.as_view(model_admin=self)
        )
        return super().get_urls() + [
            path(
                "broadcast-messages", broadcast_messages_list, name="broadcast_messages"
            ),
            path(
                "broadcast-message_crete", broadcast_messages_create, name="broadcast_message_create"
            ),
        ]
    
    schedule_broadcast.short_description = "Schedule selected broadcasts"
    
    def cancel_broadcast(self, request, queryset):
        updates = queryset.filter(status__in=['DRAFT', 'SCHEDULED']).update(status='CANCELLED')
        self.message_user(request, f"Cancelled {updates} broadcasts.")
    
    cancel_broadcast.short_description = "Cancel selected broadcasts"



admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(SolarSchedule)
admin.site.unregister(ClockedSchedule)


class UnfoldTaskSelectWidget(UnfoldAdminSelectWidget, TaskSelectWidget):
    pass


class UnfoldPeriodicTaskForm(PeriodicTaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["task"].widget = UnfoldAdminTextInputWidget()
        self.fields["regtask"].widget = UnfoldTaskSelectWidget()


@admin.register(PeriodicTask)
class PeriodicTaskAdmin(BasePeriodicTaskAdmin, ModelAdmin):
    form = UnfoldPeriodicTaskForm


@admin.register(IntervalSchedule)
class IntervalScheduleAdmin(ModelAdmin):
    pass


@admin.register(CrontabSchedule)
class CrontabScheduleAdmin(BaseCrontabScheduleAdmin, ModelAdmin):
    pass


@admin.register(SolarSchedule)
class SolarScheduleAdmin(ModelAdmin):
    pass

@admin.register(ClockedSchedule)
class ClockedScheduleAdmin(BaseClockedScheduleAdmin, ModelAdmin):
    pass
