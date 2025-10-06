from django import template
register = template.Library()

def _user_has_perm(user, code: str) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    employee = getattr(user, "employee_profile", None)
    if not employee:
        return False
    return employee.permissions.filter(permission=code, is_granted=True).exists()

@register.filter
def has_perm(user, code: str) -> bool:
    return _user_has_perm(user, code)
