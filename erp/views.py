from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Count, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from .models import Product, Stock, Order, OrderItem, Dispatch
from services.models import ServiceLog, ServiceRequest
from accounts.models import User, Dealer
from .decorators import role_required
from django.contrib import messages
from .forms import ProductForm, OrderForm, OrderItemFormSet, OrderItemForm
from django.db import transaction
from accounts.forms import CreateUserForm
from django.views.decorators.http import require_POST
from collections import defaultdict
from django.db.models import Q
from .pagination import paginate_queryset
from accounts.forms import DealerForm
from django.http import JsonResponse

# Create your views here.
def apply_filters(queryset, request, allowed_fields):
    for field in allowed_fields:
        value = request.GET.get(field)
        if value:
            queryset = queryset.filter(**{field: value})
    return queryset


def erp_global_search(request):
    q = request.GET.get('q', '').strip()

    products = Product.objects.none()
    orders = Order.objects.none()
    order_items = OrderItem.objects.none()
    users = User.objects.none()

    if q:
        #  Products
        products = Product.objects.filter(
            Q(name__icontains=q) |
            Q(product_model__icontains=q) |
            Q(category__icontains=q)
        )

        # Orders (ONLY VALID FIELDS)
        if q.isdigit():
            orders = Order.objects.filter(id=int(q))
        else:
            orders = Order.objects.filter(
                Q(full_name__icontains=q) |
                Q(company_name__icontains=q) |
                Q(email__icontains=q) |
                Q(phone__icontains=q) |
                Q(status__icontains=q) |
                Q(tracking_number__icontains=q)
            )

        #  Order Items (search by product)
        order_items = OrderItem.objects.filter(
            Q(product__name__icontains=q) |
            Q(product__product_model__icontains=q)
        ).select_related('order', 'product')

        # SERVICE REQUESTS
        if q.isdigit():
            services = ServiceRequest.objects.filter(id=int(q))
        else:
            services = ServiceRequest.objects.filter(
                Q(product_serial__icontains=q) |
                Q(product_name__icontains=q) |
                Q(product_model__icontains=q) |
                Q(status__icontains=q) |
                Q(order__full_name__icontains=q) |
                Q(order__company_name__icontains=q) |
                Q(order__email__icontains=q) |
                Q(order__phone__icontains=q) |
                Q(raised_by__email__icontains=q) |
                Q(assigned_engineer__email__icontains=q)
            )

        #  Users (EMAIL BASED)
        users = User.objects.filter(
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)
        )

    context = {
        'query': q,
        'products': products,
        'orders': orders,
        'order_items': order_items,
        'services': services,
        'users': users,
    }
    return render(request, 'erp/search/global_search.html', context)

@role_required('admin')
def admin_dashboard(request):

    # BASIC COUNTS
    total_users = User.objects.count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_service = ServiceRequest.objects.count()

    # ORDER METRICS
    pending_orders = Order.objects.filter(status='pending').count()
    completed_orders = Order.objects.filter(status='completed').count()

    # SERVICE METRICS
    open_services = ServiceRequest.objects.exclude(status='closed').count()
    completed_services = ServiceRequest.objects.filter(status='completed').count()
    closed_services = ServiceRequest.objects.filter(status='closed').count()

    # ACTIVITY
    total_activity = ServiceLog.objects.count()

    # SUCCESS RATE
    service_success_rate = (
        int((closed_services / total_service) * 100)
        if total_service > 0 else 0
    )

    context = {
        'total_users': total_users,
        'total_products': total_products,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,

        'total_service': total_service,
        'open_services': open_services,
        'completed_services': completed_services,
        'closed_services': closed_services,

        'total_activity': total_activity,
        'service_success_rate': service_success_rate,
    }
    return render(request, 'erp/admin/dashboard.html',context)

