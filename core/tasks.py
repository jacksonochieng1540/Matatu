from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Count
from .models import *
from .utils import (
    send_sms, send_email_notification, send_trip_reminder,
    query_mpesa_transaction
)
import logging

logger = logging.getLogger(__name__)


@shared_task
def release_expired_bookings():
    """Release seats from expired pending bookings"""
    try:
        now = timezone.now()
        expired_bookings = Booking.objects.filter(
            status='pending',
            booking_expires_at__lt=now
        )
        
        for booking in expired_bookings:
            # Cancel booking
            booking.status = 'cancelled'
            booking.cancelled_at = now
            booking.cancellation_reason = 'Payment timeout'
            booking.save()
            
            # Release seats
            booking.seat_bookings.update(status='available')
            
            # Update trip available seats
            trip = booking.trip
            trip.available_seats += booking.number_of_seats
            trip.save()
            
            # Notify customer
            message = f"Your booking {booking.booking_reference} has expired. Please book again."
            send_sms(booking.passenger_phone, message)
        
        logger.info(f"Released {expired_bookings.count()} expired bookings")
        return f"Released {expired_bookings.count()} bookings"
    
    except Exception as e:
        logger.error(f"Error releasing expired bookings: {str(e)}")
        return str(e)


@shared_task
def send_trip_reminders():
    """Send trip reminders 24 hours before departure"""
    try:
        tomorrow = timezone.now().date() + timedelta(days=1)
        
        bookings = Booking.objects.filter(
            status='confirmed',
            trip__departure_date=tomorrow
        ).select_related('trip', 'customer')
        
        for booking in bookings:
            send_trip_reminder(booking)
        
        logger.info(f"Sent reminders for {bookings.count()} bookings")
        return f"Sent {bookings.count()} reminders"
    
    except Exception as e:
        logger.error(f"Error sending trip reminders: {str(e)}")
        return str(e)


@shared_task
def check_pending_payments():
    """Check status of pending M-Pesa payments"""
    try:
        pending_payments = Payment.objects.filter(
            status='processing',
            created_at__gte=timezone.now() - timedelta(minutes=10)
        ).exclude(checkout_request_id='')
        
        for payment in pending_payments:
            result = query_mpesa_transaction(payment.checkout_request_id)
            if result and result.get('ResultCode') == '0':
                # Payment successful
                payment.status = 'completed'
                payment.paid_at = timezone.now()
                payment.save()
                
                # Update booking
                booking = payment.booking
                booking.status = 'confirmed'
                booking.save()
                booking.seat_bookings.update(status='booked')
        
        logger.info(f"Checked {pending_payments.count()} pending payments")
        return f"Checked {pending_payments.count()} payments"
    
    except Exception as e:
        logger.error(f"Error checking pending payments: {str(e)}")
        return str(e)


@shared_task
def update_sacco_ratings():
    """Update SACCO ratings based on reviews"""
    try:
        saccos = SACCO.objects.all()
        
        for sacco in saccos:
            reviews = Review.objects.filter(sacco=sacco, is_verified=True)
            
            if reviews.exists():
                avg_rating = reviews.aggregate(Avg('overall_rating'))['overall_rating__avg']
                sacco.rating = round(avg_rating, 2)
                sacco.total_reviews = reviews.count()
                sacco.save()
        
        logger.info(f"Updated ratings for {saccos.count()} SACCOs")
        return f"Updated {saccos.count()} SACCO ratings"
    
    except Exception as e:
        logger.error(f"Error updating SACCO ratings: {str(e)}")
        return str(e)


@shared_task
def update_driver_ratings():
    """Update driver ratings based on reviews"""
    try:
        drivers = Driver.objects.all()
        
        for driver in drivers:
            reviews = Review.objects.filter(driver=driver, is_verified=True)
            
            if reviews.exists():
                avg_rating = reviews.aggregate(Avg('overall_rating'))['overall_rating__avg']
                driver.rating = round(avg_rating, 2)
                driver.save()
        
        logger.info(f"Updated ratings for {drivers.count()} drivers")
        return f"Updated {drivers.count()} driver ratings"
    
    except Exception as e:
        logger.error(f"Error updating driver ratings: {str(e)}")
        return str(e)


