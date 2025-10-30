
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, HTML
from .models import *
from datetime import date, timedelta


class UserRegistrationForm(forms.ModelForm):
    """User registration form"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        label='Password'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}),
        label='Confirm Password'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254712345678'}),
        }
    
    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise ValidationError('Passwords do not match.')
        return password_confirm
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if User.objects.filter(phone_number=phone).exists():
            raise ValidationError('This phone number is already registered.')
        return phone


class LoginForm(forms.Form):
    """User login form"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username or Phone'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


class UserProfileForm(forms.ModelForm):
    """User profile update form"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'address', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

class TripSearchForm(forms.Form):
    """Trip search form"""
    origin = forms.ModelChoiceField(
        queryset=Location.objects.filter(location_type='stage', is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='From'
    )
    destination = forms.ModelChoiceField(
        queryset=Location.objects.filter(location_type='stage', is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='To'
    )
    travel_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Travel Date',
        initial=date.today
    )
    passengers = forms.IntegerField(
        min_value=1,
        max_value=6,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Passengers'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Row(
                Column('origin', css_class='col-md-3'),
                Column('destination', css_class='col-md-3'),
                Column('travel_date', css_class='col-md-3'),
                Column('passengers', css_class='col-md-2'),
                Column(
                    Submit('search', 'Search Trips', css_class='btn btn-primary w-100'),
                    css_class='col-md-1'
                ),
            )
        )
    
    def clean_travel_date(self):
        travel_date = self.cleaned_data.get('travel_date')
        if travel_date < date.today():
            raise ValidationError('Travel date cannot be in the past.')
        if travel_date > date.today() + timedelta(days=90):
            raise ValidationError('You can only book up to 90 days in advance.')
        return travel_date
    
    def clean(self):
        cleaned_data = super().clean()
        origin = cleaned_data.get('origin')
        destination = cleaned_data.get('destination')
        
        if origin and destination and origin == destination:
            raise ValidationError('Origin and destination cannot be the same.')
        
        return cleaned_data


class BookingForm(forms.ModelForm):
    """Booking creation form"""
    promotion_code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter promo code (optional)'}),
        label='Promotion Code'
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='I accept the terms and conditions'
    )
    
    class Meta:
        model = Booking
        fields = [
            'number_of_seats', 'boarding_point', 'dropping_point',
            'passenger_name', 'passenger_phone', 'passenger_email', 'special_requests'
        ]
        widgets = {
            'number_of_seats': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'boarding_point': forms.Select(attrs={'class': 'form-select'}),
            'dropping_point': forms.Select(attrs={'class': 'form-select'}),
            'passenger_name': forms.TextInput(attrs={'class': 'form-control'}),
            'passenger_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'passenger_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'special_requests': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.trip = kwargs.pop('trip', None)
        super().__init__(*args, **kwargs)
        
        if self.trip:
            # Set boarding and dropping point choices based on route
            route_locations = [self.trip.route.origin]
            stops = self.trip.route.stops.all().order_by('sequence')
            for stop in stops:
                route_locations.append(stop.location)
            route_locations.append(self.trip.route.destination)
            
            self.fields['boarding_point'].queryset = Location.objects.filter(id__in=[loc.id for loc in route_locations])
            self.fields['dropping_point'].queryset = Location.objects.filter(id__in=[loc.id for loc in route_locations])
    
    def clean_number_of_seats(self):
        seats = self.cleaned_data.get('number_of_seats')
        if self.trip and seats > self.trip.available_seats:
            raise ValidationError(f'Only {self.trip.available_seats} seats available.')
        return seats


class ReviewForm(forms.ModelForm):
    """Review submission form"""
    class Meta:
        model = Review
        fields = [
            'overall_rating', 'punctuality_rating', 'cleanliness_rating',
            'comfort_rating', 'service_rating', 'comment'
        ]
        widgets = {
            'overall_rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'punctuality_rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'cleanliness_rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'comfort_rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'service_rating': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }



class SACCOForm(forms.ModelForm):
    """SACCO registration/update form"""
    class Meta:
        model = SACCO
        fields = [
            'name', 'registration_number', 'logo', 'description',
            'phone_number', 'email', 'address', 'license_number', 'license_expiry'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'license_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class VehicleForm(forms.ModelForm):
    """Vehicle registration/update form"""
    class Meta:
        model = Vehicle
        fields = [
            'registration_number', 'vehicle_type', 'capacity', 'make', 'model',
            'year', 'color', 'insurance_number', 'insurance_expiry',
            'ntsa_inspection_date', 'has_wifi', 'has_ac', 'has_charging_ports',
            'has_entertainment', 'image', 'status'
        ]
        widgets = {
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-select'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'make': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'insurance_number': forms.TextInput(attrs={'class': 'form-control'}),
            'insurance_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'ntsa_inspection_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'has_wifi': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_ac': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_charging_ports': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_entertainment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class TripForm(forms.ModelForm):
    """Trip creation/update form"""
    class Meta:
        model = Trip
        fields = [
            'route', 'vehicle', 'driver', 'conductor', 'departure_date',
            'departure_time', 'fare', 'is_express', 'notes'
        ]
        widgets = {
            'route': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'driver': forms.Select(attrs={'class': 'form-select'}),
            'conductor': forms.Select(attrs={'class': 'form-select'}),
            'departure_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'departure_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'fare': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_express': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        sacco = kwargs.pop('sacco', None)
        super().__init__(*args, **kwargs)
        
        if sacco:
            self.fields['vehicle'].queryset = Vehicle.objects.filter(sacco=sacco, status='active')
            self.fields['driver'].queryset = Driver.objects.filter(sacco=sacco, is_available=True)
            self.fields['conductor'].queryset = Conductor.objects.filter(sacco=sacco, is_available=True)


class RouteForm(forms.ModelForm):
    """Route creation/update form"""
    class Meta:
        model = Route
        fields = ['name', 'origin', 'destination', 'distance', 'estimated_duration', 'base_fare', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'origin': forms.Select(attrs={'class': 'form-select'}),
            'destination': forms.Select(attrs={'class': 'form-select'}),
            'distance': forms.NumberInput(attrs={'class': 'form-control'}),
            'estimated_duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'base_fare': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PromotionForm(forms.ModelForm):
    """Promotion creation/update form"""
    class Meta:
        model = Promotion
        fields = [
            'code', 'title', 'description', 'discount_type', 'discount_value',
            'min_booking_amount', 'max_discount', 'usage_limit', 'valid_from', 'valid_until'
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_booking_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_discount': forms.NumberInput(attrs={'class': 'form-control'}),
            'usage_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'valid_until': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }