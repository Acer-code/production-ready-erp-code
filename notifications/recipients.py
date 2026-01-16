from accounts.models import User

def admins_and_directors():
    return User.objects.filter(role__in=['admin', 'director'])

def service_team():
    return User.objects.filter(
        role__in=['admin', 'director']
    ) | User.objects.filter(
        role='employee',
        sub_employee_role='service'
    )

def all_except_dealers():
    return User.objects.exclude(role='dealer')

def dispatch_team():
    return User.objects.filter(
        role='employee',
        sub_employee_role='dispatch'
    ) | User.objects.filter(role__in=['admin', 'director'])
