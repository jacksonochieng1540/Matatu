from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.urls import reverse
from phonenumber_field.modelfields import PhoneNumberField
from mptt.models import MPTTModel, TreeForeignKey
import uuid


class User(AbstractUser):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('driver', 'Driver'),
        ('conductor', 'Conductor'),
        ('sacco_admin', 'SACCO Admin'),
        ('system_admin', 'System Admin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone_number = PhoneNumberField(unique=True)
    id_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
    
    def get_absolute_url(self):
        return reverse('profile', kwargs={'pk': self.pk})


class SACCO(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=50, unique=True)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='owned_saccos')
    logo = models.ImageField(upload_to='sacco_logos/', blank=True, null=True)
    description = models.TextField()
    phone_number = PhoneNumberField()
    email = models.EmailField()
    address = models.TextField()
    license_number = models.CharField(max_length=100)
    license_expiry = models.DateField()
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'SACCO'
        verbose_name_plural = 'SACCOs'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Vehicle(models.Model):
    VEHICLE_TYPE_CHOICES = [
        ('14_seater', '14 Seater'),
        ('25_seater', '25 Seater'),
        ('33_seater', '33 Seater'),
        ('51_seater', '51 Seater (Bus)'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sacco = models.ForeignKey(SACCO, on_delete=models.CASCADE, related_name='vehicles')
    registration_number = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES)
    capacity = models.IntegerField(validators=[MinValueValidator(1)])
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    color = models.CharField(max_length=50)
    insurance_number = models.CharField(max_length=100)
    insurance_expiry = models.DateField()
    ntsa_inspection_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    has_wifi = models.BooleanField(default=False)
    has_ac = models.BooleanField(default=False)
    has_charging_ports = models.BooleanField(default=False)
    has_entertainment = models.BooleanField(default=False)
    image = models.ImageField(upload_to='vehicles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['registration_number']
    
    def __str__(self):
        return f"{self.registration_number} - {self.get_vehicle_type_display()}"


class Driver(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    sacco = models.ForeignKey(SACCO, on_delete=models.CASCADE, related_name='drivers')
    license_number = models.CharField(max_length=50, unique=True)
    license_expiry = models.DateField()
    license_category = models.CharField(max_length=20)
    psvb_badge = models.CharField(max_length=50, unique=True)
    psvb_expiry = models.DateField()
    emergency_contact = PhoneNumberField()
    is_available = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_trips = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.license_number}"


class Conductor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='conductor_profile')
    sacco = models.ForeignKey(SACCO, on_delete=models.CASCADE, related_name='conductors')
    badge_number = models.CharField(max_length=50, unique=True)
    emergency_contact = PhoneNumberField()
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.badge_number}"


class Location(MPTTModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    location_type = models.CharField(max_length=20, choices=[
        ('county', 'County'),
        ('town', 'Town'),
        ('stage', 'Stage/Terminal'),
    ])
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class MPTTMeta:
        order_insertion_by = ['name']
    
    def __str__(self):
        return self.name


class Route(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    origin = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='routes_from')
    destination = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='routes_to')
    distance = models.DecimalField(max_digits=6, decimal_places=2, help_text='Distance in KM')
    estimated_duration = models.IntegerField(help_text='Duration in minutes')
    base_fare = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['origin', 'destination']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.origin.name} to {self.destination.name}"


class RouteStop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    sequence = models.IntegerField()
    distance_from_origin = models.DecimalField(max_digits=6, decimal_places=2)
    fare_from_origin = models.DecimalField(max_digits=8, decimal_places=2)
    estimated_time = models.IntegerField(help_text='Minutes from origin')
    
    class Meta:
        ordering = ['route', 'sequence']
        unique_together = ['route', 'sequence']
    
    def __str__(self):
        return f"{self.route.name} - Stop {self.sequence}: {self.location.name}"


class Schedule(models.Model):
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sacco = models.ForeignKey(SACCO, on_delete=models.CASCADE, related_name='schedules')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='schedules')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='schedules')
    days_of_week = models.JSONField(help_text='List of active days')
    departure_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['departure_time']
    
    def __str__(self):
        return f"{self.route.name} - {self.departure_time}"


