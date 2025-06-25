from django.shortcuts import render,redirect,get_object_or_404

# Create your views here.
from rest_framework import viewsets,permissions
from django.db import IntegrityError
from django.http import HttpResponseBadRequest
from.models import Route,Trip,Matatu,Booking
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import (
    RouteSerializer,MatatuSerializer, TripSerializer, BookingSerializer
)
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import BookingForm,CustomUserCreationForm
from django.contrib.auth.decorators import login_required


class RouteViewsets(viewsets.ModelViewSet):
    queryset=Route.objects.all()
    serializer_class=RouteSerializer
    permission_classes=[permissions.IsAuthenticatedOrReadOnly]
    
class MatatuViewsets(viewsets.ModelViewSet):
    queryset=Matatu.objects.all()
    serializer_class=MatatuSerializer
    permission_classes=[permissions.IsAuthenticatedOrReadOnly]
    
class TripViewsets(viewsets.ModelViewSet):
    queryset=Trip.objects.all()
    serializer_class=TripSerializer
    permission_classes=[permissions.IsAuthenticatedOrReadOnly]
    
class BookingViewsets(viewsets.ModelViewSet):
    serializer_class=BookingSerializer
    permission_classes=[permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        return Booking.objects.filter(passengers=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(passengers=self.request.user)


def home(request):
    trips = Trip.objects.all()
    return render(request, 'home.html', {'trips': trips})


def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})



def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            messages.error(request, "Please enter both username and password.")
        else:
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password.")

    return render(request, 'login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
@login_required
def book_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.trip = trip
            booking.passenger = request.user
            booking.save()
            return redirect('home') 
    else:
        form = BookingForm()

    return render(request, 'booking.html', {'form': form, 'trip': trip})