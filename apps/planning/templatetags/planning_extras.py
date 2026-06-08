from django import template

register = template.Library()


@register.filter
def sum_values(d):
    """Sum the values of a dict — used for the diet-warning badge count."""
    return sum(d.values()) if d else 0
