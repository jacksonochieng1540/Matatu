# core/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from .models import *
from .forms import *
from .utils import send_sms, send_mail, generate_qr_code, initiate_mpesa_payment
import json



def home(request):
    """Homepage"""
    popular_routes = Route.objects.filter(is_active=True)[:6]
    recent_reviews = Review.objects.select_related('customer', 'sacco').filter(is_verified=True)[:6]
    
    context = {
        'popular_routes': popular_routes,
        'recent_reviews': recent_reviews,
    }
    return render(request, 'core/home.html', context)


def search_trips(request):
    """Search for available trips"""
    form = TripSearchForm(request.GET or None)
    trips = None
    
    if request.GET and form.is_valid():
        origin = form.cleaned_data.get('origin')
        destination = form.cleaned_data.get('destination')
        travel_date = form.cleaned_data.get('travel_date')
        passengers = form.cleaned_data.get('passengers', 1)
        
        # Get trips for the selected route and date
        trips = Trip.objects.filter(
            route__origin=origin,
            route__destination=destination,
            departure_date=travel_date,
            status='scheduled',
            available_seats__gte=passengers
        ).select_related('route', 'vehicle', 'sacco', 'driver').order_by('departure_time')
        
        # Check if trips are bookable
        for trip in trips:
            trip.can_book = trip.is_bookable
    
    context = {
        'form': form,
        'trips': trips,
    }
    return render(request, 'core/search_trips.html', context)


def trip_detail(request, pk):
    """View trip details"""
    trip = get_object_or_404(
        Trip.objects.select_related('route', 'vehicle', 'sacco', 'driver'),
        pk=pk
    )
    
    # Get occupied seats
    occupied_seats = SeatBooking.objects.filter(
        trip=trip,
        status__in=['held', 'booked']
    ).values_list('seat__seat_number', flat=True)
    
    # Get all seats for the vehicle
    seats = Seat.objects.filter(vehicle=trip.vehicle).order_by('row', 'column')
    
    context = {
        'trip': trip,
        'seats': seats,
        'occupied_seats': list(occupied_seats),
        'can_book': trip.is_bookable,
    }
    return render(request, 'core/trip_detail.html', context)


# ============================================
# Authentication
# ============================================

