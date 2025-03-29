from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import (
    Patient, Location, Medication, PatientMedication,
    NotificationLog, BroadcastMessage
)
from .forms import (
    PatientFilterForm, SendBroadcastForm, BroadcastFilterForm,
    ImportPatientForm
)
from .utils import process_import_file
from .tasks import send_broadcast_message


@login_required
def dashboard(request):
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
    
    context = {
        'patient_count': patient_count,
        'locations_count': locations_count,
        'medications_count': medications_count,
        'recent_notifications': recent_notifications,
        'upcoming_refills': upcoming_refills,
        'pending_broadcasts': pending_broadcasts,
    }
    return render(request, 'patients/dashboard.html', context)


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
        'site_title': "Well PATIENT Administration",
        'patient_count': patient_count,
        'locations_count': locations_count,
        'medications_count': medications_count,
        'recent_notifications': recent_notifications,
        'upcoming_refills': upcoming_refills,
        'pending_broadcasts': pending_broadcasts,
    })
    return context

@method_decorator(login_required, name='dispatch')
class PatientListView(ListView):
    """View for listing all patients with filtering options"""
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Patient.objects.all()
        
        # Apply filters from form
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
        
        return queryset.select_related('location')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = PatientFilterForm(self.request.GET)
        return context


@method_decorator(login_required, name='dispatch')
class PatientDetailView(DetailView):
    """View for displaying patient details"""
    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.get_object()
        
        # Get medications for the patient
        context['medications'] = PatientMedication.objects.filter(
            patient=patient
        ).select_related('medication')
        
        # Get recent notifications
        context['notifications'] = NotificationLog.objects.filter(
            patient=patient
        ).order_by('-sent_time')[:10]
        
        return context


@login_required
def broadcast_message_view(request):
    """View for sending broadcast messages"""
    if request.method == 'POST':
        form = SendBroadcastForm(request.POST)
        if form.is_valid():
            # Create the broadcast message
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
            
            # Add locations
            locations = form.cleaned_data.get('locations')
            if locations:
                broadcast.locations.set(locations)
            
            # If no scheduled time, send immediately
            if not form.cleaned_data.get('scheduled_time'):
                send_broadcast_message.delay(broadcast.id)
                messages.success(request, "Broadcast message is being sent.")
            else:
                messages.success(request, "Broadcast message has been scheduled.")
            
            return redirect('broadcast_list')
    else:
        form = SendBroadcastForm()
    
    return render(request, 'patients/broadcast_form.html', {'form': form})


@login_required
def broadcast_list_view(request):
    """View for listing all broadcast messages with filtering"""
    # Initialize form and queryset
    form = BroadcastFilterForm(request.GET)
    broadcasts = BroadcastMessage.objects.all().order_by('-created_at')
    
    # Apply filters
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
    
    context = {
        'broadcasts': broadcasts,
        'filter_form': form
    }
    
    return render(request, 'patients/broadcast_list.html', context)


@login_required
def import_patients_view(request):
    """View for importing patients from CSV/Excel files"""
    if request.method == 'POST':
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
                return redirect('patient_list')
            except Exception as e:
                messages.error(request, f"Error importing patients: {str(e)}")
    else:
        form = ImportPatientForm()
    
    return render(request, 'patients/import_patients.html', {'form': form})


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
    
    return redirect('broadcast_list')
