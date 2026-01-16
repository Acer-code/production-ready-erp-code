from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from erp.decorators import role_required
from .models import ServiceRequest, ServiceSparePart,ServiceAttachment,ServiceClosure,ServiceFeedback,ServiceLog,ServiceStatusHistory
from accounts.models import User
from django.http import HttpResponseForbidden
from .forms import ServiceRequestForm
from erp.models import Product
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.db import transaction

# Create your views here.

@role_required('employee:service')
def service_dashboard(request):
    user = request.user

    # ================= METRICS =================
    total_products = Product.objects.count()

    open_service_requests = ServiceRequest.objects.filter(
        assigned_engineer=user
    ).exclude(status='closed').count()

    assigned_services = ServiceRequest.objects.filter(
        assigned_engineer=user
    ).exclude(status='closed').count()

    context = {
        'total_products': total_products,
        'open_service_requests': open_service_requests,
        'assigned_services': assigned_services,
    }

    return render(request, 'services/service_dashboard.html', context)

@role_required('dealer', 'employee:service', 'employee:sales', 'admin')
def raise_service_request(request):
    if request.method == 'POST':
        serial_no = request.POST.get('product_serial')

        # Check block: any spare part not returned after 7 days
        blocked_spares = ServiceSparePart.objects.filter(
            service_request__product_serial=serial_no,
            status__in=['assigned', 'not_returned'],
            assigned_at__lt=timezone.now() - timedelta(days=7)
        )

        if blocked_spares.exists():
            messages.error(
                request,
                "Service request blocked! Spare parts from previous service "
                "have not been returned within 7 days."
            )
            return redirect(request.META.get('HTTP_REFERER'))

        form = ServiceRequestForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    service_request = form.save(commit=False)

                    if service_request.order_item:
                        service_request.order = service_request.order_item.order

                    service_request.raised_by = request.user
                    service_request.save()   # ← will rollback if signal fails

                messages.success(request, "Service request raised successfully.")
                return redirect('service_list')

            except Exception as e:
                # Show the actual error
                import traceback
                messages.error(
                    request,
                    f"Service request failed: {str(e)}"
                )
                print(traceback.format_exc())
                return redirect(request.META.get('HTTP_REFERER'))

        else:
            messages.error(request, "Please correct the errors below.")


    else:
        form = ServiceRequestForm(user=request.user)

    # Check if any delivered products are available
    if not form.fields['order_item'].queryset.exists():
        messages.info(
            request,
            "No delivered products available from your orders to raise a service request."
        )

    return render(request, 'services/raise_service.html', {'form': form})

# =========================
# SERVICE LIST 
# =========================
@role_required('admin', 'director', 'dealer', 'employee:service', 'employee:sales')
def service_list(request):

    user = request.user

    if user.role in ['admin', 'director']:
        # Admin & Director → all service requests
        services = ServiceRequest.objects.all()

    elif user.role == 'dealer':
        # Dealer → only their own service requests
        services = ServiceRequest.objects.filter(raised_by=user)

    elif user.role == 'employee' and user.sub_employee_role == 'sales':
        # Sales person → services raised by them
        services = ServiceRequest.objects.filter(raised_by=user)

    elif user.role == 'employee' and user.sub_employee_role == 'service':
        # Service person → ONLY services assigned to them
        services = ServiceRequest.objects.filter(assigned_engineer=user)

    else:
        services = ServiceRequest.objects.none()

    services = services.order_by('-created_at')

    return render(
        request,
        'services/admin/service_list.html',
        {'services': services}
    )

# =========================
# ASSIGN / REASSIGN ENGINEER
# =========================
@role_required('admin')
def assign_service_engineer(request, pk):
    service = get_object_or_404(ServiceRequest, pk=pk)
    engineers = User.objects.all().filter(role='employee',sub_employee_role = 'service')
    if request.method == 'POST':
        engineer_id = request.POST.get('engineer_id')
        engineer = get_object_or_404(User, pk = engineer_id)
        service.assigned_engineer = engineer
        service.status = 'assigned'
        service.save()

        ServiceLog.objects.create(
            service_request = service,
            updated_by = request.user,
            note = f"Engineer {engineer.get_full_name()} assigned"
        )
        old_status = 'raised'
        ServiceStatusHistory.objects.create(
            service_request=service,
            old_status=old_status,
            new_status='assigned',
            changed_by=request.user
        )

        return redirect('service_list')
    
    return render(request, 'services/admin/assign_engineer.html',{'service':service,'engineers':engineers})

