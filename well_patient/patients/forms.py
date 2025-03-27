from django import forms
from django.utils import timezone
from .models import BroadcastMessage, Patient, Location


class BroadcastMessageForm(forms.ModelForm):
    """Form for creating broadcast messages"""
    class Meta:
        model = BroadcastMessage
        fields = ['title', 'message', 'locations', 'broadcast_type', 
                 'send_sms', 'send_whatsapp', 'scheduled_time']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5}),
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def clean_scheduled_time(self):
        scheduled_time = self.cleaned_data.get('scheduled_time')
        if scheduled_time and scheduled_time < timezone.now():
            raise forms.ValidationError("Scheduled time cannot be in the past.")
        return scheduled_time


class PatientFilterForm(forms.Form):
    """Form for filtering patients by location and other criteria"""
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        empty_label="All Locations"
    )
    is_active = forms.BooleanField(required=False, initial=True)
    notification_preference = forms.ChoiceField(
        choices=(('', 'All'),) + Patient.NOTIFICATION_CHOICES,
        required=False
    )
    search = forms.CharField(required=False, max_length=100)


class BroadcastFilterForm(forms.Form):
    """Form for filtering broadcasts in the dashboard"""
    status = forms.ChoiceField(
        choices=(('', 'All'),) + BroadcastMessage.STATUS_CHOICES,
        required=False
    )
    broadcast_type = forms.ChoiceField(
        choices=(('', 'All'),) + BroadcastMessage.BROADCAST_TYPE_CHOICES,
        required=False
    )
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        empty_label="All Locations"
    )
    from_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    to_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))


class ImportPatientForm(forms.Form):
    """Form for importing patients from CSV/Excel"""
    file = forms.FileField()
    update_existing = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Update existing patients if they already exist"
    )


class SendBroadcastForm(forms.Form):
    """Form for sending broadcast messages from the dashboard"""
    title = forms.CharField(max_length=255)
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}))
    locations = forms.ModelMultipleChoiceField(
        queryset=Location.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Leave empty to send to all locations"
    )
    broadcast_type = forms.ChoiceField(choices=BroadcastMessage.BROADCAST_TYPE_CHOICES)
    send_sms = forms.BooleanField(required=False, initial=True)
    send_whatsapp = forms.BooleanField(required=False, initial=True)
    scheduled_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text="Leave empty to send immediately"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        send_sms = cleaned_data.get('send_sms')
        send_whatsapp = cleaned_data.get('send_whatsapp')
        
        if not send_sms and not send_whatsapp:
            raise forms.ValidationError("You must select at least one notification channel (SMS or WhatsApp)")
        
        return cleaned_data
