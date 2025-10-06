def employee_permissions(request):
    return {
        "emp_perms": getattr(request, "employee_permissions", set()),
        "employee_obj": getattr(getattr(request.user, "employee_profile", None), "pk", None),
    }
