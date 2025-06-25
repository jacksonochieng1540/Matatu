from django.contrib import admin

# Register your models here.
from.models import Booking,Trip,Matatu,Route
admin.site.register(Booking)
admin.site.register(Route)
admin.site.register(Trip)
admin.site.register(Matatu)