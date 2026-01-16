from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from functools import wraps


# def role_required(*allowed_roles):
#     def decorator(view_func):
#         @wraps(view_func)
#         def wrapper(request, *args, **kwargs):

#             if not request.user.is_authenticated:
#                 return redirect('login')

#             if request.user.role not in allowed_roles:
#                 return HttpResponseForbidden("Access Denied.")

#             return view_func(request, *args, **kwargs)

#         return wrapper
#     return decorator

def role_required(*allowed):
    """
    Usage:
    @role_required('admin', 'director')
    @role_required('employee:service')
    @role_required('admin', 'employee:sales')
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect('login')

            user = request.user

            for rule in allowed:

                # CASE 1: Normal role (admin, dealer, director)
                if ':' not in rule:
                    if user.role == rule:
                        return view_func(request, *args, **kwargs)

                # CASE 2: Employee sub-role (employee:service)
                else:
                    role, sub_employee_role = rule.split(':')

                    if (
                        user.role == role and
                        getattr(user, 'sub_employee_role', None) == sub_employee_role
                    ):
                        return view_func(request, *args, **kwargs)

            return HttpResponseForbidden("Access Denied.")

        return wrapper
    return decorator

