"""
Main URL routing configuration for TrimStyle project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # App URLs
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('booking/', include('booking.urls', namespace='booking')),
    
    # Landing page
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
]