# =========================
# CHANGE SERVICE STATUS (FORWARD-ONLY)
# =========================
@role_required('admin','employee:service')
def change_service_status(request, pk):
    service = get_object_or_404(ServiceRequest, pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        old_status = service.status

        STATUS_FLOW = [
            'raised', 'assigned', 'waiting_spare',
            'in_progress', 'completed', 'closed'
        ]

        current_index = STATUS_FLOW.index(old_status)
        allowed_next = STATUS_FLOW[current_index + 1:current_index + 2]

        if new_status not in allowed_next:
            messages.error(request, "Invalid status transition")
            return redirect(request.META.get('HTTP_REFERER'))

        # Engineers cannot complete or close
        if request.user.sub_employee_role != 'service' and new_status in ['completed', 'closed']:
            messages.error(request, "Only Engineer can complete or close service")
            return redirect(request.META.get('HTTP_REFERER'))
        
        # BLOCK closing without resolution summary
        if new_status == 'closed':
            if not hasattr(service, 'closure') or not service.closure.resolution_summary:
                messages.error(
                    request,
                    "Add Resolution Summary before closing the service request."
                )
                return redirect(request.META.get('HTTP_REFERER'))


        service.status = new_status
        service.updated_by = request.user
        service.save(update_fields=['status', 'updated_by'])

        ServiceLog.objects.create(
            service_request=service,
            updated_by=request.user,
            note=f"Status changed from {old_status} → {new_status}"
        )
        ServiceStatusHistory.objects.create(
            service_request=service,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user
        )


    return redirect(request.META.get('HTTP_REFERER'))

# =========================
# ADD MULTIPLE SPARE PARTS
# =========================
@role_required('admin', 'employee:service')
def add_spare_parts(request, pk):
    service = get_object_or_404(ServiceRequest, pk=pk)

    if service.status in ['completed', 'closed']:
        messages.error(request, 'Cannot add spare parts at this stage!')
        return redirect(request.META.get('HTTP_REFERER'))

    if request.method == 'POST':
        parts_data = request.POST.getlist('part_name')
        part_numbers = request.POST.getlist('part_number')
        quantities = request.POST.getlist('quantity')

        added_any = False
        for i, part_name in enumerate(parts_data):
            if part_name.strip() == '':
                continue

            ServiceSparePart.objects.create(
                service_request=service,
                part_name=part_name,
                part_number=part_numbers[i],
                quantity=int(quantities[i]),
                status='assigned',
                assigned_at=timezone.now()
            )
            ServiceLog.objects.create(
                service_request=service,
                updated_by=request.user,
                note=f"Spare part '{part_name}' added"
            )
            added_any = True

        if added_any:
            # Automatically update service status
            if service.status == 'assigned':
                service.status = 'waiting_spare'
                service.updated_by = request.user
                service.save(update_fields=['status', 'updated_by'])
                
                ServiceStatusHistory.objects.create(
                    service_request=service,
                    old_status='assigned',
                    new_status='waiting_spare',
                    changed_by=request.user
                )
            messages.success(request, "Spare parts added successfully.")
        else:
            messages.error(request, "No valid spare parts provided.")

        return redirect(request.META.get('HTTP_REFERER'))

    return HttpResponseForbidden("Invalid request")

# =========================
# UPDATE SPARE PART STATUS (NO REASSIGN AFTER IN-PROGRESS)
# =========================
@role_required('admin')
def update_spare_part_status(request, spare_id):
    spare = get_object_or_404(ServiceSparePart, pk=spare_id)
    service = spare.service_request
    old_status = service.status

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status not in ['returned', 'not_returned']:
            messages.error(request, "Invalid spare status")
            return redirect(request.META.get('HTTP_REFERER'))

        spare.status = new_status
        spare.returned_at = timezone.now()

        
        spare.save(update_fields=['status', 'returned_at'])

        
        ServiceStatusHistory.objects.create(
            service_request=service,
            old_status=old_status,
            new_status='in_progress',
            changed_by=request.user
        )

        # Move service forward if all spares returned
        if new_status == 'returned':
            if not service.spare_parts.filter(status='assigned').exists():
                if service.status == 'waiting_spare':
                    service.status = 'in_progress'
                    service.updated_by = request.user
                    service.save(update_fields=['status', 'updated_by'])

        ServiceLog.objects.create(
            service_request=service,
            updated_by=request.user,
            note=f"Spare part '{spare.part_name}' marked as {new_status}"
        )

        messages.success(request, "Spare part status updated")

    return redirect(request.META.get('HTTP_REFERER'))

# =========================
# REMOVE SPARE PART

@role_required('admin', 'employee:service')
def remove_spare_part(request, service_id, spare_id):
    service = get_object_or_404(ServiceRequest, pk=service_id)
    spare = get_object_or_404(ServiceSparePart, pk=spare_id, service_request=service)

    if service.status == 'closed':
        messages.error(request, 'Cannot remove spare part from a closed service.')
        return redirect(request.META.get('HTTP_REFERER'))

    spare.delete()

    # Optional: add a log entry
    ServiceLog.objects.create(
        service_request=service,
        updated_by=request.user,
        note=f"Removed spare part: {spare.part_name}"
    )

    messages.success(request, f"Spare part '{spare.part_name}' removed successfully.")
    return redirect(request.META.get('HTTP_REFERER'))

# =========================
# CLOSE SERVICE (FINAL)
# =========================  

@role_required('admin', 'employee:service')
def close_service(request, pk):

    user = request.user

    # ================= GET SERVICE (ROLE SAFE) =================
    if user.role == 'admin':
        service = get_object_or_404(ServiceRequest, pk=pk)
    else:
        service = get_object_or_404(
            ServiceRequest,
            pk=pk,
            assigned_engineer=user
        )

    # ================= VALIDATIONS =================
      # Engineer can only close their own service
    if user.role == 'employee' and service.assigned_engineer != user:
        return HttpResponseForbidden("Not allowed")
    if service.status == 'closed':
        messages.error(request, 'Service already closed!')
        return redirect(request.META.get('HTTP_REFERER'))

    if service.status != 'completed':
        messages.error(request, 'Service must be completed before closing!')
        return redirect(request.META.get('HTTP_REFERER'))

    # ================= CLOSE SERVICE =================
    if request.method == 'POST':
        resolution = request.POST.get('resolution')

        if not resolution:
            messages.error(request, 'Resolution is required!')
            return redirect(request.META.get('HTTP_REFERER'))

        ServiceClosure.objects.create(
            service_request=service,
            resolution_summary=resolution,
            closed_by=user
        )

        service.status = 'closed'
        service.updated_by = user
        service.save(update_fields=['status', 'updated_by'])
       
        ServiceStatusHistory.objects.create(
            service_request=service,
            old_status='completed',
            new_status='closed',
            changed_by=user
        )
        # AUTO UPDATE SPARE PARTS
        service.spare_parts.filter(
            status='assigned'
        ).update(
            status='not_returned',
            returned_at=timezone.now()
        )

        ServiceLog.objects.create(
            service_request=service,
            updated_by=user,
            note='Service closed'
        )

        messages.success(request, 'Service closed successfully')

    return redirect(request.META.get('HTTP_REFERER'))

# =========================
# SERVICE DETAIL (ADMIN)
# =========================

@role_required('admin', 'director', 'dealer', 'employee:service', 'employee:sales')
def service_detail(request, pk):

    user = request.user

    # ---------- ACCESS CONTROL ----------
    if user.role in ['admin', 'director']:
        service = get_object_or_404(ServiceRequest, pk=pk)

    elif user.role == 'dealer':
        service = get_object_or_404(ServiceRequest, pk=pk, raised_by=user)

    elif user.role == 'employee' and user.sub_employee_role == 'sales':
        service = get_object_or_404(ServiceRequest, pk=pk, raised_by=user)

    elif user.role == 'employee' and user.sub_employee_role == 'service':
        service = get_object_or_404(ServiceRequest, pk=pk, assigned_engineer=user)

    else:
        return HttpResponseForbidden("Access denied")
    
    # ---------- ORDER & CUSTOMER ----------
    order = None
    order_item = None
    customer = None
    order_creator = None

    if service.order_item:
        order_item = service.order_item
        order = order_item.order


        customer = {
            'name': order.full_name,
            'phone': order.phone,
            'email': order.email,
            'company': order.company_name,
            'gstin': order.gstin,
            'shipping_address': f"{order.shipp_building}, {order.shipp_city}, {order.shipp_state} - {order.shipp_zip}",
        }

        # WHO PLACED THE ORDER (Dealer / Sales / Admin)
        order_creator = order.creator_display


    # ---------- FLAGS ----------
    is_engineer = user.role == 'employee' and user.sub_employee_role == 'service'
    is_dealer = user.role == 'dealer'
    is_admin = user.role in ['admin', 'director']

    can_edit_status = is_engineer or is_admin

    has_assigned_spares = service.spare_parts.filter(status='assigned').exists()
    is_service_final = service.status in ['completed', 'closed']



    # ---------- SPARE & BLOCK STATUS ----------
    machine_blocked = service.is_machine_blocked()

    overdue_spares_48 = service.spare_parts.filter(
        status='assigned',
        assigned_at__lt=timezone.now() - timedelta(hours=48)
    )

    overdue_spares_7days = service.spare_parts.filter(
        status__in=['assigned', 'not_returned'],
        assigned_at__lt=timezone.now() - timedelta(days=7)
    )


    # ---------- CONTEXT ----------
    context = {
        'service': service,
        'order': order,
        'order_item': order_item,
        'customer': customer,
        'order_creator': order_creator,

        'logs': service.service_logs.order_by('created_at'),
        'is_engineer': is_engineer,
        'is_dealer': is_dealer,
        'is_admin': is_admin,
        'spares': service.spare_parts.all(),
        'can_edit_status': can_edit_status,
        'machine_blocked': machine_blocked,
        'overdue_spares_48': overdue_spares_48,
        'overdue_spares_7days': overdue_spares_7days,
        'has_assigned_spares': has_assigned_spares,
        'is_service_final': is_service_final,
    }

    return render(request, 'services/admin/service_detail.html', context)

# Inventory Dashboard View
@role_required('employee:inventory')
def inventory_dashboard(request):
    return render(request, 'erp/inventory/inventory_dashboard.html')

# Dispatch Dashboard View
@role_required('employee:dispatch')
def dispatch_dashboard(request):
    return render(request,'erp/dispatch/dispatch_dashboard.html')