# Create User 
@role_required('admin')
def create_user(request):
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                messages.success(request, 'User created successfully!')
                if user.role == 'dealer':
                    return redirect('edit_dealer_details', pk=user.id)
                return redirect('user_list')
            except Exception as e:
                messages.error(request,f'Error creating user : {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form=CreateUserForm()
    
    return render(request,'erp/admin/user/create_user.html',{'form':form})

# Edit User
@role_required('admin')
def edit_user(request, pk):
    if request.method == 'POST':
        user = get_object_or_404(User, pk=pk)
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        company = request.POST.get('company')
        role = request.POST.get('role')
        print('role',role)
        sub_employee_role = request.POST.get('sub_employee_role')
        print('sub_employee_role',sub_employee_role)
        try:
            with transaction.atomic():
                user.first_name = first_name
                user.last_name = last_name
                user.phone = phone
                user.email = email
                user.company = company
                user.role = role
                user.sub_employee_role = sub_employee_role
                user.save()
            messages.success(request,'User updated successfully!')
        except Exception as e:
            messages.error(request,f'Error Updating User {e}')
        # return redirect('user_list')
    return redirect('user_list')

@role_required('admin')
def delete_user(request, pk):
    if request.method == 'POST':
        user = get_object_or_404(User, pk=pk)
        
        if request.user.id == user.id:
            messages.error(request,'You cannot delete your own account.')
            return redirect('user_list')
        try:
            user.delete()
            messages.success(request,'account deleted successfully!')
        except Exception as e:
            messages.error(request,f'Error During Delete account {e}')
    return redirect('user_list')

#USER LIST
@role_required('admin','director')
def user_list(request):
    users= User.objects.exclude(id= request.user.id)
    users = apply_filters(users, request, [
        'role',
        'sub_employee_role'
    ])
    create_user_form = CreateUserForm()
    page_obj = paginate_queryset(request, users, 10)
    return render(request,'erp/admin/user/user_list.html',{'users':page_obj,'create_user_form':create_user_form,'page_obj':page_obj})

# Product Related Views Start
# Add Product
@role_required('admin','employee:inventory')
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()

            messages.success(request, 'Product added successfully!')
            return redirect('product_list')
    return redirect('product_list')

# Edit Product
@role_required('admin','employee:inventory')
def edit_product(request,slug):
    product = get_object_or_404(Product, slug=slug)

    if request.method == 'POST':

        # form = ProductForm(request.POST, request.FILES, instance=product)
        product.name = request.POST.get('name')
        product.product_model = request.POST.get('product_model')
        product.category = request.POST.get('category')
        product.price = request.POST.get('price')
        product.tax =request.POST.get('tax')
        product.desc = request.POST.get('desc')
        if 'img' in request.FILES:
            product.img = request.FILES['img']
        product.save()
        if product.product_model:
            messages.success(request, f"'{product.name} ({product.product_model})' updated successfully!")
        else:
            messages.success(request, f"'{product.name}' updated successfully!")
        return redirect('product_list')

    return redirect('product_list')

# Delete Product
@role_required('admin','employee:inventory')
def delete_product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    try:
        stock = Stock.objects.get(product=product)
        stock.delete()
    except Stock.DoesNotExist:
        pass
    product.delete()
    messages.success(request, 'Product deleted successfully!')
    return redirect('product_list')

# PRODUCT LIST
@role_required('admin','director','dealer','employee:sales','employee:inventory','employee:dispatch')
def product_list(request):
    stock_status = request.GET.get('stock_status')  
    # values: in, low, out

    products = Product.objects.all()
    stocks = Stock.objects.select_related('product')

    if stock_status == 'in':
        stocks = stocks.filter(current_quantity__gt=F('min_stock_level'))

    elif stock_status == 'low':
        stocks = stocks.filter(
            current_quantity__lte=F('min_stock_level'),
            current_quantity__gt=0
        )

    elif stock_status == 'out':
        stocks = stocks.filter(current_quantity__lte=0)

    else:
        # ALL → no filtering
        stocks = stocks.all()

    # map back to products
    products = products.filter(id__in=stocks.values('product_id'))
    page_obj = paginate_queryset(request, products, 10)
    out_of_stock_products = Stock.objects.filter(current_quantity__lte=0).select_related('product')
    return render(request, 'erp/admin/product_list.html',{'products':page_obj, 'page_obj':page_obj,'out_of_stock_products':out_of_stock_products,'stock_status':stock_status})
# PRODUCT RELATED VIEWS END

# Inventory/STOCK Views Start
@role_required('admin', 'director','employee:sales','employee:inventory','employee:dispatch')
def inventory_list(request):
    LOW_STOCK_LIMIT = 10
    stocks = Stock.objects.select_related('product').all()
    low_stocks = Stock.objects.select_related('product').filter(current_quantity__lte=LOW_STOCK_LIMIT)

    # status filter
    status = request.GET.get('status')

    if status == 'low':
        stocks = stocks.filter(
            current_quantity__gt=0,
            current_quantity__lte=F('min_stock_level')
        )
    elif status == 'out':
        stocks = stocks.filter(current_quantity=0)
    elif status == 'ok':
        stocks = stocks.filter(current_quantity__gt=F('min_stock_level'))
    page_obj = paginate_queryset(request, stocks, 10)
    return render(request, 'erp/admin/inventory_list.html',{'page_obj':page_obj,'stocks': page_obj,'low_stocks':low_stocks,'low_stock_count':low_stocks.count()})

@role_required('admin','employee:inventory')
def update_inventory_stock(request, pk):
    stock  = get_object_or_404(Stock, pk=pk)
    if request.method == 'POST':
        try:
            stock.new_stock_shippment = int(request.POST.get('new_stock_shippment'))
            # stock.current_quantity = int(request.POST.get('current_quantity', stock.current_quantity))
            # stock.min_stock_level = int(request.POST.get('min_stock_level', stock.min_stock_level))
            # stock.total_stock = int(request.POST.get('total_stock', stock.total_stock))
        except ValueError:
            messages.error(request, "Please enter valid shippment quantity.")
            return redirect('inventory_list')
        stock.location = request.POST.get('location', stock.location)
        stock.save()
        messages.success(request, 'Stock updated successfully!') 
        return redirect('inventory_list')
    return redirect('inventory_list')

# Inventory/Stock Views End

# create Order
@role_required('admin', 'dealer', 'employee:sales')
def create_order(request):

    products = Product.objects.all()

    if request.method == 'POST':
        order_form = OrderForm(request.POST, user=request.user)
        formset = OrderItemFormSet(request.POST, prefix='items')

        if order_form.is_valid() and formset.is_valid():

            # -----------------------------------
            # At least one product
            # -----------------------------------
            valid_items = [
                f.cleaned_data for f in formset
                if f.cleaned_data and not f.cleaned_data.get('DELETE', False)
            ]

            if not valid_items:
                messages.error(request, 'Please add at least one product.')
                return render(request, 'erp/admin/order/create_order.html', {
                    'order_form': order_form,
                    'formset': formset,
                    'products': products
                })

            try:
                with transaction.atomic():

                    # -----------------------------------
                    #Create Order
                    # -----------------------------------
                    order = order_form.save(commit=False)
                    order.created_by = request.user

                    # -----------------------------------
                    # Role logic
                    # -----------------------------------
                    if request.user.role == 'dealer':
                        order.dealer = request.user.dealer_profile            # assign User for FK
                        dealer_profile = request.user.dealer_profile  # get Dealer object

                    if request.user.role == 'employee' and request.user.sub_employee_role == 'sales':
                        order.sales_person = request.user
                        # dealer from form

                 

                    # -----------------------------------
                    # Billing == Shipping
                    # -----------------------------------
                    if order_form.cleaned_data.get('billing_same_as_shipping'):
                        order.bill_building = order.shipp_building
                        order.bill_city = order.shipp_city
                        order.bill_state = order.shipp_state
                        order.bill_zip = order.shipp_zip
                        order.bill_country = order.shipp_country

                    order.save()

                    # -----------------------------------
                    # MERGE DUPLICATE PRODUCTS 
                    # -----------------------------------
                    product_qty_map = defaultdict(int)

                    for item in valid_items:
                        product = item['product']
                        qty = item['qty']
                        product_qty_map[product] += qty

                    # -----------------------------------
                    #  Save clean order items
                    # -----------------------------------
                    for product, qty in product_qty_map.items():
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            qty=qty,
                            unit_price=product.price,
                            gst_rate=product.tax
                        )

                    # -----------------------------------
                    #Calculate totals
                    # -----------------------------------
                    order.calculate_totals()

                messages.success(request, 'Order created successfully.')
                return redirect('order_list')

            except Exception as e:
                print('Order creation error:', e)
                messages.error(request, 'Something went wrong while creating order.')

        else:
            messages.error(request, 'Invalid form data.')


    else:
        order_form = OrderForm(user=request.user)

        # auto fill for dealer
        if request.user.role == 'dealer':
            dealer = request.user.dealer_profile
            order_form.initial = {
                'full_name': dealer.get_full_name(),
                'phone': dealer.user.phone,
                'email': dealer.user.email,
                'company_name': dealer.firm_name,
                'gstin': dealer.gst_number,
                'bill_building': dealer.bill_address_line1,
                'bill_city': dealer.bill_city,
                'bill_state': dealer.bill_state,
                'bill_zip': dealer.bill_pincode,
                'bill_country': dealer.bill_country,
                'shipp_building': dealer.ship_address_line1,
                'shipp_city': dealer.ship_city,
                'shipp_state': dealer.ship_state,
                'shipp_zip': dealer.ship_pincode,
                'shipp_country': dealer.ship_country,
            }

        formset = OrderItemFormSet(prefix='items')

    return render(request, 'erp/admin/order/create_order.html', {
        'order_form': order_form,
        'formset': formset,
        'products': products
    })

