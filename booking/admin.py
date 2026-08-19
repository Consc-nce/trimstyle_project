"""
Django admin configuration for booking app.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Service, StaffProfile, WorkingHours, Appointment


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """
    Admin interface for Service model.
    """
    list_display = (
        'name',
        'price_display',
        'duration_minutes',
        'is_active',
        'created_at'
    )
    
    list_filter = ('is_active', 'created_at')
    
    search_fields = ('name', 'description')
    
    fieldsets = (
        ('Service Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Booking Details', {
            'fields': ('price', 'duration_minutes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def price_display(self, obj):
        return f"${obj.price}"
    price_display.short_description = 'Price'


class WorkingHoursInline(admin.TabularInline):
    """
    Inline admin for managing staff working hours.
    """
    model = WorkingHours
    extra = 1
    fields = ('day_of_week', 'start_time', 'end_time')


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for StaffProfile model.
    """
    list_display = (
        'staff_name',
        'service_count',
        'is_available',
        'created_at'
    )
    
    list_filter = ('is_available', 'created_at')
    
    search_fields = ('user__first_name', 'user__last_name', 'user__username')
    
    filter_horizontal = ('services',)
    
    fieldsets = (
        ('Staff Information', {
            'fields': ('user', 'bio', 'is_available')
        }),
        ('Services Offered', {
            'fields': ('services',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    inlines = [WorkingHoursInline]
    
    def staff_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
    staff_name.short_description = 'Staff Name'
    
    def service_count(self, obj):
        return obj.services.count()
    service_count.short_description = 'Services'


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    """
    Admin interface for WorkingHours model.
    """
    list_display = (
        'staff_name',
        'day_of_week',
        'time_range'
    )
    
    list_filter = ('day_of_week', 'staff__user__username')
    
    search_fields = ('staff__user__first_name', 'staff__user__last_name')
    
    fieldsets = (
        ('Assignment', {
            'fields': ('staff', 'day_of_week')
        }),
        ('Working Hours', {
            'fields': ('start_time', 'end_time')
        }),
    )
    
    def staff_name(self, obj):
        return f"{obj.staff.user.first_name} {obj.staff.user.last_name}".strip() or obj.staff.user.username
    staff_name.short_description = 'Staff'
    
    def time_range(self, obj):
        return f"{obj.start_time.strftime('%I:%M %p')} - {obj.end_time.strftime('%I:%M %p')}"
    time_range.short_description = 'Hours'


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """
    Admin interface for Appointment model.
    """
    list_display = (
        'customer_name',
        'service_name',
        'staff_name',
        'appointment_date',
        'time_slot',
        'status_badge',
        'created_at'
    )
    
    list_filter = ('status', 'appointment_date', 'service')
    
    search_fields = (
        'customer__username',
        'customer__first_name',
        'customer__last_name',
        'staff__user__first_name',
        'staff__user__last_name',
        'service__name'
    )
    
    fieldsets = (
        ('Appointment Details', {
            'fields': ('customer', 'staff', 'service', 'status')
        }),
        ('Scheduling', {
            'fields': ('appointment_date', 'start_time', 'end_time')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    date_hierarchy = 'appointment_date'
    
    ordering = ('-appointment_date', '-start_time')
    
    def customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}".strip() or obj.customer.username
    customer_name.short_description = 'Customer'
    
    def service_name(self, obj):
        return obj.service.name
    service_name.short_description = 'Service'
    
    def staff_name(self, obj):
        return f"{obj.staff.user.first_name} {obj.staff.user.last_name}".strip() or obj.staff.user.username
    staff_name.short_description = 'Staff'
    
    def time_slot(self, obj):
        return f"{obj.start_time.strftime('%I:%M %p')} - {obj.end_time.strftime('%I:%M %p')}"
    time_slot.short_description = 'Time'
    
    def status_badge(self, obj):
        colors = {
            'CONFIRMED': '#28a745',
            'CANCELLED': '#dc3545',
            'COMPLETED': '#007bff',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'