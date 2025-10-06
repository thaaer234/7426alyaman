from django.utils.deprecation import MiddlewareMixin

class EmployeePermissionsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        perms = set()
        user = request.user
        if user.is_authenticated:
            if user.is_superuser:
                # سوبر يوزر يتجاوز كل شيء
                request.employee_permissions = {"__ALL__"}
                return

            # إذا للمستخدم Employee مربوط
            employee = getattr(user, "employee_profile", None)
            if employee:
                perms = set(employee.permissions.filter(is_granted=True)
                            .values_list("permission", flat=True))
        request.employee_permissions = perms
