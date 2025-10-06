from django.contrib import admin
from django.urls import path
from . import views

app_name = "pages"


urlpatterns = [
    path('index',views.IndexView.as_view() , name="index"),
    path('',views.welcome.as_view() , name="welcome"),
]