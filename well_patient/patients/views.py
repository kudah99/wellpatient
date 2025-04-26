from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import logging
from django.utils import timezone
from django.db.models import  Q
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from unfold.views import UnfoldModelAdminViewMixin
from .models import (
    Patient, Location, Medication, PatientMedication,
    NotificationLog, BroadcastMessage
)
import json
from .forms import (
    PatientFilterForm, SendBroadcastForm, BroadcastFilterForm,
    ImportPatientForm
)
from .utils import process_import_file,send_whatsapp
from .tasks import send_broadcast_message

# Initialize logging
logger = logging.getLogger(__name__)

def dashboard_callback(request, context):
    """Main dashboard view showing stats and recent notifications"""
    # Get counts for dashboard
    patient_count = Patient.objects.filter(is_active=True).count()
    locations_count = Location.objects.count()
    medications_count = Medication.objects.count()
    
    # Recent notifications
    recent_notifications = NotificationLog.objects.order_by('-sent_time')[:10]
    
    # Upcoming refills in the next week
    today = timezone.now().date()
    next_week = today + timezone.timedelta(days=7)
    upcoming_refills = PatientMedication.objects.filter(
        next_refill_date__range=[today, next_week],
        is_active=True
    ).select_related('patient', 'medication')
    
    # Pending broadcasts
    pending_broadcasts = BroadcastMessage.objects.filter(
        status__in=['SCHEDULED', 'SENDING']
    ).order_by('scheduled_time')[:5]
    
    context.update({
        'title': "WELL PATIENT Administration",
        'patient_count': patient_count,
        'locations_count': locations_count,
        'medications_count': medications_count,
        'recent_notifications': recent_notifications,
        'upcoming_refills': upcoming_refills,
        'pending_broadcasts': pending_broadcasts,
    })
    return context

@method_decorator(login_required, name='dispatch')
class PatientListView(UnfoldModelAdminViewMixin, TemplateView):
    title = "Patients"
    permission_required = ()  # set your permissions if needed
    template_name = 'patients/patient_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        queryset = Patient.objects.all()
        form = PatientFilterForm(self.request.GET)

        if form.is_valid():
            location = form.cleaned_data.get('location')
            is_active = form.cleaned_data.get('is_active')
            notification_preference = form.cleaned_data.get('notification_preference')
            search = form.cleaned_data.get('search')

            if location:
                queryset = queryset.filter(location=location)
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active)
            if notification_preference:
                queryset = queryset.filter(notification_preference=notification_preference)
            if search:
                queryset = queryset.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(phone_number__icontains=search) |
                    Q(email__icontains=search)
                )

        context['patients'] = queryset.select_related('location')
        context['filter_form'] = form
        return context


@method_decorator(login_required, name='dispatch')
class PatientDetailView(UnfoldModelAdminViewMixin, TemplateView):
    title = "Patient Details"
    permission_required = ()
    template_name = 'patients/patient_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient_id = self.kwargs.get('pk')
        patient = Patient.objects.get(pk=patient_id)

        context['patient'] = patient
        context['medications'] = PatientMedication.objects.filter(
            patient=patient
        ).select_related('medication')

        context['notifications'] = NotificationLog.objects.filter(
            patient=patient
        ).order_by('-sent_time')[:10]

        return context

class BroadcastMessageView(UnfoldModelAdminViewMixin, TemplateView):
    title = "Send Broadcast Message"
    permission_required = ()
    template_name = 'admin/broadcast_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SendBroadcastForm(self.request.POST or None)
        return context

    def post(self, request, *args, **kwargs):
        form = SendBroadcastForm(request.POST)
        if form.is_valid():
            broadcast = BroadcastMessage(
                title=form.cleaned_data['title'],
                message=form.cleaned_data['message'],
                broadcast_type=form.cleaned_data['broadcast_type'],
                send_sms=form.cleaned_data['send_sms'],
                send_whatsapp=form.cleaned_data['send_whatsapp'],
                scheduled_time=form.cleaned_data.get('scheduled_time'),
                status='SCHEDULED' if form.cleaned_data.get('scheduled_time') else 'SENDING',
                created_by=request.user
            )
            broadcast.save()

            locations = form.cleaned_data.get('locations')
            if locations:
                broadcast.locations.set(locations)

            if not form.cleaned_data.get('scheduled_time'):
               # send_broadcast_message.delay(broadcast.id)
                messages.success(request, "Broadcast message is being sent.")
            else:
                messages.success(request, "Broadcast message has been scheduled.")

            return redirect(reverse_lazy("admin:broadcast_messages"))

        return self.render_to_response({'form': form})


