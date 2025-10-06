from django.urls import path
from . import views

app_name = "classroom"

urlpatterns = [
        
        path('classroom/', views.ClassroomListView.as_view(), name="classroom"),
        path('create_classroom/', views.CreateClassroomView.as_view(), name="create_classroom"),
        path('assign-students/<int:classroom_id>/', views.AssignStudentsView.as_view(), name='assign_students'),
        path('assign-students/<int:classroom_id>/remove/<int:student_id>/', views.UnassignStudentView.as_view(), name='unassign_student'),
        path('classroom/<int:classroom_id>/students/', views.ClassroomStudentsView.as_view(), name='classroom_students'),
        path('classroom/<int:classroom_id>/delete/', views.DeleteClassroomView.as_view(), name='delete_classroom'),
        path('classroom/<int:classroom_id>/subjects/', views.ClassroomSubjectListView.as_view(), name='classroom_subject_list'),
        path('classroom/<int:classroom_id>/subjects/add/', views.ClassroomSubjectCreateView.as_view(), name='classroom_subject_create'),
        path('classroom/<int:classroom_id>/students/export/', views.export_classroom_students_to_excel, name='export_classroom_students'),

]