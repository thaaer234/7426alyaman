from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('', views.student.as_view(), name='student_list'),
    path('<int:student_id>/profile/', views.StudentProfileView.as_view(), name='student_profile'),
    path('<int:student_id>/statement/', views.StudentStatementView.as_view(), name='student_statement'),
    path('student/<int:student_id>/statement/', views.student_statement, name='student_statement_legacy'),
    path('student/<int:student_id>/quick-receipt/', views.quick_receipt, name='quick_receipt'),
    path('student/', views.student.as_view(), name="student"),
    path('student_groups/', views.student_groups.as_view(), name="student_groups"),
    path('student_profile/<int:student_id>/', views.student_profile, name="student_profile_legacy"),
    path('stunum', views.stunum.as_view(), name="stu_num"),
    path('create/', views.CreateStudentView.as_view(), name="create_student"),
    path('update/<int:pk>/', views.UpdateStudentView.as_view(), name="update_student"),  
    path('delete/<int:pk>/', views.StudentDeleteView.as_view(), name="delete_student"),
    path('deactivate/<int:pk>/', views.DeactivateStudentView.as_view(), name="deactivate_student"),
    path('<int:student_id>/register_course/', views.register_course, name='register_course'),
    path('<int:student_id>/quick_receipt/', views.quick_receipt, name='quick_receipt'),
    path('<int:student_id>/withdraw/', views.withdraw_student, name='withdraw_student'),
]