class Trip(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('boarding', 'Boarding'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sacco = models.ForeignKey(SACCO, on_delete=models.CASCADE, related_name='trips')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='trips')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='trips')
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name='trips')
    conductor = models.ForeignKey(Conductor, on_delete=models.PROTECT, related_name='trips', blank=True, null=True)
    departure_date = models.DateField()
    departure_time = models.TimeField()
    arrival_time = models.TimeField(blank=True, null=True)
    actual_departure = models.DateTimeField(blank=True, null=True)
    actual_arrival = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    fare = models.DecimalField(max_digits=8, decimal_places=2)
    available_seats = models.IntegerField()
    total_seats = models.IntegerField()
    is_express = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-departure_date', '-departure_time']
        indexes = [
            models.Index(fields=['departure_date', 'status']),
            models.Index(fields=['route', 'departure_date']),
        ]
    
    def __str__(self):
        return f"{self.route.name} - {self.departure_date} {self.departure_time}"
    
    @property
    def is_bookable(self):
        """Check if trip can still be booked"""
        now = timezone.now()
        departure_datetime = timezone.make_aware(
            timezone.datetime.combine(self.departure_date, self.departure_time)
        )
        time_diff = (departure_datetime - now).total_seconds() / 60
        return (
            self.status == 'scheduled' and
            self.available_seats > 0 and
            time_diff >= 30  
        )
class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_reference = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='bookings')
    trip = models.ForeignKey(Trip, on_delete=models.PROTECT, related_name='bookings')
    number_of_seats = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)])
    boarding_point = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='boarding_bookings')
    dropping_point = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='dropping_bookings')
    total_fare = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, blank=True)
    passenger_name = models.CharField(max_length=200)
    passenger_phone = PhoneNumberField()
    passenger_email = models.EmailField(blank=True)
    special_requests = models.TextField(blank=True)
    seat_numbers = models.JSONField(blank=True, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    checked_in_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    booking_expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking_reference']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['trip', 'status']),
        ]
    
    def __str__(self):
        return f"{self.booking_reference} - {self.passenger_name}"
    
    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = self.generate_reference()
        super().save(*args, **kwargs)
    
    def generate_reference(self):
        import random
        import string
        while True:
            ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            if not Booking.objects.filter(booking_reference=ref).exists():
                return ref
    
    def can_cancel(self):
        """Check if booking can be cancelled"""
        if self.status not in ['confirmed', 'pending']:
            return False
        now = timezone.now()
        departure = timezone.make_aware(
            timezone.datetime.combine(self.trip.departure_date, self.trip.departure_time)
        )
        hours_remaining = (departure - now).total_seconds() / 3600
        return hours_remaining >= 2  


class Seat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)
    row = models.IntegerField()
    column = models.CharField(max_length=5)
    is_window = models.BooleanField(default=False)
    is_aisle = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['vehicle', 'seat_number']
        ordering = ['row', 'column']
    
    def __str__(self):
        return f"{self.vehicle.registration_number} - Seat {self.seat_number}"


class SeatBooking(models.Model):
    STATUS_CHOICES = [
        ('held', 'Held'),
        ('booked', 'Booked'),
        ('available', 'Available'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='seat_bookings', blank=True, null=True)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='seat_bookings')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='held')
    held_until = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['trip', 'seat']
    
    def __str__(self):
        return f"{self.trip} - Seat {self.seat.seat_number}"

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Credit/Debit Card'),
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_id = models.CharField(max_length=100, unique=True)
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    phone_number = PhoneNumberField(blank=True, null=True)
    mpesa_receipt = models.CharField(max_length=100, blank=True)
    mpesa_transaction_id = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(max_length=100, blank=True)
    response_code = models.CharField(max_length=10, blank=True)
    response_message = models.TextField(blank=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['mpesa_receipt']),
        ]
    
    def __str__(self):
        return f"{self.transaction_id} - {self.amount}"


class Refund(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds')
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='processed_refunds')
    processed_at = models.DateTimeField(blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund for {self.booking.booking_reference} - {self.amount}"


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='reviews')
    sacco = models.ForeignKey(SACCO, on_delete=models.CASCADE, related_name='reviews')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='reviews', blank=True, null=True)
    overall_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    punctuality_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    cleanliness_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comfort_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    service_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    response = models.TextField(blank=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='review_responses')
    responded_at = models.DateTimeField(blank=True, null=True)
    is_verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review by {self.customer.get_full_name()} - {self.overall_rating} stars"


class Notification(models.Model):
    """User notifications"""
    TYPE_CHOICES = [
        ('booking', 'Booking'),
        ('payment', 'Payment'),
        ('trip', 'Trip'),
        ('promotion', 'Promotion'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"


class SMSLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = PhoneNumberField()
    message = models.TextField()
    status = models.CharField(max_length=20)
    response = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-sent_at']


class EmailLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20)
    error = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-sent_at']


class SystemSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.key


class Promotion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    discount_type = models.CharField(max_length=20, choices=[
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ])
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_booking_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    usage_limit = models.IntegerField(blank=True, null=True)
    times_used = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.title}"
    
    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_until and
            (self.usage_limit is None or self.times_used < self.usage_limit)
        )
