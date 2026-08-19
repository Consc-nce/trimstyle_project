"""
Utility functions for appointment booking.
Core algorithm for calculating available time slots.
"""
from datetime import datetime, timedelta, time
from django.utils import timezone

from .models import Appointment, WorkingHours


def get_available_slots(staff_profile, service, date_obj):
    """
    Calculate available appointment slots for a staff member on a specific date.
    
    Algorithm:
    1. Get the weekday of the requested date (0=Monday, 6=Sunday)
    2. Query the staff's WorkingHours for that weekday
    3. If no working hours defined, return empty list
    4. Generate discrete time slots based on service duration
    5. Filter out time slots with existing CONFIRMED appointments
    6. Return list of available (start_time, end_time) tuples
    
    Args:
        staff_profile (StaffProfile): The staff member
        service (Service): The service being booked
        date_obj (date): The requested appointment date
    
    Returns:
        list: List of available time slots as (start_time, end_time) tuples
    """
    available_slots = []
    
    # Get the weekday (0=Monday, 6=Sunday)
    weekday = date_obj.weekday()
    
    # Query the staff's working hours for this weekday
    # WorkingHours.day_of_week uses 0=Monday to 6=Sunday format
    try:
        working_hours = WorkingHours.objects.get(
            staff=staff_profile,
            day_of_week=weekday
        )
    except WorkingHours.DoesNotExist:
        # Staff doesn't work on this day
        return available_slots
    
    # Get the service duration in minutes
    duration_minutes = service.duration_minutes
    
    # Convert working hours to datetime objects for manipulation
    work_start = datetime.combine(date_obj, working_hours.start_time)
    work_end = datetime.combine(date_obj, working_hours.end_time)
    
    # Query all CONFIRMED appointments for this staff on this date
    # This prevents double-booking
    existing_appointments = Appointment.objects.filter(
        staff=staff_profile,
        appointment_date=date_obj,
        status='CONFIRMED'
    ).values_list('start_time', 'end_time').order_by('start_time')
    
    # Convert appointment times to datetime objects for range checking
    booked_slots = [
        (datetime.combine(date_obj, appt[0]), datetime.combine(date_obj, appt[1]))
        for appt in existing_appointments
    ]
    
    # Generate all possible slots based on service duration
    current_slot_start = work_start
    
    while True:
        # Calculate the end time of this potential slot
        current_slot_end = current_slot_start + timedelta(minutes=duration_minutes)
        
        # Check if slot extends beyond working hours
        if current_slot_end > work_end:
            break
        
        # Check if this slot conflicts with any booked appointment
        slot_is_available = True
        for booked_start, booked_end in booked_slots:
            # Two intervals [a,b] and [c,d] overlap if a < d and c < b
            if current_slot_start < booked_end and booked_start < current_slot_end:
                slot_is_available = False
                break
        
        # If slot is available, add it to the list
        if slot_is_available:
            available_slots.append({
                'start_time': current_slot_start.time(),
                'end_time': current_slot_end.time(),
                'display': f"{current_slot_start.strftime('%I:%M %p')} - {current_slot_end.strftime('%I:%M %p')}"
            })
        
        # Move to the next potential slot (increment by duration)
        current_slot_start = current_slot_start + timedelta(minutes=duration_minutes)
    
    return available_slots


def check_slot_availability(staff_profile, service, date_obj, start_time):
    """
    Check if a specific time slot is available for booking.
    
    This is a security/validation check to prevent race conditions
    where two simultaneous booking requests might create overlapping appointments.
    
    Args:
        staff_profile (StaffProfile): The staff member
        service (Service): The service being booked
        date_obj (date): The appointment date
        start_time (time): The requested start time
    
    Returns:
        tuple: (is_available, error_message)
    """
    # Get available slots for this staff/service/date
    available_slots = get_available_slots(staff_profile, service, date_obj)
    
    # Check if the requested start time exists in available slots
    for slot in available_slots:
        if slot['start_time'] == start_time:
            return True, None
    
    return False, "This time slot is no longer available. Please select another time."


def get_next_available_date(staff_profile, service, start_from_date=None):
    """
    Find the next date when the staff member has available slots for a service.
    
    Useful for showing "Next available: [Date]" on the UI.
    
    Args:
        staff_profile (StaffProfile): The staff member
        service (Service): The service being booked
        start_from_date (date, optional): Date to start searching from. Defaults to today.
    
    Returns:
        date or None: First available date, or None if none found in next 30 days
    """
    if start_from_date is None:
        start_from_date = timezone.now().date()
    
    # Search up to 30 days in advance
    for days_ahead in range(0, 30):
        search_date = start_from_date + timedelta(days=days_ahead)
        available_slots = get_available_slots(staff_profile, service, search_date)
        
        if available_slots:
            return search_date
    
    return None


def get_staff_utilization(staff_profile, date_obj):
    """
    Calculate how busy a staff member is on a given date.
    
    Returns the total minutes booked out of total working minutes.
    
    Args:
        staff_profile (StaffProfile): The staff member
        date_obj (date): The date to check
    
    Returns:
        dict: {
            'working_minutes': int,
            'booked_minutes': int,
            'utilization_percent': float,
            'available_minutes': int
        }
    """
    weekday = date_obj.weekday()
    
    try:
        working_hours = WorkingHours.objects.get(
            staff=staff_profile,
            day_of_week=weekday
        )
    except WorkingHours.DoesNotExist:
        return {
            'working_minutes': 0,
            'booked_minutes': 0,
            'utilization_percent': 0,
            'available_minutes': 0
        }
    
    # Calculate total working minutes
    work_start = datetime.combine(date_obj, working_hours.start_time)
    work_end = datetime.combine(date_obj, working_hours.end_time)
    working_minutes = int((work_end - work_start).total_seconds() / 60)
    
    # Calculate booked minutes
    booked_appointments = Appointment.objects.filter(
        staff=staff_profile,
        appointment_date=date_obj,
        status='CONFIRMED'
    ).values_list('start_time', 'end_time')
    
    booked_minutes = 0
    for start_time, end_time in booked_appointments:
        start_dt = datetime.combine(date_obj, start_time)
        end_dt = datetime.combine(date_obj, end_time)
        booked_minutes += int((end_dt - start_dt).total_seconds() / 60)
    
    # Calculate utilization percentage
    utilization_percent = (booked_minutes / working_minutes * 100) if working_minutes > 0 else 0
    available_minutes = working_minutes - booked_minutes
    
    return {
        'working_minutes': working_minutes,
        'booked_minutes': booked_minutes,
        'utilization_percent': round(utilization_percent, 1),
        'available_minutes': available_minutes
    }