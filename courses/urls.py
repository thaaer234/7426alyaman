from django.contrib import admin
from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
        
        path('courses/',views.courses.as_view() , name="courses"),
        path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
        path('subjects/add/', views.SubjectCreateView.as_view(), name='subject_create'),
        path('subjects/<int:pk>/edit/', views.SubjectUpdateView.as_view(), name='subject_update'),
        path('subjects/<int:pk>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),

]