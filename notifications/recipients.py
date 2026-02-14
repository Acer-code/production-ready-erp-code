from accounts.models import User
from django.db.models import Q

def product_notification_users():
    """
    Stock notifications should go to:
    - Admin
    - Director
    - Sales employee
    - Inventory employee
    - Dispatch employee
    """
    return User.objects.filter(
        Q(role__in=['admin', 'director']) |
        Q(role='employee', sub_employee_role__in=[
            'sales', 'inventory', 'dispatch'
        ])
    )

def stock_notification_users():
    """
    Stock notifications should go to:
    - Admin
    - Director
    - Sales employee
    - Inventory employee
    - Dispatch employee
    """
    return User.objects.filter(
        Q(role__in=['admin', 'director']) |
        Q(role='employee', sub_employee_role__in=[
            'sales', 'inventory', 'dispatch'
        ])
    )

def admins_and_directors():
    return User.objects.filter(role__in=["admin", "director"])

def dispatch_team():
    return User.objects.filter(
        role="employee",
        sub_employee_role="dispatch"
    ) | admins_and_directors()

def inventory_team():
    return User.objects.filter(
        role="employee",
        sub_employee_role="inventory"
    ) | admins_and_directors()
