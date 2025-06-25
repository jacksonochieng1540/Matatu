from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Route, Matatu, Trip, Booking

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = '__all__'

class MatatuSerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)

    class Meta:
        model = Matatu
        fields = '__all__'

class TripSerializer(serializers.ModelSerializer):
    matatu = MatatuSerializer(read_only=True)
    matatu_id = serializers.PrimaryKeyRelatedField(
        queryset=Matatu.objects.all(), source='matatu', write_only=True
    )

    class Meta:
        model = Trip
        fields = ['id', 'matatu', 'matatu_id', 'date', 'departure_time']

class BookingSerializer(serializers.ModelSerializer):
    passenger = UserSerializer(read_only=True)
    trip = TripSerializer(read_only=True)
    trip_id = serializers.PrimaryKeyRelatedField(
        queryset=Trip.objects.all(), source='trip', write_only=True
    )

    class Meta:
        model = Booking
        fields = ['id', 'passenger', 'trip', 'trip_id', 'seat_number']