def register(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Send verification SMS
            # verification_code = generate_verification_code()
            # user.verification_code = verification_code
            # user.save()
            # send_sms(user.phone_number, f"Your verification code is: {verification_code}")
            
            login(request, user)
            messages.success(request, 'Registration successful! Welcome aboard.')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def user_login(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            
            if user:
                login(request, user)
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid credentials')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def user_logout(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


# ============================================
# Booking Process
# ============================================

@login_required
def create_booking(request, trip_id):
    """Create a new booking"""
    trip = get_object_or_404(Trip, pk=trip_id)
    
    if not trip.is_bookable:
        messages.error(request, 'This trip is no longer available for booking.')
        return redirect('search_trips')
    
    if request.method == 'POST':
        form = BookingForm(request.POST, trip=trip)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.customer = request.user
            booking.trip = trip
            booking.status = 'pending'
            
            # Calculate total fare
            booking.total_fare = trip.fare * booking.number_of_seats
            
            # Apply promotion if provided
            promo_code = form.cleaned_data.get('promotion_code')
            if promo_code:
                try:
                    promotion = Promotion.objects.get(code=promo_code)
                    if promotion.is_valid() and booking.total_fare >= promotion.min_booking_amount:
                        if promotion.discount_type == 'percentage':
                            discount = (booking.total_fare * promotion.discount_value) / 100
                            if promotion.max_discount:
                                discount = min(discount, promotion.max_discount)
                        else:
                            discount = promotion.discount_value
                        booking.total_fare -= discount
                        promotion.times_used += 1
                        promotion.save()
                except Promotion.DoesNotExist:
                    messages.warning(request, 'Invalid promotion code')
            
            # Set booking expiry (10 minutes to complete payment)
            booking.booking_expires_at = timezone.now() + timedelta(minutes=10)
            booking.save()
            
            # Hold selected seats
            selected_seats = request.POST.getlist('seats')
            for seat_id in selected_seats:
                seat = Seat.objects.get(pk=seat_id)
                SeatBooking.objects.create(
                    booking=booking,
                    trip=trip,
                    seat=seat,
                    status='held',
                    held_until=booking.booking_expires_at
                )
            
            # Update available seats
            trip.available_seats -= booking.number_of_seats
            trip.save()
            
            # Send booking confirmation SMS
            message = f"Booking confirmed! Reference: {booking.booking_reference}. Complete payment within 10 minutes."
            send_sms(booking.passenger_phone, message)
            
            messages.success(request, f'Booking created successfully! Reference: {booking.booking_reference}')
            return redirect('booking_payment', pk=booking.pk)
    else:
        form = BookingForm(trip=trip, initial={
            'passenger_name': request.user.get_full_name(),
            'passenger_phone': request.user.phone_number,
            'passenger_email': request.user.email,
        })
    
    context = {
        'form': form,
        'trip': trip,
    }
    return render(request, 'core/create_booking.html', context)


@login_required
def booking_payment(request, pk):
    """Process booking payment"""
    booking = get_object_or_404(Booking, pk=pk, customer=request.user)
    
    if booking.status != 'pending':
        messages.info(request, 'This booking has already been processed.')
        return redirect('booking_detail', pk=booking.pk)
    
    # Check if booking has expired
    if timezone.now() > booking.booking_expires_at:
        booking.status = 'cancelled'
        booking.save()
        # Release held seats
        booking.seat_bookings.update(status='available')
        booking.trip.available_seats += booking.number_of_seats
        booking.trip.save()
        messages.error(request, 'Your booking has expired. Please try again.')
        return redirect('search_trips')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        if payment_method == 'mpesa':
            phone = request.POST.get('phone_number')
            # Initiate M-Pesa STK Push
            result = initiate_mpesa_payment(booking, phone)
            
            if result.get('success'):
                Payment.objects.create(
                    transaction_id=result['transaction_id'],
                    booking=booking,
                    amount=booking.total_fare,
                    payment_method='mpesa',
                    status='processing',
                    phone_number=phone,
                    checkout_request_id=result.get('checkout_request_id')
                )
                messages.success(request, 'Payment request sent! Check your phone to complete payment.')
                return redirect('booking_detail', pk=booking.pk)
            else:
                messages.error(request, f'Payment initiation failed: {result.get("message")}')
        
        elif payment_method == 'cash':
            # For cash payment, mark as confirmed but pending verification
            Payment.objects.create(
                transaction_id=f"CASH-{booking.booking_reference}",
                booking=booking,
                amount=booking.total_fare,
                payment_method='cash',
                status='pending'
            )
            messages.info(request, 'Cash payment recorded. Please pay at the terminal.')
            return redirect('booking_detail', pk=booking.pk)
    
    context = {
        'booking': booking,
        'time_remaining': (booking.booking_expires_at - timezone.now()).total_seconds(),
    }
    return render(request, 'core/booking_payment.html', context)


@login_required
def booking_detail(request, pk):
    """View booking details"""
    booking = get_object_or_404(
        Booking.objects.select_related('trip__route', 'trip__vehicle', 'trip__sacco'),
        pk=pk
    )
    
    # Check if user owns this booking or is staff
    if booking.customer != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this booking.')
        return redirect('dashboard')
    
    payments = booking.payments.all()
    
    context = {
        'booking': booking,
        'payments': payments,
        'can_cancel': booking.can_cancel(),
    }
    return render(request, 'core/booking_detail.html', context)


@login_required
@require_POST
def cancel_booking(request, pk):
    """Cancel a booking"""
    booking = get_object_or_404(Booking, pk=pk, customer=request.user)
    
    if not booking.can_cancel():
        messages.error(request, 'This booking cannot be cancelled.')
        return redirect('booking_detail', pk=booking.pk)
    
    reason = request.POST.get('reason', '')
    booking.status = 'cancelled'
    booking.cancelled_at = timezone.now()
    booking.cancellation_reason = reason
    
    # Calculate refund (80% for cancellations more than 2 hours before)
    if booking.payments.filter(status='completed').exists():
        completed_payment = booking.payments.filter(status='completed').first()
        booking.refund_amount = booking.total_fare * 0.8
        
        Refund.objects.create(
            payment=completed_payment,
            booking=booking,
            amount=booking.refund_amount,
            reason=reason,
            processed_by=request.user,
            status='pending'
        )
    
    booking.save()
    
    # Release seats
    booking.seat_bookings.update(status='available')
    booking.trip.available_seats += booking.number_of_seats
    booking.trip.save()
    
    messages.success(request, 'Booking cancelled successfully. Refund will be processed within 24 hours.')
    return redirect('booking_detail', pk=booking.pk)


# ============================================
# User Dashboard
# ============================================

@login_required
def dashboard(request):
    """User dashboard"""
    user = request.user
    
    if user.role == 'customer':
        upcoming_bookings = Booking.objects.filter(
            customer=user,
            status__in=['confirmed', 'checked_in'],
            trip__departure_date__gte=timezone.now().date()
        ).select_related('trip__route', 'trip__vehicle')[:5]
        
        past_bookings = Booking.objects.filter(
            customer=user,
            status='completed'
        ).select_related('trip__route')[:5]
        
        context = {
            'upcoming_bookings': upcoming_bookings,
            'past_bookings': past_bookings,
        }
        return render(request, 'core/customer_dashboard.html', context)
    
    elif user.role == 'driver':
        driver = user.driver_profile
        today_trips = Trip.objects.filter(
            driver=driver,
            departure_date=timezone.now().date()
        ).select_related('route', 'vehicle')
        
        context = {
            'today_trips': today_trips,
            'driver': driver,
        }
        return render(request, 'core/driver_dashboard.html', context)
    
    elif user.role == 'sacco_admin':
        sacco = user.owned_saccos.first()
        if sacco:
            today_trips = Trip.objects.filter(
                sacco=sacco,
                departure_date=timezone.now().date()
            ).annotate(
                bookings_count=Count('bookings')
            )
            
            revenue_today = Booking.objects.filter(
                trip__sacco=sacco,
                trip__departure_date=timezone.now().date(),
                status='confirmed'
            ).aggregate(total=Sum('total_fare'))['total'] or 0
            
            context = {
                'sacco': sacco,
                'today_trips': today_trips,
                'revenue_today': revenue_today,
            }
            return render(request, 'core/sacco_dashboard.html', context)
    
    return render(request, 'core/dashboard.html')


@login_required
def my_bookings(request):
    """List user's bookings"""
    bookings = Booking.objects.filter(
        customer=request.user
    ).select_related('trip__route', 'trip__vehicle', 'trip__sacco').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    paginator = Paginator(bookings, 10)
    page = request.GET.get('page')
    bookings_page = paginator.get_page(page)
    
    context = {
        'bookings': bookings_page,
        'status_filter': status_filter,
    }
    return render(request, 'core/my_bookings.html', context)


@login_required
def profile(request):
    """User profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/profile.html', context)


# ============================================
# AJAX Views
# ============================================

def check_seat_availability(request):
    """Check seat availability (AJAX)"""
    trip_id = request.GET.get('trip_id')
    trip = get_object_or_404(Trip, pk=trip_id)
    
    occupied = SeatBooking.objects.filter(
        trip=trip,
        status__in=['held', 'booked']
    ).values_list('seat__seat_number', flat=True)
    
    return JsonResponse({
        'available_seats': trip.available_seats,
        'occupied_seats': list(occupied)
    })


def verify_promotion(request):
    """Verify promotion code (AJAX)"""
    code = request.GET.get('code')
    amount = float(request.GET.get('amount', 0))
    
    try:
        promotion = Promotion.objects.get(code=code)
        if promotion.is_valid() and amount >= promotion.min_booking_amount:
            if promotion.discount_type == 'percentage':
                discount = (amount * promotion.discount_value) / 100
                if promotion.max_discount:
                    discount = min(discount, promotion.max_discount)
            else:
                discount = promotion.discount_value
            
            return JsonResponse({
                'valid': True,
                'discount': float(discount),
                'final_amount': amount - discount,
                'message': f'{promotion.title} applied!'
            })
        else:
            return JsonResponse({
                'valid': False,
                'message': 'Promotion code is not valid or minimum amount not met.'
            })
    except Promotion.DoesNotExist:
        return JsonResponse({
            'valid': False,
            'message': 'Invalid promotion code.'
        })
