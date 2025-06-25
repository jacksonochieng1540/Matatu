from django.db import models

# Create your models here.
from django.contrib.auth.models import User

class Route(models.Model):
    origin=models.CharField(max_length=100)
    destination=models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.origin}➡️{self.destination}"
    
    
class Matatu(models.Model):
    router=models.ForeignKey(Route,on_delete=models.CASCADE)
    plate_number=models.CharField(max_length=10)
    capacity=models.IntegerField()
    
    def __str__(self):
        return self.plate_number
    
class Trip(models.Model):
    matatu=models.ForeignKey(Matatu,on_delete=models.CASCADE)
    date=models.DateField()
    departure_time=models.DateTimeField(auto_now_add=True)
    route=models.ForeignKey(Route,on_delete=models.CASCADE,null=True,blank=True)
    
    def __str__(self):
        return f"{self.matatu} on {self.date} at {self.departure_time}"
    
class Booking(models.Model):
    trip=models.ForeignKey(Trip,on_delete=models.CASCADE)
    passenger=models.ForeignKey(User,on_delete=models.CASCADE)
    seat_number=models.IntegerField()
    
    class Meta:
        unique_together=['trip','seat_number']
    
    def __str__(self):
        return f"{self.passenger.username} seats on  {self.seat_number}"
    