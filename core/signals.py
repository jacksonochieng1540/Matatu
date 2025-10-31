from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import F
from .models import *


@receiver(post_save, sender=Booking)
def handle_booking_confirmation(sender, instance, created, **kwargs):
    """Handle booking confirmation"""
    if not created and instance.status == 'confirmed':
        Notification.objects.create(
            user=instance.customer,
            type='booking',
            title='Booking Confirmed',
            message=f'Your booking {instance.booking_reference} has been confirmed!',
            link=f'/bookings/{instance.pk}/'
        )


@receiver(post_save, sender=Review)
def handle_new_review(sender, instance, created, **kwargs):
    if created:
        avg_rating = Review.objects.filter(
            sacco=instance.sacco,
            is_verified=True
        ).aggregate(Avg('overall_rating'))['overall_rating__avg']
        
        if avg_rating:
            instance.sacco.rating = round(avg_rating, 2)
            instance.sacco.total_reviews = F('total_reviews') + 1
            instance.sacco.save()
        
    
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
    if instance.status == 'boarding':
        bookings = instance.bookings.filter(status='confirmed')
        for booking in bookings:
            message = f"Your trip {instance.route.name} is now boarding at {booking.boarding_point.name}!"
            send_sms(booking.passenger_phone, message)


@receiver(pre_save, sender=Trip)
def calculate_trip_totals(sender, instance, **kwargs):
    if not instance.pk: 
        instance.total_seats = instance.vehicle.capacity
        instance.available_seats = instance.vehicle.capacity


@receiver(post_save, sender=Payment)
def handle_payment_completion(sender, instance, created, **kwargs):
    if not created and instance.status == 'completed':
        booking = instance.booking
        if booking.status != 'confirmed':
            booking.status = 'confirmed'
            booking.save()


