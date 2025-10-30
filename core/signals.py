from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import F
from .models import *


@receiver(post_save, sender=Booking)
def handle_booking_confirmation(sender, instance, created, **kwargs):
    """Handle booking confirmation"""
    if not created and instance.status == 'confirmed':
        # Send confirmation notification
        Notification.objects.create(
            user=instance.customer,
            type='booking',
            title='Booking Confirmed',
            message=f'Your booking {instance.booking_reference} has been confirmed!',
            link=f'/bookings/{instance.pk}/'
        )


@receiver(post_save, sender=Review)
def handle_new_review(sender, instance, created, **kwargs):
    """Handle new review submission"""
    if created:
        # Update SACCO rating
        avg_rating = Review.objects.filter(
            sacco=instance.sacco,
            is_verified=True
        ).aggregate(Avg('overall_rating'))['overall_rating__avg']
        
        if avg_rating:
            instance.sacco.rating = round(avg_rating, 2)
            instance.sacco.total_reviews = F('total_reviews') + 1
            instance.sacco.save()
        
        # Update driver rating
        if instance.driver:
            driver_avg = Review.objects.filter(
                driver=instance.driver,
                is_verified=True
            ).aggregate(Avg('overall_rating'))['overall_rating__avg']
            
            if driver_avg:
                instance.driver.rating = round(driver_avg, 2)
                instance.driver.save()


@receiver(post_save, sender=Trip)
def handle_trip_status_change(sender, instance, **kwargs):
    """Handle trip status changes"""
    if instance.status == 'boarding':
        # Notify booked customers
        bookings = instance.bookings.filter(status='confirmed')
        for booking in bookings:
            message = f"Your trip {instance.route.name} is now boarding at {booking.boarding_point.name}!"
            send_sms(booking.passenger_phone, message)


@receiver(pre_save, sender=Trip)
def calculate_trip_totals(sender, instance, **kwargs):
    """Calculate total and available seats"""
    if not instance.pk:  # New trip
        instance.total_seats = instance.vehicle.capacity
        instance.available_seats = instance.vehicle.capacity


@receiver(post_save, sender=Payment)
def handle_payment_completion(sender, instance, created, **kwargs):
    """Handle payment completion"""
    if not created and instance.status == 'completed':
        booking = instance.booking
        if booking.status != 'confirmed':
            booking.status = 'confirmed'
            booking.save()


# ============================================
# config/celery.py
# ============================================

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('matatu_booking')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    'release-expired-bookings': {
        'task': 'core.tasks.release_expired_bookings',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'send-trip-reminders': {
        'task': 'core.tasks.send_trip_reminders',
        'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
    },
    'check-pending-payments': {
        'task': 'core.tasks.check_pending_payments',
        'schedule': crontab(minute='*/2'),  # Every 2 minutes
    },
    'update-sacco-ratings': {
        'task': 'core.tasks.update_sacco_ratings',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'mark-completed-trips': {
        'task': 'core.tasks.mark_completed_trips',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'send-no-show-notifications': {
        'task': 'core.tasks.send_no_show_notifications',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'generate-daily-reports': {
        'task': 'core.tasks.generate_daily_reports',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
    },
    'cleanup-old-notifications': {
        'task': 'core.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Weekly on Sunday
    },
    'check-license-expiries': {
        'task': 'core.tasks.check_license_expiries',
        'schedule': crontab(hour=9, minute=0),  
    },
}

