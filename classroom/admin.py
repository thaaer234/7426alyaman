from django.contrib import admin
from .models import Classroom, Classroomenrollment, ClassroomSubject


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ['name', 'class_type', 'branches']
    list_filter = ['class_type', 'branches']
    search_fields = ['name']


@admin.register(Classroomenrollment)
class ClassroomenrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'classroom', 'enrolled_at']
    list_filter = ['classroom', 'enrolled_at']
    search_fields = ['student__full_name', 'classroom__name']


@admin.register(ClassroomSubject)
class ClassroomSubjectAdmin(admin.ModelAdmin):
    list_display = ['classroom', 'subject']
    list_filter = ['classroom', 'subject']