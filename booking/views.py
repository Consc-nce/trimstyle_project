"""
Views for the appointment booking system.
"""
import json
from datetime import datetime, timedelta, time
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from .models import Service, StaffProfile, Appointment
from .utils import get_available_slots, check_slot_availability


@require_http_methods(["GET"])
def service_list(request):
    """
    Display all available services.
    Shows service details with pricing and duration.
    """
    # Get all active services, ordered by name
    services = Service.objects.filter(is_active=True).order_by('name')
    
    # For each service, get staff members who offer it
    services_with_staff = []
    for service in services:
        staff_members = StaffProfile.objects.filter(
            services=service,
            is_available=True
        ).select_related('user')
        
        services_with_staff.append({
            'service': service,
            'staff_count': staff_members.count(),
            'staff_members': staff_members
        })
    
    context = {
        'services_with_staff': services_with_staff,
        'total_services': services.count(),
    }
    
    return render(request, 'booking/service_list.html', context)


@login_required(login_url='accounts:login')
@require_http_methods(["GET", "POST"])
def select_slot(request, service_id):
    """
    Interactive booking slot selection view.
    Handles date selection, staff selection, and time slot generation.
    
    GET: Display the booking form
    POST: Process slot selection (via AJAX)
    """
    # Get the service
    service = get_object_or_404(Service, id=service_id, is_active=True)
    
    if request.method == 'POST':
        # Handle AJAX requests for slot availability
        try:
            data = json.loads(request.body)
            staff_id = data.get('staff_id')
            date_str = data.get('date')
            
            # Validate inputs
            if not staff_id or not date_str:
                return JsonResponse({
                    'success': False,
                    'error': 'Missing required parameters'
                }, status=400)
            
            # Parse the date
            try:
                appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid date format'
                }, status=400)
            
            # Validate date is not in the past
            if appointment_date < timezone.now().date():
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot book appointments in the past'
                }, status=400)
            
            # Validate date is not too far in the future (e.g., max 90 days)
            max_date = timezone.now().date() + timedelta(days=90)
            if appointment_date > max_date:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot book more than 90 days in advance'
                }, status=400)
            
            # Get the staff member
            staff = get_object_or_404(StaffProfile, id=staff_id, is_available=True)
            
            # Check if staff offers this service
            if not staff.services.filter(id=service_id).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'This staff member does not offer this service'
                }, status=400)
            
            # Get available slots
            available_slots = get_available_slots(staff, service, appointment_date)
            
            if not available_slots:
                return JsonResponse({
                    'success': False,
                    'error': 'No available slots for this date',
                    'slots': []
                })
            
            return JsonResponse({
                'success': True,
                'slots': available_slots,
                'staff_name': f"{staff.user.first_name} {staff.user.last_name}",
                'service_name': service.name,
                'date': appointment_date.strftime('%B %d, %Y'),
            })
        
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)
    
    # GET: Display the booking form
    # Get available staff members who offer this service
    staff_members = StaffProfile.objects.filter(
        services=service,
        is_available=True
    ).select_related('user').order_by('user__first_name', 'user__last_name')
    
    if not staff_members.exists():
        messages.warning(request, 'No staff members available for this service.')
        return redirect('booking:service_list')
    
    # Calculate min and max booking dates
    today = timezone.now().date()
    min_date = today
    max_date = today + timedelta(days=90)
    
    context = {
        'service': service,
        'staff_members': staff_members,
        'min_date': min_date.isoformat(),
        'max_date': max_date.isoformat(),
        'today': today.isoformat(),
    }
    
    return render(request, 'booking/select_slot.html', context)


