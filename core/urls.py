from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('search/', views.search_trips, name='search_trips'),
    path('trip/<uuid:pk>/', views.trip_detail, name='trip_detail'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # User dashboard and profile
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    
    
    # Booking process
    path('booking/create/<uuid:trip_id>/', views.create_booking, name='create_booking'),
    path('booking/<uuid:pk>/', views.booking_detail, name='booking_detail'),
    path('booking/<uuid:pk>/payment/', views.booking_payment, name='booking_payment'),
    path('booking/<uuid:pk>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('booking/<uuid:booking_id>/review/', views.submit_review, name='submit_review'),
    
    # AJAX endpoints
    path('ajax/check-seats/', views.check_seat_availability, name='check_seat_availability'),
    path('ajax/verify-promo/', views.verify_promotion, name='verify_promotion'),
]

