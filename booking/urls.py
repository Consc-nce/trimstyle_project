"""
URL routing for booking app.
"""
from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    # Service management
    path('services/', views.service_list, name='service_list'),
    
    # Booking flow
    path('book/<int:service_id>/', views.select_slot, name='select_slot'),
    path('submit/', views.submit_booking, name='submit_booking'),
    path('confirmation/<int:appointment_id>/', views.confirmation, name='confirmation'),
    
    # Appointment management
    path('cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
]