@role_required('admin', 'employee:sales')
def get_dealer_details(request, dealer_id):
    dealer = Dealer.objects.get(id=dealer_id)

    return JsonResponse({
        'success': True,
        'full_name': dealer.get_full_name(),
        'phone': dealer.user.phone,
        'email': dealer.user.email,
        'company': dealer.firm_name,
        'gstin': dealer.gst_number,
        'bill_building': dealer.bill_address_line1,
        'bill_city': dealer.bill_city,
        'bill_state': dealer.bill_state,
        'bill_zip': dealer.bill_pincode,
        'bill_country': dealer.bill_country,
        'shipp_building': dealer.ship_address_line1,
        'shipp_city': dealer.ship_city,
        'shipp_state': dealer.ship_state,
        'shipp_zip': dealer.ship_pincode,
        'shipp_country': dealer.ship_country,
    })


# @role_required('admin','employee:dispatch')
# @require_POST
# def update_order_status(request, pk):
#     order = get_object_or_404(Order, pk=pk)
#     new_status = request.POST.get('status')
#     valid_statuses = dict(Order.ORDER_STATUS)

#     if order.status == 'delivered':
#         messages.warning(request, "Delivered orders cannot be changed.")
#         return redirect(request.META.get('HTTP_REFERER'))
    
