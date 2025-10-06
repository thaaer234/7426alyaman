from django.shortcuts import render
from django.views import View

class EmployeePermissionRequiredMixin(View):
    required_permission: str | None = None

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        perms = getattr(request, "employee_permissions", set())
        ok = user.is_authenticated and (
            user.is_superuser or
            (self.required_permission and self.required_permission in perms) or
            ("__ALL__" in perms)
        )
        if ok:
            return super().dispatch(request, *args, **kwargs)
        return render(request, "503.html", status=503)
