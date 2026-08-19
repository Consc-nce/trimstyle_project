"""
Django admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin interface.
    Extends Django's default UserAdmin to include custom fields.
    """
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'phone')}),
    )
    
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'phone',
        'is_staff',
        'is_superuser',
    )
    
    list_filter = BaseUserAdmin.list_filter + ('role',)
    
    search_fields = BaseUserAdmin.search_fields + ('phone', 'role')
    
    ordering = ('-date_joined',)