#     # Allowed forward transitions
#     allowed_transitions ={
#         'pending':['approved','rejected'],
#         'approved':['dispatched'],
#         'dispatched':['delivered']
#     }

#     # CHECK TRANSITION VALIDITY
#     if new_status in valid_statuses:
#         if order.status in allowed_transitions:
#             if new_status in allowed_transitions[order.status]:
#                 # If approving, reduce stock
#                 if new_status == 'approved':
#                     for item in order.items.all():  # loop through OrderItem
#                         try:
#                             stock = Stock.objects.get(product=item.product)
#                             if stock.current_quantity is None:
#                                 stock.current_quantity = 0
#                             stock.current_quantity -= item.qty
#                             # Prevent negative stock
#                             if stock.current_quantity < 0:
#                                 stock.current_quantity = 0
#                             stock.save()
#                         except Stock.DoesNotExist:
#                             # Optional: create stock or skip
#                             pass
#                 order.status = new_status
#                 order.save()
#     return redirect(request.META.get('HTTP_REFERER'))


@role_required('admin','employee:dispatch')
@require_POST
def update_order_status(request, pk):
    order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
    new_status = request.POST.get('status')
    valid_statuses = dict(Order.ORDER_STATUS)

    if order.status == 'delivered':
        messages.warning(request, "Delivered orders cannot be changed.")
        return redirect(request.META.get('HTTP_REFERER'))

    allowed_transitions = {
        'pending': ['approved', 'rejected'],
        'approved': ['dispatched'],
        'dispatched': ['delivered']
    }

    if new_status not in valid_statuses:
        messages.error(request, "Invalid status.")
        return redirect(request.META.get('HTTP_REFERER'))

    if order.status not in allowed_transitions or \
       new_status not in allowed_transitions[order.status]:
        messages.error(request, "Invalid status transition.")
        return redirect(request.META.get('HTTP_REFERER'))

    try:
        with transaction.atomic():

            # APPROVE → deduct stock
            if order.status == 'pending' and new_status == 'approved':
                for item in order.items.select_related('product'):
                    stock = Stock.objects.select_for_update().get(product=item.product)

                    if stock.current_quantity < item.qty:
                        messages.error(
                            request,
                            f"Not enough stock for {item.product.name}. "
                            f"Available: {stock.current_quantity}"
                        )
                        return redirect(request.META.get('HTTP_REFERER'))

                    stock.current_quantity = F('current_quantity') - item.qty
                    stock.save()

            # REJECT → restore stock (only if already approved)
            if order.status == 'approved' and new_status == 'rejected':
                for item in order.items.select_related('product'):
                    stock = Stock.objects.select_for_update().get(product=item.product)
                    stock.current_quantity = F('current_quantity') + item.qty
                    stock.save()

            order.status = new_status
            order.save()

            messages.success(request, f"Order marked as {new_status}.")

    except Stock.DoesNotExist:
        messages.error(request, "Stock record missing for one or more products.")

    return redirect(request.META.get('HTTP_REFERER'))


