from django.urls import path
from . import views

app_name = 'grade'

urlpatterns = [
    path('', views.grades_dashboard, name='dashboard'),
    path('<int:classroom_id>/subjects/', views.select_subject, name='select_subject'),  
    path('<int:classroom_id>/subjects/<int:subject_id>/', views.view_grades, name='view_grades'),
    path('<int:classroom_id>/subjects/<int:subject_id>/edit/', views.edit_grades, name='edit_grades'),
    path('<int:classroom_id>/subjects/<int:subject_id>/export-excel/', views.export_grades_excel, name='export_grades_excel'),
    path('classroom/<int:classroom_id>/subject/<int:subject_id>/custom-print/', views.custom_print_grades, name='custom_print_grades'),
]