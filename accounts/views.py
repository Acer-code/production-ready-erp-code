from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm, CreateUserForm
from django.contrib import messages
from erp.views import admin_dashboard
from django.db import transaction, connections
from django.views.decorators.cache import never_cache
from erp.views_dealer import dealer_dashboard

# Create your views here.


@never_cache
def user_login(request):
    # Ensure connection is fresh and not in a problematic state
    connections.close_all()
    
    if request.method =='POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            if user:
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