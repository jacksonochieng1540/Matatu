from django.urls import path,include
from rest_framework.routers import DefaultRouter
from.import views
from. views import RouteViewsets,TripViewsets,BookingViewsets,MatatuViewsets


router=DefaultRouter()
router.register(r'routes',RouteViewsets,basename='routes')
router.register('matatus',MatatuViewsets,basename='matatus')
router.register('trips',TripViewsets,basename='trips')
router.register(r'bookings',BookingViewsets,basename='bookings')


urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('book/<int:trip_id>/', views.book_trip, name='book_trip'),
    path('',include(router.urls)),
]