@shared_task
def mark_completed_trips():
    """Mark trips as completed after arrival time"""
    try:
        now = timezone.now()
        
        # Find trips that should be completed
        trips = Trip.objects.filter(
            status='in_transit',
            departure_date__lt=now.date()
        )
        
        for trip in trips:
            trip.status = 'completed'
            trip.actual_arrival = now
            trip.save()
            
            # Update related bookings
            trip.bookings.filter(status='checked_in').update(status='completed')
        
        logger.info(f"Marked {trips.count()} trips as completed")
        return f"Completed {trips.count()} trips"
    
    except Exception as e:
        logger.error(f"Error marking completed trips: {str(e)}")
        return str(e)


@shared_task
def send_no_show_notifications():
    """Mark bookings as no-show if customer didn't check in"""
    try:
        now = timezone.now()
        cutoff_time = now - timedelta(hours=1)
        
        # Find bookings where trip departed over 1 hour ago but not checked in
        bookings = Booking.objects.filter(
            status='confirmed',
            trip__status__in=['in_transit', 'completed'],
            trip__actual_departure__lt=cutoff_time,
            checked_in_at__isnull=True
        )
        
        for booking in bookings:
            booking.status = 'no_show'
            booking.save()
            
            # Could implement penalty or refund policy here
        
        logger.info(f"Marked {bookings.count()} bookings as no-show")
        return f"Marked {bookings.count()} as no-show"
    
    except Exception as e:
        logger.error(f"Error processing no-shows: {str(e)}")
        return str(e)


@shared_task
def generate_daily_reports():
    """Generate daily reports for SACCOs"""
    try:
        yesterday = timezone.now().date() - timedelta(days=1)
        
        for sacco in SACCO.objects.filter(is_active=True):
            # Calculate stats
            trips = Trip.objects.filter(sacco=sacco, departure_date=yesterday)
            bookings = Booking.objects.filter(
                trip__sacco=sacco,
                trip__departure_date=yesterday,
                status__in=['confirmed', 'completed']
            )
            
            total_revenue = sum(b.total_fare for b in bookings)
            total_bookings = bookings.count()
            total_passengers = sum(b.number_of_seats for b in bookings)
            
            # Send report via email to SACCO admin
            context = {
                'sacco': sacco,
                'date': yesterday,
                'total_trips': trips.count(),
                'total_bookings': total_bookings,
                'total_passengers': total_passengers,
                'total_revenue': total_revenue,
            }
            
            send_email_notification(
                subject=f'Daily Report - {yesterday}',
                recipient=sacco.email,
                template_name='emails/daily_report.html',
                context=context
            )
        
        logger.info("Generated daily reports for all SACCOs")
        return "Daily reports generated"
    
    except Exception as e:
        logger.error(f"Error generating daily reports: {str(e)}")
        return str(e)


@shared_task
def cleanup_old_notifications():
    """Delete old read notifications"""
    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted = Notification.objects.filter(
            is_read=True,
            created_at__lt=cutoff_date
        ).delete()
        
        logger.info(f"Deleted {deleted[0]} old notifications")
        return f"Deleted {deleted[0]} notifications"
    
    except Exception as e:
        logger.error(f"Error cleaning up notifications: {str(e)}")
        return str(e)


@shared_task
def check_license_expiries():
    """Check for expiring licenses and send notifications"""
    try:
        warning_date = timezone.now().date() + timedelta(days=30)
        
        # Check driver licenses
        drivers = Driver.objects.filter(
            license_expiry__lte=warning_date,
            license_expiry__gte=timezone.now().date()
        )
        
        for driver in drivers:
            message = f"Your license expires on {driver.license_expiry}. Please renew it soon."
            send_sms(driver.user.phone_number, message)
        
        # Check vehicle insurance
        vehicles = Vehicle.objects.filter(
            insurance_expiry__lte=warning_date,
            insurance_expiry__gte=timezone.now().date()
        )
        
        for vehicle in vehicles:
            message = f"Insurance for {vehicle.registration_number} expires on {vehicle.insurance_expiry}."
            send_sms(vehicle.sacco.phone_number, message)
        
        logger.info(f"Checked {drivers.count()} driver licenses and {vehicles.count()} vehicle insurances")
        return "License checks completed"
    
    except Exception as e:
        logger.error(f"Error checking license expiries: {str(e)}")
        return str(e)

