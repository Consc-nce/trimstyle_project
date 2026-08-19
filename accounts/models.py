"""
User account models for TrimStyle application.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Adds role-based access control and phone number field.
    """
    ROLE_CHOICES = [
        ('CUSTOMER', 'Customer'),
        ('STAFF', 'Staff Member'),
        ('ADMIN', 'Administrator'),
    ]
    
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='CUSTOMER',
        help_text='User role determines access permissions'
    )
    
    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text='User contact phone number'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
    
    def is_customer(self):
        """Check if user is a customer."""
        return self.role == 'CUSTOMER'
    
    def is_staff_member(self):
        """Check if user is a staff member."""
        return self.role == 'STAFF'
    
    def is_admin_user(self):
        """Check if user is an administrator."""
        return self.role == 'ADMIN'