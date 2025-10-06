from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()


@register.filter
def money(value, decimals=2):
    """
    Format numbers as financial strings with comma thousands, e.g. 1,234,567.89.
    Usage: {{ value|money }} or {{ value|money:0 }}
    """
    try:
        q = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    fmt = "{:,.%df}" % int(decimals)
    return fmt.format(q)