# Update order tracking details
@role_required('admin','employee:dispatch')
def update_order_tracking(request,pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        courier = request.POST.get('courier')
        tracking = request.POST.get('tracking_number')

        order.courier = courier
        order.tracking_number = tracking

        if order.tracking_number:
            order.status = 'dispatched'

        order.save()

    return redirect(request.META.get('HTTP_REFERER'))

# ORDER DETAILS
@role_required('admin', 'director','dealer','employee:sales','employee:dispatch')
def order_detail(request, id):
    order = get_object_or_404(Order.objects.select_related('created_by', 'dealer__user', 'sales_person').prefetch_related('items__product'), id=id)
    order_items = OrderItem.objects.filter(order=order)
    return render(request, 'erp/admin/order/order_detail.html',{'order':order, 'order_items':order_items})


@role_required('admin', 'dealer', 'employee:sales','director','employee:dispatch')
def order_list(request):
    user = request.user
    pending_orders = Order.objects.filter(status='pending').prefetch_related('items__product')
    if user.role == 'admin':
        orders = Order.objects.select_related(
            'dealer', 'created_by', 'sales_person'
        )
        

    elif user.role == 'dealer':
        orders = Order.objects.select_related(
            'dealer', 'created_by'
        ).filter(dealer=user.dealer_profile)   

    elif user.role == 'employee' and user.sub_employee_role == 'sales':
        orders = Order.objects.select_related(
            'dealer', 'created_by'
        ).filter(created_by=user)

    else:
        orders = Order.objects.all().order_by('-order_date')
        # return HttpResponseForbidden()

     # status filter
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)

    page_obj = paginate_queryset(request, orders, 10)

    return render(request, 'erp/admin/order/order_list.html', {'orders': page_obj,'page_obj':page_obj, 'pending_orders': pending_orders})



