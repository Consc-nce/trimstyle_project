"""
Booking models for TrimStyle appointment system.
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import User


class Service(models.Model):
    """
    Represents a salon/barber service (haircut, shave, coloring, etc.).
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Service name (e.g., Haircut, Beard Trim)'
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text='Detailed service description'
    )
    
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text='Service price in dollars'
    )
    
    duration_minutes = models.PositiveIntegerField(
        help_text='Service duration in minutes (used for slot calculation)'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this service is currently available for booking'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'booking_service'
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} (${self.price} / {self.duration_minutes}min)"
    
    def clean(self):
        """Validate model fields."""
        if self.duration_minutes <= 0:
            raise ValidationError({'duration_minutes': 'Duration must be positive.'})
        if self.price < 0:
            raise ValidationError({'price': 'Price cannot be negative.'})


class StaffProfile(models.Model):
    """
    Extended profile for staff members.
    Links to User model and stores staff-specific information.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'STAFF'},
        help_text='Link to staff user account'
    )
    
    bio = models.TextField(
        blank=True,
        null=True,
        help_text='Staff member biography and specializations'
    )
    
    services = models.ManyToManyField(
        Service,
        related_name='staff_members',
        help_text='Services this staff member can provide'
    )
    
    is_available = models.BooleanField(
        default=True,
        help_text='Whether this staff member is available for booking'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'booking_staff_profile'
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'
        ordering = ['user__first_name', 'user__last_name']
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - Staff"


class WorkingHours(models.Model):
    """
    Staff working hours schedule.
    Defines when a staff member is available for each day of the week.
    """
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    staff = models.ForeignKey(
        StaffProfile,
        on_delete=models.CASCADE,
        related_name='working_hours',
        help_text='Staff member this schedule belongs to'
    )
    
    day_of_week = models.IntegerField(
        choices=DAYS_OF_WEEK,
        help_text='Day of week (0=Monday, 6=Sunday)'
    )
    
    start_time = models.TimeField(
        help_text='Working start time'
    )
    
    end_time = models.TimeField(
        help_text='Working end time'
    )
    
    class Meta:
        db_table = 'booking_working_hours'
        verbose_name = 'Working Hours'
        verbose_name_plural = 'Working Hours'
        unique_together = ('staff', 'day_of_week')
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.staff.user.username} - {self.get_day_of_week_display()}: {self.start_time}-{self.end_time}"
    
    def clean(self):
        """Validate working hours."""
        if self.start_time >= self.end_time:
            raise ValidationError('Start time must be before end time.')


class Appointment(models.Model):
    """
    Represents a booking appointment.
    Links customer, staff, service, and time details.
    """
    STATUS_CHOICES = [
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]
    
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='appointments',
        limit_choices_to={'role': 'CUSTOMER'},
        help_text='Customer who booked the appointment'
    )
    
    staff = models.ForeignKey(
        StaffProfile,
        on_delete=models.CASCADE,
        related_name='appointments',
        help_text='Staff member assigned to the appointment'
    )
    
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name='appointments',
        help_text='Service being provided'
    )
    
    appointment_date = models.DateField(
        help_text='Date of the appointment'
    )
    
    start_time = models.TimeField(
        help_text='Appointment start time'
    )
    
    end_time = models.TimeField(
        help_text='Appointment end time (calculated from service duration)'
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='CONFIRMED',
        help_text='Current status of the appointment'
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Optional notes from customer or staff'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'booking_appointment'
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
        unique_together = ('staff', 'appointment_date', 'start_time')
        ordering = ['-appointment_date', '-start_time']
        indexes = [
            models.Index(fields=['appointment_date', 'status']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['staff', 'appointment_date']),
        ]
    
    def __str__(self):
        return f"{self.customer.username} - {self.service.name} on {self.appointment_date} at {self.start_time}"
    
    def clean(self):
        """Validate appointment."""
        if self.appointment_date < timezone.now().date():
            raise ValidationError('Cannot book appointments in the past.')
        if self.start_time >= self.end_time:
            raise ValidationError('Start time must be before end time.')
    
    def is_upcoming(self):
        """Check if appointment is in the future."""
        from datetime import datetime
        appointment_datetime = datetime.combine(
            self.appointment_date,
            self.start_time
        )
        return appointment_datetime > timezone.now()
    
    def get_duration(self):
        """Get appointment duration in minutes."""
        from datetime import datetime, timedelta
        start = datetime.combine(self.appointment_date, self.start_time)
        end = datetime.combine(self.appointment_date, self.end_time)
        delta = end - start
        return int(delta.total_seconds() // 60)