@method_decorator(login_required, name='dispatch')
class BroadcastListView(UnfoldModelAdminViewMixin, TemplateView):
    title = "Broadcast Messages"
    permission_required = ()
    template_name = 'admin/broadcast_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = BroadcastFilterForm(self.request.GET)
        broadcasts = BroadcastMessage.objects.all().order_by('-created_at')

        if form.is_valid():
            status = form.cleaned_data.get('status')
            broadcast_type = form.cleaned_data.get('broadcast_type')
            location = form.cleaned_data.get('location')
            from_date = form.cleaned_data.get('from_date')
            to_date = form.cleaned_data.get('to_date')

            if status:
                broadcasts = broadcasts.filter(status=status)
            if broadcast_type:
                broadcasts = broadcasts.filter(broadcast_type=broadcast_type)
            if location:
                broadcasts = broadcasts.filter(locations=location)
            if from_date:
                broadcasts = broadcasts.filter(created_at__gte=from_date)
            if to_date:
                broadcasts = broadcasts.filter(created_at__lte=to_date)

        context['broadcasts'] = broadcasts
        context['filter_form'] = form
        return context


class ImportPatientsView(UnfoldModelAdminViewMixin, LoginRequiredMixin, TemplateView):
    title = "Import Patients"
    permission_required = ()  # Add required permissions if needed
    template_name = "admin/import_patients.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ImportPatientForm()
        return context

    def post(self, request, *args, **kwargs):
        form = ImportPatientForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            update_existing = form.cleaned_data['update_existing']
            
            try:
                result = process_import_file(file, update_existing)
                messages.success(
                    request, 
                    f"Successfully imported {result['created']} new patients and updated {result['updated']} existing patients."
                )
                return redirect(reverse_lazy("admin:patients_patient_changelist"))
            except Exception as e:
                messages.error(request, f"Error importing patients: {str(e)}")
        
        # If form is invalid or exception occurs, re-render the form with errors
        return self.render_to_response(self.get_context_data(form=form))


@login_required
def cancel_broadcast(request, pk):
    """View to cancel a scheduled broadcast"""
    broadcast = get_object_or_404(BroadcastMessage, pk=pk)
    
    if broadcast.status in ['DRAFT', 'SCHEDULED']:
        broadcast.status = 'CANCELLED'
        broadcast.save()
        messages.success(request, "Broadcast has been cancelled.")
    else:
        messages.error(request, "Cannot cancel a broadcast that has already been sent or completed.")
    
    return redirect('broadcast_messages')


@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "GET":
        # Handle WhatsApp Webhook Verification
        VERIFY_TOKEN = "@vd7uHW1M"
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            logger.info("Webhook verification successful.")
            return HttpResponse(challenge, status=200)
        else:
            logger.error("Webhook verification failed. Invalid token.")
            return HttpResponse("Forbidden", status=403)
    
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            logger.info(f"Incoming webhook data: {data}")
            
            # Extract message details
            entry = data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            message = value.get('messages', [{}])[0]
            
            if not message:
                return HttpResponse("OK", status=200)
                
            # Extract phone number and message text
            phone_number = message.get('from', '')
            message_body = message.get('text', {}).get('body', '').strip().upper()
            
            if not phone_number:
                return HttpResponse("OK", status=200)
            
            # Prepare response
            if message_body == "CANCEL":
                response_text = "You have successfully unsubscribed from Well PATIENT notifications. You will no longer receive medication refill reminders from us."
                # Here you would typically update your database to mark this user as unsubscribed
                logger.info(f"User {phone_number} unsubscribed")
            else:
                response_text = """Welcome to Well PATIENT! 
A platform that sends medical refill reminders to help you stay on track with your medications.

Reply CANCEL to no longer receive these and other notification texts from us."""
            
            # Construct response payload
            send_whatsapp(phone_number, response_text)
            
            # Send response (you'll need to implement this part)
            # send_whatsapp_message(response_payload)
            logger.info(f"Prepared response for {phone_number}: {response_text}")
            
            return HttpResponse("OK", status=200)
            
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return HttpResponse("OK", status=200)
    
    return HttpResponse("Method Not Allowed", status=405)