from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import *

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'phone_number', 'is_verified', 'created_at']
    list_filter = ['role', 'is_verified', 'is_active']
    search_fields = ['username', 'email', 'phone_number', 'first_name', 'last_name']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone_number', 'id_number', 'profile_picture', 
                      'date_of_birth', 'address', 'is_verified')
        }),
    )


@admin.register(SACCO)
class SACCOAdmin(admin.ModelAdmin):
    list_display = ['name', 'registration_number', 'owner', 'is_active', 'rating', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'registration_number', 'email']
    readonly_fields = ['rating', 'total_reviews']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('owner')


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['registration_number', 'sacco', 'vehicle_type', 'capacity', 'status']
    list_filter = ['vehicle_type', 'status', 'has_wifi', 'has_ac']
    search_fields = ['registration_number', 'make', 'model']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('sacco')


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ['user', 'sacco', 'license_number', 'is_available', 'rating', 'total_trips']
    list_filter = ['is_available', 'sacco']
    search_fields = ['license_number', 'psvb_badge', 'user__username']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'sacco')


@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = ['user', 'sacco', 'badge_number', 'is_available']
    list_filter = ['is_available', 'sacco']
    search_fields = ['badge_number', 'user__username']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'location_type', 'parent', 'is_active']
    list_filter = ['location_type', 'is_active']
    search_fields = ['name']


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['name', 'origin', 'destination', 'distance', 'base_fare', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'origin__name', 'destination__name']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('origin', 'destination')


@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    list_display = ['route', 'location', 'sequence', 'distance_from_origin', 'fare_from_origin']
    list_filter = ['route']
    search_fields = ['route__name', 'location__name']


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['route', 'vehicle', 'departure_date', 'departure_time', 'status', 
                    'available_seats', 'total_seats']
    list_filter = ['status', 'departure_date', 'is_express']
    search_fields = ['route__name', 'vehicle__registration_number']
    date_hierarchy = 'departure_date'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('route', 'vehicle', 'sacco', 'driver')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_reference', 'customer', 'trip', 'status', 'number_of_seats', 
                    'total_fare', 'created_at']
    list_filter = ['status', 'created_at', 'trip__departure_date']
    search_fields = ['booking_reference', 'customer__username', 'passenger_name', 'passenger_phone']
    readonly_fields = ['booking_reference', 'qr_code']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'trip__route', 'trip__vehicle')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'booking', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['payment_method', 'status', 'created_at']
    search_fields = ['transaction_id', 'mpesa_receipt', 'booking__booking_reference']
    readonly_fields = ['transaction_id']
    date_hierarchy = 'created_at'


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['booking', 'amount', 'status', 'processed_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['booking__booking_reference', 'transaction_id']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['customer', 'trip', 'overall_rating', 'is_verified', 'created_at']
    list_filter = ['overall_rating', 'is_verified', 'created_at']
    search_fields = ['customer__username', 'comment']
    readonly_fields = ['booking', 'customer', 'trip']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'title', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'discount_type', 'discount_value', 'is_active', 
                    'times_used', 'usage_limit']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code', 'title']


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'updated_at']
    search_fields = ['key', 'description']


# Customize admin site 
admin.site.site_header = "MatatuBook Administration"
admin.site.site_title = "MatatuBook Admin"
admin.site.index_title = "Welcome to MatatuBook Administration"