# Sales Employee Views Start
@role_required('employee:sales')
def sales_dashboard(request):
    user = request.user
    today = timezone.now().date()
    week_start = today - timedelta(days=7)

    # Total sales by this salesperson (only delivered orders)
    my_sales = (
        Order.objects.filter(sales_person=user, status='delivered')
        .aggregate(total=Sum('grand_total'))['total'] or 0
    )

    # Orders created by this salesperson this week
    orders_this_week = Order.objects.filter(
        sales_person=user,
        order_date__gte=week_start
    ).count()

    # Pending deliveries (approved / dispatched but not delivered)
    pending_deliveries = Order.objects.filter(
        sales_person=user,
        status__in=['approved', 'dispatched']
    ).count()

    # Inventory summary
    inventory_units = Stock.objects.aggregate(total=Sum('current_quantity'))['total'] or 0
    product_count = Product.objects.filter().count()

    context = {
        'my_sales': my_sales,
        'orders_this_week': orders_this_week,
        'pending_deliveries': pending_deliveries,
        'inventory_units': inventory_units,
        'product_count': product_count,
    }

    return render(request,'erp/sales/sales_dashboard.html', context)
# End Sales Employee Views

@role_required('employee:inventory')
def inventory_dashboard(request):
    # Total products
    total_products = Product.objects.count()

    # Low stock count
    low_stock_count = Stock.objects.filter(
        current_quantity__lte=F('min_stock_level')
    ).count()

    # Total stock value (current_quantity * product.price)
    total_stock_value = Stock.objects.annotate(
        value=F('product__price') * Coalesce(F('current_quantity'), Value(0))
    ).aggregate(total=Sum('value'))['total'] or 0

    context = {
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'total_stock_value': total_stock_value,
    }

    return render(request, 'erp/inventory/inventory_dashboard.html', context)


# Dispatch Dashboard View
@role_required('employee:dispatch')
def dispatch_dashboard(request):

    today = timezone.now().date()

    # Pending = approved but not dispatched
    pending_shipments = Order.objects.filter(
        status='approved',
        dispatch__isnull=True
    ).count()

    # Shipped today
    shipped_today = Order.objects.filter(
        status='dispatched',
        dispatch__dispatch_date__date=today
    ).count()

    # Delayed = approved but not dispatched after X days
    delayed_orders = Order.objects.filter(
        status='approved',
        order_date__lt=today - timezone.timedelta(days=4),
        dispatch__isnull=True
    ).count()

    return render(request, 'erp/dispatch/dispatch_dashboard.html', {
        'pending_shipments': pending_shipments,
        'shipped_today': shipped_today,
        'delayed_orders': delayed_orders,
    })

# dealer
@role_required('admin')
def edit_dealer_profile(request,pk):
    # Always ensure profile exists
    # dealer = get_object_or_404(Dealer, pk=pk)
    user = get_object_or_404(User, id=pk)

    # Auto-create dealer if not exists
    dealer, created = Dealer.objects.get_or_create(user=user)
    if request.method == 'POST':
        form = DealerForm(request.POST, instance=dealer)
        if form.is_valid():
            dealer = form.save(commit=False)

            # Copy shipping → billing if checked
            if form.cleaned_data.get('same_as_shipping'):
                dealer.bill_address_line1 = dealer.ship_address_line1
                dealer.bill_address_line2 = dealer.ship_address_line2
                dealer.bill_city = dealer.ship_city
                dealer.bill_state = dealer.ship_state
                dealer.bill_pincode = dealer.ship_pincode
                dealer.bill_country = dealer.ship_country

            dealer.save()
            messages.success(request, "Dealer Details updated successfully.")
            return redirect('user_list')
    else:
        form = DealerForm(instance=dealer)

    return render(request, 'erp/dealer/edit_profile.html', {'form': form, 'user': user})
