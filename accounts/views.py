from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm
from django.contrib import messages
from django.db import connections
from django.views.decorators.cache import never_cache
from erp.decorators import role_required
from .models import User

# Create your views here.
# views.py

@role_required('admin','director')
def suspend_user(request, user_id):
    user = User.objects.get(id=user_id)
    user.is_suspended = True
    user.save()
    messages.success(request, f"{user.username} has been suspended temporarily.")
    return redirect('user_list')


@role_required('admin','director')
def resume_user(request, user_id):
    user = User.objects.get(id=user_id)
    user.is_suspended = False
    user.save()
    messages.success(request, f"{user.username} has been activated successfully.")
    return redirect('user_list')


@never_cache
def user_login(request):
    # Ensure connection is fresh and not in a problematic state
    connections.close_all()
    
    if request.method =='POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            selected_role = form.cleaned_data.get('role')
            selected_sub_role = form.cleaned_data.get('sub_employee_role')
            user = authenticate(request, email=email, password=password)
            if user is None:
                messages.error(request, 'Invalid Email or Password')
                return redirect('login')
            if user.is_suspended:
                messages.error(request, "Your account is temporarily suspended.")
                return redirect('login')
            if user is not None:

                #ROLE VALIDATION BEFORE LOGIN
                if user.role != selected_role:
                    messages.error(request, "Invalid role selected.")
                    return redirect('login')

                if user.role == 'employee' and user.sub_employee_role != selected_sub_role:
                    messages.error(request, "Invalid employee role selected.")
                    return redirect('login')
                
                login(request, user)
                
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'dealer':
                    return redirect('dealer_dashboard')
                elif user.role == 'director':
                    return redirect('director_dashboard')
                elif user.role == 'employee':
                    if user.sub_employee_role == 'sales':
                        return redirect('sales_dashboard')
                    elif user.sub_employee_role == 'engineer':
                        return redirect('engineer_dashboard')
                    elif user.sub_employee_role == 'service':
                        return redirect('service_dashboard')
                    elif user.sub_employee_role == 'dispatch':
                        return redirect('dispatch_dashboard')
                    elif user.sub_employee_role == 'inventory':
                        return redirect('inventory_dashboard')
                    return redirect('/')
                    
            else:
                messages.error(request, 'Invalid Credentials or role mismatch')
    else:
        form = LoginForm()
    return render(request,'accounts/login.html',{'form':form})    


def user_logout(request):
    logout(request)
    return redirect('login')