import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
import datetime

from .models import (
    Patient, PatientMedication, NotificationLog, 
    NotificationType, BroadcastMessage
)
from .utils import send_sms, send_whatsapp

logger = logging.getLogger(__name__)

@shared_task
def check_medication_resupply():
    """
    Task to check for upcoming medication resupplies and send reminders.
    Runs daily to identify patients who need refills in a week.
    """
    logger.info("Running medication resupply check...")
    today = timezone.now().date()
    notification_date = today + datetime.timedelta(days=7)
    
    # Get all active patient medications due for refill in 7 days
    patient_meds = PatientMedication.objects.filter(
        next_refill_date=notification_date,
        is_active=True
    ).select_related('patient', 'medication')
    
    logger.info(f"Found {patient_meds.count()} medications due for refill in 7 days")
    
    # Get or create the refill notification type
    refill_type, _ = NotificationType.objects.get_or_create(
        name="Medication Refill Reminder",
        defaults={
            "template_sms": "Hello {patient_name}, this is a reminder that you need to refill your {medication_name} in one week. Please contact us to arrange your refill.",
            "template_whatsapp": "Hello {patient_name}, this is a reminder that you need to refill your {medication_name} in one week. Please contact us to arrange your refill."
        }
    )
    
    # Send notifications to each patient
    for patient_med in patient_meds:
        patient = patient_med.patient
        medication = patient_med.medication
        
        # Skip inactive patients or those who don't want notifications
        if not patient.is_active or patient.notification_preference == 'NONE':
            continue
        
        # Prepare message data
        message_data = {
            'patient_name': patient.get_full_name(),
            'medication_name': medication.name,
            'refill_date': patient_med.next_refill_date.strftime('%Y-%m-%d')
        }
        
        # Schedule SMS if patient wants it
        if patient.notification_preference in ['SMS', 'BOTH']:
            sms_message = refill_type.template_sms.format(**message_data)
            notify_patient.delay(
                patient.id,
                refill_type.id,
                'SMS',
                sms_message,
                today.isoformat()
            )
        
        # Schedule WhatsApp if patient wants it
        if patient.notification_preference in ['WA', 'BOTH']:
            wa_message = refill_type.template_whatsapp.format(**message_data)
            notify_patient.delay(
                patient.id,
                refill_type.id,
                'WA',
                wa_message,
                today.isoformat()
            )
    
    return f"Scheduled notifications for {patient_meds.count()} patients"


@shared_task
def notify_patient(patient_id, notification_type_id, channel, message, scheduled_date):
    """
    Task to send a notification to a patient via the specified channel.
    """
    try:
        patient = Patient.objects.get(id=patient_id)
        notification_type = NotificationType.objects.get(id=notification_type_id)
        scheduled_time = datetime.datetime.fromisoformat(scheduled_date)
        
        # Create notification log entry
        notification = NotificationLog.objects.create(
            patient=patient,
            notification_type=notification_type,
            channel=channel,
            message=message,
            scheduled_time=scheduled_time,
            status='PENDING'
        )
        
        # Send the notification based on channel
        if channel == 'SMS':
            success, status_message = send_sms(patient.phone_number, message)
        else:  # WhatsApp
            success, status_message = send_whatsapp(patient.phone_number, message)
        
        # Update notification status
        notification.status = 'SENT' if success else 'FAILED'
        notification.status_message = status_message
        notification.sent_time = timezone.now()
        notification.save()
        
        logger.info(f"Notification {notification.id} sent to {patient.get_full_name()} via {channel}")
        return f"Notification sent to {patient.get_full_name()}"
    
    except Exception as e:
        logger.error(f"Error sending notification to patient {patient_id}: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def send_broadcast_message(broadcast_id):
    """
    Task to send a broadcast message to multiple patients based on location.
    """
    try:
        broadcast = BroadcastMessage.objects.get(pk=broadcast_id)
        
        # Update status to sending
        broadcast.status = 'SENDING'
        broadcast.save()
        
        # Get patients based on locations
        if broadcast.locations.exists():
            patients = Patient.objects.filter(
                location__in=broadcast.locations.all(),
                is_active=True
            ).distinct()
        else:
            # If no locations specified, send to all active patients
            patients = Patient.objects.filter(is_active=True)
        
        logger.info(f"Sending broadcast {broadcast.title} to {patients.count()} patients")
        
        # Create notification type for this broadcast
        notification_type, _ = NotificationType.objects.get_or_create(
            name=f"Broadcast: {broadcast.title}",
            defaults={
                "template_sms": broadcast.message,
                "template_whatsapp": broadcast.message
            }
        )
        
        # Schedule individual notifications
        scheduled_date = timezone.now().isoformat()
        sent_count = 0
        
        for patient in patients:
            # Skip patients who don't want notifications
            if patient.notification_preference == 'NONE':
                continue
                
            # Send SMS if enabled
            if broadcast.send_sms and patient.notification_preference in ['SMS', 'BOTH']:
                notify_patient.delay(
                    patient.id,
                    notification_type.id,
                    'SMS',
                    broadcast.message,
                    scheduled_date
                )
                sent_count += 1
            
            # Send WhatsApp if enabled
            if broadcast.send_whatsapp and patient.notification_preference in ['WA', 'BOTH']:
                notify_patient.delay(
                    patient.id,
                    notification_type.id,
                    'WA',
                    broadcast.message,
                    scheduled_date
                )
                sent_count += 1
        
        # Update status to completed
        broadcast.status = 'COMPLETED'
        broadcast.save()
        
        logger.info(f"Broadcast {broadcast.id} completed, sent {sent_count} notifications")
        return f"Broadcast sent to {patients.count()} patients"
    
    except Exception as e:
        logger.error(f"Error sending broadcast {broadcast_id}: {str(e)}")
        # Update status to failed
        try:
            broadcast = BroadcastMessage.objects.get(id=broadcast_id)
            broadcast.status = 'CANCELLED'
            broadcast.save()
        except:
            pass
        return f"Error: {str(e)}"


@shared_task
def process_scheduled_broadcasts():
    """
    Task to check for scheduled broadcasts that need to be sent.
    """
    now = timezone.now()
    
    # Find broadcasts scheduled for now or in the past
    broadcasts = BroadcastMessage.objects.filter(
        status='SCHEDULED',
        scheduled_time__lte=now
    )
    for broadcast in broadcasts:
        send_broadcast_message.delay(broadcast.pk)
    
    return f"Processed {broadcasts.count()} scheduled broadcasts"