@login_required(login_url='accounts:login')
@require_http_methods(["POST"])
@transaction.atomic
def submit_booking(request):
    """
    Process and confirm a booking appointment.
    
    Uses atomic transaction to ensure data consistency.
    Performs final verification against double-booking before creation.
    """
    service_id = request.POST.get('service_id')
    staff_id = request.POST.get('staff_id')
    date_str = request.POST.get('appointment_date')
    start_time_str = request.POST.get('start_time')
    
    # Validate all required fields
    errors = []
    
    if not service_id:
        errors.append('Service selection is required.')
    if not staff_id:
        errors.append('Staff member selection is required.')
    if not date_str:
        errors.append('Appointment date is required.')
    if not start_time_str:
        errors.append('Appointment time is required.')
    
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('booking:service_list')
    
    # Get and validate service
    service = get_object_or_404(Service, id=service_id, is_active=True)
    
    # Get and validate staff
    staff = get_object_or_404(StaffProfile, id=staff_id, is_available=True)
    
    # Validate staff offers this service
    if not staff.services.filter(id=service_id).exists():
        messages.error(request, 'This staff member does not offer this service.')
        return redirect('booking:service_list')
    
    # Parse and validate date
    try:
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Invalid appointment date format.')
        return redirect('booking:service_list')
    
    # Validate date is not in the past
    if appointment_date < timezone.now().date():
        messages.error(request, 'Cannot book appointments in the past.')
        return redirect('booking:service_list')
    
    # Validate date is not too far in the future
    max_date = timezone.now().date() + timedelta(days=90)
    if appointment_date > max_date:
        messages.error(request, 'Cannot book more than 90 days in advance.')
        return redirect('booking:service_list')
    
    # Parse and validate start time
    try:
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
    except ValueError:
        messages.error(request, 'Invalid appointment time format.')
        return redirect('booking:service_list')
    
    # Perform final availability check
    # This double-checks to prevent race conditions
    is_available, error_msg = check_slot_availability(
        staff, service, appointment_date, start_time
    )
    
    if not is_available:
        messages.error(request, error_msg or 'This time slot is no longer available.')
        return redirect('booking:service_list')
    
    # Calculate end time based on service duration
    start_datetime = datetime.combine(appointment_date, start_time)
    end_datetime = start_datetime + timedelta(minutes=service.duration_minutes)
    end_time = end_datetime.time()
    
    # Verify end time doesn't exceed working hours (additional safety check)
    weekday = appointment_date.weekday()
    try:
        from .models import WorkingHours
        working_hours = WorkingHours.objects.get(staff=staff, day_of_week=weekday)
        work_end = working_hours.end_time
        
        if end_time > work_end:
            messages.error(request, 'Selected time slot extends beyond working hours.')
            return redirect('booking:service_list')
    except:
        pass
    
    # Create the appointment (atomic transaction ensures consistency)
    appointment = Appointment.objects.create(
        customer=request.user,
        staff=staff,
        service=service,
        appointment_date=appointment_date,
        start_time=start_time,
        end_time=end_time,
        status='CONFIRMED'
    )
    
    messages.success(request, f'Appointment confirmed for {appointment_date} at {start_time.strftime("%I:%M %p")}')
    
    return redirect('booking:confirmation', appointment_id=appointment.id)


@login_required(login_url='accounts:login')
@require_http_methods(["GET"])
def confirmation(request, appointment_id):
    """
    Display appointment confirmation details.
    """
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        customer=request.user
    )
    
    context = {
        'appointment': appointment,
        'service_price': appointment.service.price,
        'appointment_datetime': f"{appointment.appointment_date.strftime('%B %d, %Y')} at {appointment.start_time.strftime('%I:%M %p')}",
    }
    
    return render(request, 'booking/confirmation.html', context)


@login_required(login_url='accounts:login')
@require_http_methods(["POST"])
def cancel_appointment(request, appointment_id):
    """
    Cancel a confirmed appointment.
    """
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        customer=request.user,
        status='CONFIRMED'
    )
    
    # Check if appointment is in the future
    if not appointment.is_upcoming():
        messages.error(request, 'Cannot cancel past appointments.')
        return redirect('accounts:dashboard')
    
    appointment.status = 'CANCELLED'
    appointment.save()
    
    messages.success(request, f'Appointment on {appointment.appointment_date} has been cancelled.')
    
    return redirect('accounts:dashboard')