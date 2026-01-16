from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Count
from django.utils import timezone
from datetime import timedelta
from .models import Product, Stock, Order, OrderItem, Dispatch
from services.models import ServiceRequest
from accounts.models import User
from .decorators import role_required


# Director DASHBOARD START
# @role_required('director')
# def director_dashboard(request):
#     total_products = Product.objects.count()
#     total_dealers =User.objects.filter(role='dealer').count()
#     total_employees = User.objects.filter(role='employee').count()
#     total_orders = Order.objects.count()
#     total_services = ServiceRequest.objects.count()
#     total_dispatches = Dispatch.objects.count()

#     # Revenue Calculation
#     total_revenue = OrderItem.objects.aggregate(total=Sum(F('qty')*F('product__price')))['total']
#     # monthly sales data for past 30 days
#     last_30_days = timezone.now()-timedelta(days=30)
#     monthly_sales = OrderItem.objects.filter(order__order_date__gte=last_30_days).aggregate(total=Sum(F('qty')*F('product__price')))['total']

#     # top_selling_products = OrderItem.objects.values('product__name').annotate(total_sold=Sum('qty')).order_by('-total_sold')[:5]
#     top_selling_products=(
#         OrderItem.objects.values('product__name')
#         .annotate(total_sold=Sum('qty'))
#         .order_by('-total_sold')[:5]
#     )
#     # Sales by Employee
#     # sales_by_employee = Order.objects.filter(order_by__role='employee').values('order_by__username').annotate(total_sales=Sum(F('orderitem__qty')*F('orderitem__product__price')))
#     sales_by_employee=(
#         Order.objects.values('order_by__username')
#         .filter(order_by__role='employee')
#         .annoatate(total_sales=Sum(F('orderitem__qty')*F('orderitem__product__price')))
#         .order_by('total_sales')
#     )
    
#     # Sales by Dealer
#     # sales_by_dealer = Order.objects.filter(order_by__role='dealer').values('order_by__username').annotate(total_sales=Sum(F('orderitem__qty')*F('orderitem__product__price')))
#     sales_by_dealer=(
#         Order.objects.values('order_by__username')
#         .filter(order_by__role='dealer')
#         .annotate(total_sales=Sum(F('orderitem__qty')*F('orderitem__product__price')))
#         .order_by('total_sales')
#     )

#     # Service Summary
#     service_summary =(
#         ServiceRequest.objects.values('status')
#         .annotate(total =Count('id'))
#     )
#     # Request Per Engineer
#     service_by_engineer=(
#         ServiceRequest.objects.values('assigned_engineer__username')
#         .annotate(total=Count('id'))
#         .order_by('-total')
#     )

#     # low stock products
#     low_stock_products = Stock.objects.filter(quantity__lt=10)

#     context = {
#         'total_products':total_products,
#         'total_dealers':total_dealers,
#         'total_employees':total_employees,
#         'total_orders':total_orders,
#         'total_services':total_services,
#         'total_dispatches':total_dispatches,
#         'total_revenue':total_revenue,
#         'monthly_sales':monthly_sales,
#         'top_selling_products':top_selling_products,
#         'sales_by_employee':sales_by_employee,
#         'sales_by_dealer':sales_by_dealer,
#         'service_summary':service_summary,
#         'service_by_engineer':service_by_engineer,
#         'low_stock_products':low_stock_products,
#     }
#     return render(request, 'erp/director/director_dashboard.html', context)



@role_required('director')
def director_dashboard(request):

    total_products = Product.objects.count()
    total_dealers = User.objects.filter(role='dealer').count()
    total_employees = User.objects.filter(role='employee').count()
    total_orders = Order.objects.count()
    total_services = ServiceRequest.objects.count()
    total_dispatches = Dispatch.objects.count()

    total_revenue = OrderItem.objects.aggregate(
        total=Sum(F('qty') * F('product__price'))
    )['total'] or 0

    last_30_days = timezone.now() - timedelta(days=30)
    monthly_sales = OrderItem.objects.filter(
        order__order_date__gte=last_30_days
    ).aggregate(
        total=Sum(F('qty') * F('product__price'))
    )['total'] or 0

    top_selling_products = (
        OrderItem.objects.values('product__name')
        .annotate(total_sold=Sum('qty'))
        .order_by('-total_sold')[:5]
    )

    service_summary = (
        ServiceRequest.objects.values('status')
        .annotate(total=Count('id'))
    )

    service_by_engineer = (
        ServiceRequest.objects.values('assigned_engineer__email')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    low_stock_products = Stock.objects.filter(current_quantity__lt=10)

    context = {
        'total_products': total_products,
        'total_dealers': total_dealers,
        'total_employees': total_employees,
        'total_orders': total_orders,
        'total_services': total_services,
        'total_dispatches': total_dispatches,
        'total_revenue': total_revenue,
        'monthly_sales': monthly_sales,
        'top_selling_products': top_selling_products,
        'service_summary': service_summary,
        'service_by_engineer': service_by_engineer,
        'low_stock_products': low_stock_products,
    }

    return render(request, 'erp/director/director_dashboard.html', context)

# Director DASHBOARD END