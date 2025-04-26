from django.db import models
from django.utils import timezone
from model_utils import FieldTracker
import datetime
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from account.models import CustomUser

class Location(models.Model):
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)

    class Meta:
        ordering = ['city', 'name']
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'

    def __str__(self):
        return f"{self.name}, {self.city}"


class CorporateClient(models.Model):
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Corporate Client'
        verbose_name_plural = 'Corporate Clients'

    def __str__(self):
        return self.name


class Medication(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    refill_period_days = models.PositiveIntegerField(default=30)

    class Meta:
        ordering = ['name']
        verbose_name = 'Medication'
        verbose_name_plural = 'Medications'

    def __str__(self):
        return self.name


class Patient(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    NOTIFICATION_CHOICES = (
        ('SMS', 'SMS Only'),
        ('WA', 'WhatsApp Only'),
        ('BOTH', 'SMS and WhatsApp'),
        ('NONE', 'No Notifications'),
    )
    PAYMENT_METHOD_CHOICES = (
        ('CASH', 'Cash'),
        ('MEDICAL_AID', 'Medical Aid'),
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+263783046041. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17)

    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, related_name='patients')
    address = models.TextField(null=True, blank=True)

    medications = models.ManyToManyField(Medication, through='PatientMedication')

    notification_preference = models.CharField(max_length=4, choices=NOTIFICATION_CHOICES, default='BOTH')

    corporate_client = models.ForeignKey(
        CorporateClient, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients'
    )

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    medical_aid_company = models.CharField(max_length=255, blank=True)

    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        null=True, blank=True,
        help_text="Used for grouping clients by payment amount"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        if self.payment_method == 'MEDICAL_AID' and not self.medical_aid_company:
            raise ValidationError("Medical Aid company must be specified when payment method is Medical Aid.")

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_payment_group(self):
        """Returns the group range the patient belongs to based on amount_paid."""
        amount = self.amount_paid
        if amount <= 50:
            return '10 - 50'
        elif amount <= 100:
            return '51 - 100'
        elif amount <= 500:
            return '101 - 500'
        elif amount <= 1000:
            return '501 - 1000'
        else:
            return '1000+'


class PatientMedication(models.Model):
    """Model to store the relationship between patients and medications with resupply dates"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    
    dosage = models.CharField(max_length=100, blank=True)
    instructions = models.TextField(blank=True)
    tracker = FieldTracker(fields=['is_active'])
    
    start_date = models.DateField()
    next_refill_date = models.DateField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Patient Medication'
        verbose_name_plural = 'Patient Medications'
        unique_together = ('patient', 'medication')
    
    def __str__(self):
        return f"{self.patient} - {self.medication}"
    
    def save(self, *args, **kwargs):
        # If this is a new record, calculate the next refill date
        if not self.next_refill_date:
            self.next_refill_date = self.start_date + datetime.timedelta(days=self.medication.refill_period_days)
        super().save(*args, **kwargs)
    
    def update_next_refill_date(self):
        """Update the next refill date based on the medication's refill period"""
        self.next_refill_date = timezone.now().date() + datetime.timedelta(days=self.medication.refill_period_days)
        self.save()
    
    def is_refill_due_soon(self, days=7):
        """Check if refill is due within the specified days"""
        return (self.next_refill_date - timezone.now().date()).days <= days and self.is_active


class NotificationType(models.Model):
    """Model to store different types of notifications"""
    name = models.CharField(max_length=100)
    template_sms = models.TextField(help_text="Template for SMS with {placeholders}")
    template_whatsapp = models.TextField(help_text="Template for WhatsApp with {placeholders}")
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Notification Type'
        verbose_name_plural = 'Notification Types'
    
    def __str__(self):
        return self.name


class NotificationLog(models.Model):
    """Model to log all notifications sent to patients"""
    NOTIFICATION_CHANNELS = (
        ('SMS', 'SMS'),
        ('WA', 'WhatsApp'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
    )
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE)
    channel = models.CharField(max_length=3, choices=NOTIFICATION_CHANNELS)
    message = models.TextField()
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    status_message = models.TextField(blank=True)
    
    scheduled_time = models.DateTimeField()
    sent_time = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_time']
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
    
    def __str__(self):
        return f"{self.patient} - {self.notification_type} ({self.channel})"


class BroadcastMessage(models.Model):
    """Model to store broadcast messages sent to patients based on location"""
    BROADCAST_TYPE_CHOICES = (
        ('MARKETING', 'Marketing'),
        ('PROMOTIONAL', 'Promotional'),
        ('INFORMATIONAL', 'Informational'),
        ('EMERGENCY', 'Emergency'),
    )
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('SCHEDULED', 'Scheduled'),
        ('SENDING', 'Sending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    locations = models.ManyToManyField(Location, blank=True, related_name='broadcasts')
    broadcast_type = models.CharField(max_length=15, choices=BROADCAST_TYPE_CHOICES)
    
    send_sms = models.BooleanField(default=True)
    send_whatsapp = models.BooleanField(default=True)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey('account.CustomUser', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Broadcast Message'
        verbose_name_plural = 'Broadcast Messages'
    
    def __str__(self):
        return self.title