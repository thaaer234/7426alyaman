from django.contrib import admin
from django.urls import path
from . import views

app_name = "employ"

urlpatterns = [
    path('teachers/',views.teachers.as_view() , name="teachers"),
    path('delete/<int:pk>/', views.TeacherDeleteView.as_view(), name="delete_teacher"),
    path('teacher/<int:pk>/', views.TeacherProfileView.as_view(), name='teacher_profile'),
    path('employee/<int:pk>/', views.EmployeeProfileView.as_view(), name='employee_profile'),
    path('employee/<int:pk>/pay-salary/', views.PayEmployeeSalaryView.as_view(), name='pay_employee_salary'),
    path('employee/<int:pk>/permissions/', views.EmployeePermissionsView.as_view(), name='employee_permissions'),
    path('employee/<int:pk>/permissions/', views.EmployeePermissionsView.as_view(), name='employee_permissions'),
    path('hr/',views.hr.as_view() , name="hr"),
    path('create/', views.CreateTeacherView.as_view(), name="create"),
    path('delete-employee/<int:pk>/', views.EmployeeDeleteView.as_view(), name='employee_delete'),
    path('register/', views.EmployeeCreateView.as_view(), name='employee_register'),
    path('update/', views.select_employee, name='select_employee'),
    path('update/<int:pk>/', views.EmployeeUpdateView.as_view(), name='employee_update'),
    path('vacations/', views.VacationListView.as_view(), name='vacation_list'),
    path('vacations/create/', views.VacationCreateView.as_view(), name='vacation_create'),
    path('vacations/update/<int:pk>/', views.VacationUpdateView.as_view(), name='vacation_update'),
    path('teacher/<int:pk>/pay-salary/', views.PayTeacherSalaryView.as_view(), name='pay_teacher_salary'),
    path('teacher/<int:pk>/create-accrual/', views.CreateTeacherAccrualView.as_view(), name='create_teacher_accrual'),
    path('salary-management/', views.SalaryManagementView.as_view(), name='salary_management'),
    path('teacher/<int:teacher_id>/advance/create/', views.TeacherAdvanceCreateView.as_view(), name='teacher_advance_create'),
    path('teacher/<int:teacher_id>/advances/', views.TeacherAdvanceListView.as_view(), name='teacher_advance_list'),
    path('employee/advance/create/', views.EmployeeAdvanceCreateView.as_view(), name='employee_advance_create'),
    path('employee/advance/list/', views.EmployeeAdvanceListView.as_view(), name='employee_advance_list'),
    path("employee/<int:pk>/permissions/", views.EmployeePermissionsView.as_view(), name="employee_permissions"),
    path("denied/", views.no_permission, name="no_permission"),
    
    # Employee Dashboard
    path('dashboard/', views.EmployeeDashboardView.as_view(), name='employee_dashboard'),
]