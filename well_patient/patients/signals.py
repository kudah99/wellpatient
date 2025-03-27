import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from .models import PatientMedication, NotificationLog, BroadcastMessage
from .tasks import send_broadcast_message

logger = logging.getLogger(__name__)

@receiver(post_save, sender=PatientMedication)
def handle_patient_medication_update(sender, instance, created, **kwargs):
    """
    Signal handler to manage PatientMedication changes.
    Updates next refill date if necessary and logs any important changes.
    """
    if created:
        logger.info(f"New medication {instance.medication} assigned to patient {instance.patient}")
    else:
        # If medication was previously inactive and now active, recalculate next refill date
        if instance.is_active and instance.tracker.has_changed('is_active') and not instance.tracker.previous('is_active'):
            # Calculate new refill date based on current date
            instance.next_refill_date = timezone.now().date() + timedelta(days=instance.medication.refill_period_days)
            # Save again but don't trigger this signal recursively
            PatientMedication.objects.filter(pk=instance.pk).update(next_refill_date=instance.next_refill_date)
            logger.info(f"Reactivated medication {instance.medication} for patient {instance.patient}, "
                        f"next refill set to {instance.next_refill_date}")


@receiver(post_save, sender=BroadcastMessage)
def handle_broadcast_creation(sender, instance, created, **kwargs):
    """
    Signal handler for broadcast message creation/updates.
    Queues immediate broadcast messages for sending.
    """
    # If a new broadcast has been created with a SENDING status, immediately queue it for sending
    if (created or instance.tracker.has_changed('status')) and instance.status == 'SENDING':
        logger.info(f"Queuing immediate broadcast: {instance.title}")
        send_broadcast_message.delay(instance.id)


@receiver(pre_save, sender=NotificationLog)
def handle_notification_status_update(sender, instance, **kwargs):
    """
    Signal handler for tracking notification status changes.
    Logs when a notification is sent or when it fails.
    """
    if not instance.pk:  # New notification
        return
    
    old_status = NotificationLog.objects.get(pk=instance.pk).status
    
    if old_status != instance.status:
        if instance.status == 'SENT':
            logger.info(f"Notification to {instance.patient} successfully sent via {instance.get_channel_display()}")
        elif instance.status == 'FAILED':
            logger.warning(f"Notification to {instance.patient} failed: {instance.status_message}")
