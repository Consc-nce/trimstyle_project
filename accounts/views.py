"""
Authentication and account management views.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta

from .models import User
from booking.models import Appointment, StaffProfile


@require_http_methods(["GET", "POST"])
def register(request):
    """
    User registration view.
    Handles both GET (show form) and POST (process registration) requests.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        role = request.POST.get('role', 'CUSTOMER')
        
        # Validate input
        errors = []
        
        if not username:
            errors.append('Username is required.')
        elif User.objects.filter(username=username).exists():
            errors.append('Username already taken.')
        
        if not email:
            errors.append('Email is required.')
        elif User.objects.filter(email=email).exists():
            errors.append('Email already registered.')
        
        if not password:
            errors.append('Password is required.')
        elif len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        
        if password != password_confirm:
            errors.append('Passwords do not match.')
        
        if role not in ['CUSTOMER', 'STAFF', 'ADMIN']:
            role = 'CUSTOMER'
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'accounts/register.html', {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
            })
        
        # Create new user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=role
        )
        
        # Log the user in after registration
        login(request, user)
        messages.success(request, f'Welcome, {user.first_name or user.username}!')
        return redirect('accounts:dashboard')
    
    return render(request, 'accounts/register.html')


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    User login view.
    Handles both GET (show form) and POST (process login) requests.
    """
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username or not password:
            messages.error(request, 'Please enter both username and password.')
            return render(request, 'accounts/login.html', {'username': username})
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect('accounts:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
            return render(request, 'accounts/login.html', {'username': username})
    
    return render(request, 'accounts/login.html')


@require_http_methods(["POST"])
def logout_view(request):
    """
    User logout view.
    Only accepts POST requests for security.
    """
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('index')


@login_required(login_url='accounts:login')
def dashboard(request):
    """
    Role-aware dashboard view.
    Customers see their upcoming appointments.
    Staff members see their schedule and client bookings.
    Admins see all system appointments.
    """
    user = request.user
    context = {
        'user': user,
        'is_customer': user.is_customer(),
        'is_staff': user.is_staff_member(),
        'is_admin': user.is_admin_user(),
    }
    
    # Get current date and time
    now = timezone.now()
    
    if user.is_customer():
        # Fetch customer's upcoming appointments
        upcoming_appointments = Appointment.objects.filter(
            customer=user,
            status='CONFIRMED',
            appointment_date__gte=now.date()
        ).select_related(
            'staff__user',
            'service'
        ).order_by('appointment_date', 'start_time')
        
        # Fetch past appointments
        past_appointments = Appointment.objects.filter(
            customer=user,
            appointment_date__lt=now.date()
        ).select_related(
            'staff__user',
            'service'
        ).order_by('-appointment_date', '-start_time')[:5]
        
        context.update({
            'upcoming_appointments': upcoming_appointments,
            'past_appointments': past_appointments,
            'appointment_count': upcoming_appointments.count(),
        })
    
    elif user.is_staff_member():
        # Fetch the staff profile
        try:
            staff_profile = user.staffprofile
        except StaffProfile.DoesNotExist:
            staff_profile = None
        
        if staff_profile:
            # Fetch today's appointments for this staff member
            today_appointments = Appointment.objects.filter(
                staff=staff_profile,
                status='CONFIRMED',
                appointment_date=now.date()
            ).select_related(
                'customer',
                'service'
            ).order_by('start_time')
            
            # Fetch upcoming appointments (next 7 days)
            upcoming_appointments = Appointment.objects.filter(
                staff=staff_profile,
                status='CONFIRMED',
                appointment_date__gte=now.date(),
                appointment_date__lte=now.date() + timedelta(days=7)
            ).select_related(
                'customer',
                'service'
            ).order_by('appointment_date', 'start_time')
            
            context.update({
                'staff_profile': staff_profile,
                'today_appointments': today_appointments,
                'upcoming_appointments': upcoming_appointments,
                'services': staff_profile.services.all(),
            })
    
    elif user.is_admin_user():
        # Fetch all appointments for admin overview
        total_appointments = Appointment.objects.filter(
            status='CONFIRMED'
        ).count()
        
        today_appointments = Appointment.objects.filter(
            status='CONFIRMED',
            appointment_date=now.date()
        ).select_related(
            'customer',
            'staff__user',
            'service'
        ).order_by('start_time')
        
        context.update({
            'total_appointments': total_appointments,
            'today_appointments': today_appointments,
            'total_customers': User.objects.filter(role='CUSTOMER').count(),
            'total_staff': User.objects.filter(role='STAFF').count(),
        })
    
    return render(request, 'accounts/dashboard.html', context)