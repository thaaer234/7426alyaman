from django.contrib import admin
from .models import Employee, Teacher, Vacation, EmployeePermission

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """
    نسخة آمنة لا تعتمد على حقول غير موجودة.
    إذا كانت لديك حقول مثل position/hire_date/salary لاحقًا، أضفها هنا.
    """
    list_display = ('full_name_display', 'username_display',)
    search_fields = ('user__first_name', 'user__last_name', 'user__username',)
    ordering = ('-id',)

    @admin.display(description='الاسم الكامل')
    def full_name_display(self, obj: Employee):
        if hasattr(obj, 'full_name') and obj.full_name:
            return obj.full_name
        u = getattr(obj, 'user', None)
        if u:
            return u.get_full_name() or u.get_username()
        return str(obj)

    @admin.display(description='اسم المستخدم')
    def username_display(self, obj: Employee):
        u = getattr(obj, 'user', None)
        return u.get_username() if u else ''


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'salary_type', 'hourly_rate', 'monthly_salary', 'hire_date')
    list_filter = ('salary_type', 'hire_date')
    search_fields = ('full_name', 'phone_number')
    ordering = ('-created_at',)


@admin.register(Vacation)
class VacationAdmin(admin.ModelAdmin):
    list_display = ('employee', 'vacation_type', 'status', 'start_date', 'end_date', 'is_replacement_secured')
    list_filter = ('vacation_type', 'status', 'is_replacement_secured', 'start_date', 'end_date')
    search_fields = ('employee__user__first_name', 'employee__user__last_name', 'employee__user__username')
    ordering = ('-created_at',)


@admin.register(EmployeePermission)
class EmployeePermissionAdmin(admin.ModelAdmin):
    list_display = ('employee', 'permission', 'is_granted', 'granted_by', 'granted_at')
    list_filter = ('permission', 'is_granted', 'granted_at')
    search_fields = ('employee__user__first_name', 'employee__user__last_name', 'employee__user__username')
    ordering = ('-granted_at',)
