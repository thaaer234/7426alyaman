# decorators.py
from django.http import HttpResponse
from functools import wraps

def emp_permission_required(code):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_authenticated and (
                request.user.is_superuser or
                getattr(request.user, 'employee_profile', None) and
                request.user.employee_profile.permissions.filter(permission=code, is_granted=True).exists()
            ):
                return view_func(request, *args, **kwargs)
            return HttpResponse("Service Unavailable", status=503)
        return _wrapped
    return decorator
