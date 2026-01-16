from django.shortcuts import render, redirect, get_object_or_404
from django.forms import inlineformset_factory
from .decorators import role_required
from .models import Order, OrderItem
from django.db import transaction
from django.contrib import messages
from .forms import OrderForm, OrderItemForm, ProductForm
from .models import Order, OrderItem, Product
from services.models import ServiceRequest

@role_required('dealer')
def dealer_create_order(request):
    products = Product.objects.all()
    OrderItemFormSet = inlineformset_factory(Order, OrderItem, form=OrderItemForm, extra=1, can_delete=True)

    if request.method == 'POST':
        order_form = OrderForm(request.POST)
        formset = OrderItemFormSet(request.POST, prefix='items')

        if order_form.is_valid() and formset.is_valid():
            # Check if at least one product is added
            if not any([f.cleaned_data for f in formset if f.cleaned_data and not f.cleaned_data.get('DELETE', False)]):
                messages.error(request, 'Please add at least 1 product')
                return render(request, 'erp/dealer/create_order.html', {'order_form': order_form, 'formset': formset, 'products': products})
            try:
                with transaction.atomic():
                    order = order_form.save(commit=False)
                    order.dealer = request.user  # assign current vendor

                    # Billing same as shipping (optional checkbox in form)
                    if order_form.cleaned_data.get('billing_same_as_shipping'):
                        order.bill_building = order.shipp_building
                        order.bill_city = order.shipp_city
                        order.bill_state = order.shipp_state
                        order.bill_zip = order.shipp_zip
                        order.bill_country = order.shipp_country

                    order.save()

                    # Save order items
                    items = formset.save(commit=False)
                    for item in items:
                        item.unit_price = item.product.price
                        item.gst_rate = item.product.tax
                        item.order = order
                        item.save()

                    order.calculate_totals()

                messages.success(request, 'Order created successfully!')
                return redirect('dealer_dashboard')
            except Exception as e:
                messages.error(request, f'Error creating order: {e}')
        else:
            messages.error(request, 'Form is invalid')

    else:
        order_form = OrderForm()
        formset = OrderItemFormSet(prefix='items')

    return render(request, 'erp/dealer/create_order.html', {'order_form': order_form, 'formset': formset, 'products': products})



@role_required('dealer')
def dealer_dashboard(request):
    dealer = request.user.dealer_profile
    user = request.user

    # ================= ORDERS =================
    my_orders_count = Order.objects.filter(dealer=dealer).count()

    pending_shipments = Order.objects.filter(
        dealer=dealer,
        status__in=['pending','approved', 'dispatched']
    ).count()

    # ================= SERVICES =================
    open_services_count = ServiceRequest.objects.filter(
        raised_by=user
    ).exclude(status='closed').count()

    completed_services_count = ServiceRequest.objects.filter(
        raised_by=user,
        status='closed'
    ).count()

    context = {
        'my_orders_count': my_orders_count,
        'open_services_count': open_services_count,
        'completed_services_count': completed_services_count,
        'pending_shipments': pending_shipments,
    }

    return render(request, 'erp/dealer/dashboard.html', context)

@role_required('dealer')
def dealer_order_detail(request, pk):
    order = get_object_or_404(request.user.dealer_orders, pk=pk)
    return render(request, 'erp/dealer/order_detail.html',{'order':order})

@role_required('dealer')
def dealer_order_detail(request, pk):
    # Ensure vendor can only see their own orders
    dealer = request.user.dealer_profile
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=pk, dealer=dealer)
    order_items = order.items.all()  # using related_name
    return render(request, 'erp/dealer/order_detail.html', {'order': order, 'order_items': order_items})

@role_required('dealer')
def dealer_order_history(request):
    orders = request.user.dealer_orders.filter(status='delivered').order_by('-order_date')
    return render(request, 'erp/dealer/order_history.html',{'orders':orders})

