from django.db import models
from django.utils import timezone

class ActiveManager(models.Manager):
    """Manager for active objects only"""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class BookableTripsManager(models.Manager):
    """Manager for bookable trips"""
    def get_queryset(self):
        now = timezone.now()
        return super().get_queryset().filter(
            status='scheduled',
            available_seats__gt=0,
            departure_date__gte=now.date()
        )


class UpcomingTripsManager(models.Manager):
    """Manager for upcoming trips"""
    def get_queryset(self):
        now = timezone.now()
        return super().get_queryset().filter(
            status__in=['scheduled', 'boarding'],
            departure_date__gte=now.date()
        )