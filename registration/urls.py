from django.contrib.auth.views import LoginView,LogoutView
from django.urls import path
from .views import registerview


urlpatterns = [
    
    path('signup/',registerview.as_view(),name='signup'),
]
