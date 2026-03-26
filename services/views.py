from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from erp.decorators import role_required
from .models import (
    SparePart, SparePartReturn, SparePartRequest,
    ServiceRequest, ServiceSparePart,ServiceAttachment,
    ServiceClosure,ServiceFeedback,ServiceLog,ServiceStatusHistory, SparePartStock
)
from accounts.models import User
from django.http import HttpResponseForbidden
from .forms import ServiceRequestForm, SparePartForm
from erp.models import OrderItem, Product
from django.utils import timezone
from datetime import timedelta
from django.db.models import F, Q
from django.db import transaction
from erp.pagination import paginate_queryset
import traceback

# Create your views here.
# =========================

@role_required('employee:engineer')
def request_spare_parts(request, service_id):

    service = get_object_or_404(
        ServiceRequest,
        pk=service_id,
        assigned_engineer=request.user
    )

    if service.approval_status == 'rejected':
        messages.error(request,"This service request is rejected and locked.")
        return redirect(request.META.get('HTTP_REFERER'))

    if request.method != 'POST':
        return HttpResponseForbidden()

    part_names = request.POST.getlist('part_name')
    part_numbers = request.POST.getlist('part_number')
    quantities = request.POST.getlist('quantity')

    if not part_names:
        messages.error(request, "Please select at least one spare part.")
        return redirect(request.META.get('HTTP_REFERER'))

    added = False

    try:
        with transaction.atomic():

            for name, number, qty in zip(part_names, part_numbers, quantities):

                if not name or not qty:
                    continue

                spare = SparePart.objects.filter(part_name=name).first()

                if not spare:
                    continue

                if SparePartRequest.objects.filter(
                    service_request=service,
                    spare_part=spare,
                    status__in=['draft', 'requested']
                ).exists():
                    continue

                SparePartRequest.objects.create(
                    service_request=service,
                    requested_by=request.user,
                    spare_part=spare,
                    part_number=number,
                    quantity=int(qty),
                    status='requested'
                )

                added = True

            if not added:
                raise ValueError("No valid spare parts were added.")

            if service.status == 'assigned':
                old_status = service.status
                service.status = 'waiting_spare'
                service.updated_by = request.user
                service.save(update_fields=['status', 'updated_by'])

                ServiceStatusHistory.objects.create(
                    service_request=service,
                    old_status=old_status,
                    new_status='waiting_spare',
                    changed_by=request.user
                )

    except Exception as e:
        messages.error(request, str(e))
        return redirect(request.META.get('HTTP_REFERER'))

    messages.success(request, "Spare parts requested successfully.")
    return redirect(request.META.get('HTTP_REFERER'))

# REQUEST SPARE PARTS (ENGINEER)
# @role_required('employee:engineer')
# def request_spare_parts(request, service_id):
#     service = get_object_or_404(
#         ServiceRequest,
#         pk=service_id,
#         assigned_engineer=request.user
#     )

#     # =========================
#     # START: BLOCK REJECTED SERVICE
#     # =========================
#     if service.approval_status == 'rejected':
#         messages.error(request, "This service request is rejected and is locked. No further actions are allowed.")
#         return redirect(request.META.get('HTTP_REFERER'))
#     # =========================
#     # END: BLOCK REJECTED SERVICE

#     if request.method != 'POST':
#         return HttpResponseForbidden()

#     part_names = request.POST.getlist('part_name')
#     part_numbers = request.POST.getlist('part_number')
#     quantities = request.POST.getlist('quantity')

#     if not part_names:
#         messages.error(request, "Please add at least one spare part.")
#         return redirect(request.META.get('HTTP_REFERER'))

#     added = False

#     for i in range(len(part_names)):
#         name = part_names[i].strip()
#         qty = quantities[i]

#         if not name or not qty:
#             continue

#         # PREVENT DUPLICATE (draft + requested)
#         if SparePartRequest.objects.filter(
#             service_request=service,
#             part_name__iexact=name,
#             status__in=['draft', 'requested']
#         ).exists():
#             messages.warning(
#                 request,
#                 f"Spare '{name}' already added."
#             )
            
#             continue

#         # CREATE AS REQUESTED (IMPORTANT FIX)
#         SparePartRequest.objects.create(
#             service_request=service,
#             requested_by=request.user,
#             part_name=name,
#             part_number=part_numbers[i],
#             quantity=int(qty),
#             status='requested'
#         )

#         added = True

#     if not added:
#         messages.error(request, "No valid spare parts were added.")
#         return redirect(request.META.get('HTTP_REFERER'))

#     # UPDATE SERVICE STATUS ONLY ONCE
#     if service.status == 'assigned':
#         old_status = service.status
#         service.status = 'waiting_spare'
#         service.updated_by = request.user
#         service.save(update_fields=['status', 'updated_by'])

#         ServiceStatusHistory.objects.create(
#             service_request=service,
#             old_status=old_status,
#             new_status='waiting_spare',
#             changed_by=request.user
#         )

#     messages.success(request, "Spare parts requested successfully.")
#     return redirect(request.META.get('HTTP_REFERER'))

@role_required('admin', 'employee:service')
def dispatch_spare_part(request, request_id):
    spare_request = get_object_or_404(
    SparePartRequest,
    pk=request_id,
    status='requested'
    )
    service = spare_request.service_request

    # =========================
    # START: BLOCK REJECTED SERVICE
    # =========================
    if service.approval_status == 'rejected':
        messages.error(request, "This service request is rejected and is locked. No further actions are allowed.")
        return redirect(request.META.get('HTTP_REFERER'))
    # =========================
    # END: BLOCK REJECTED SERVICE

    # if request.method == 'POST':
    #     spare_request.courier_partner = request.POST.get('courier_partner')
    #     spare_request.docket_number = request.POST.get('docket_number')
    #     spare_request.status = 'dispatched'
    #     spare_request.dispatched_at = timezone.now()
    #     spare_request.save()

    #     messages.success(request, "Spare part dispatched to engineer")
    #     return redirect(request.META.get('HTTP_REFERER'))

    if request.method == 'POST':

        spare_request.courier_partner = request.POST.get('courier_partner')
        spare_request.docket_number = request.POST.get('docket_number')

        spare = spare_request.spare_part
        stock = spare.sparepartstock

        required_qty = spare_request.quantity
        current_stock = stock.current_quantity

        # Case 1: No stock
        if current_stock == 0:
            messages.error(
                request,
                f"{spare.part_name} is out of stock. Dispatch not allowed."
            )
            return redirect(request.META.get('HTTP_REFERER'))

        # Case 2: Stock less than required
        if current_stock < required_qty:
            messages.error(
                request,
                f"Only {current_stock} units of {spare.part_name} available. "
                f"Requested quantity is {required_qty}."
            )
            return redirect(request.META.get('HTTP_REFERER'))

        # Case 3: Enough stock → deduct
        stock.current_quantity -= required_qty
        stock.save()

        spare_request.status = 'dispatched'
        spare_request.dispatched_at = timezone.now()
        spare_request.save()

        messages.success(request, "Spare part dispatched successfully.")
        return redirect(request.META.get('HTTP_REFERER'))

    return HttpResponseForbidden()

@role_required('employee:engineer')
def receive_spare_part(request, request_id):
    spare_request = get_object_or_404(
        SparePartRequest,
        pk=request_id,
        requested_by=request.user
    )
    service = spare_request.service_request
    old_status=service.status

    # =========================
    # START: BLOCK REJECTED SERVICE
    # =========================
    if service.approval_status == 'rejected':
        messages.error(request, "Cannot receive spares for rejected service request.")
        return redirect(request.META.get('HTTP_REFERER'))

    if spare_request.status != 'dispatched':
        messages.error(request, "Spare part not yet dispatched")
        return redirect(request.META.get('HTTP_REFERER'))

    with transaction.atomic():
        spare_request.status = 'received'
        spare_request.save()

        service = spare_request.service_request
        if service.status == 'waiting_spare':
            service.status = 'in_progress'
            service.updated_by = request.user
            service.save(update_fields=['status', 'updated_by'])

            ServiceStatusHistory.objects.create(
            service_request=service,
            old_status=old_status,
            new_status='in_progress',
            changed_by=request.user
            )

        # Create actual ServiceSparePart record
        ServiceSparePart.objects.create(
            service_request=spare_request.service_request,
            part_name=spare_request.spare_part.part_name,
            part_number=spare_request.spare_part.part_number,
            quantity=spare_request.quantity,
            status='assigned',
            assigned_at=timezone.now()
        )
        # ServiceSparePart.objects.create(
        #     service_request=spare_request.service_request,
        #     part_name=spare_request.part_name,
        #     part_number=spare_request.part_number,
        #     quantity=spare_request.quantity,
        #     status='assigned',
        #     assigned_at=timezone.now()
        # )

    messages.success(request, "Spare part received successfully")
    return redirect(request.META.get('HTTP_REFERER'))

@role_required('employee:engineer')
def submit_spare_return(request, service_id):
    service = get_object_or_404(
        ServiceRequest,
        pk=service_id,
        assigned_engineer=request.user
    )
    # =========================
    if service.approval_status == 'rejected':
        messages.error(request, "Rejected service request cannot submit spare return.")
        return redirect(request.META.get('HTTP_REFERER'))
    # =========================
    #  allow only after completed / closed
    if service.status not in ['completed', 'closed']:
        messages.error(request, "Service must be completed before returning spares.")
        return redirect(request.META.get('HTTP_REFERER'))

    if request.method == 'POST':
        SparePartReturn.objects.create(
            service_request=service,
            engineer=request.user,
            part_name=request.POST.get('part_name'),
            part_number=request.POST.get('part_number'),
            quantity=request.POST.get('quantity'),
            remark=request.POST.get('remark'),
            courier_partner=request.POST.get('courier_partner'),
            docket_number=request.POST.get('docket_number'),
            status ='pending'
        )

        messages.success(request, "Spare return submitted for admin approval")
        return redirect(request.META.get('HTTP_REFERER'))

    return HttpResponseForbidden()

@role_required('admin','employee:service')
def approve_spare_return(request, return_id):
    spare_return = get_object_or_404(SparePartReturn, pk=return_id)
    service = spare_return.service_request
    # =========================
    if service.approval_status == 'rejected':
        messages.error(request, "Rejected service request cannot submit spare return.")
        return redirect(request.META.get('HTTP_REFERER'))
    
    # =========================
    if request.method == 'POST':
        decision = request.POST.get('decision')

        # if decision == 'approve':
        #     spare_return.status = 'approved'
        #     spare_return.approved_at = timezone.now()

        #     # Update spare parts
        #     spare_return.service_request.spare_parts.filter(
        #         status='assigned'
        #     ).update(
        #         status='returned',
        #         returned_at=timezone.now()
        #     )
        if decision == 'approve':

            spare_return.status = 'approved'
            spare_return.approved_at = timezone.now()

            spare = SparePart.objects.filter(
                part_name=spare_return.part_name
            ).first()

            if spare:
                stock = spare.sparepartstock
                stock.current_quantity += int(spare_return.quantity)
                stock.save()

            spare_return.service_request.spare_parts.filter(
                status='assigned'
            ).update(
                status='returned',
                returned_at=timezone.now()
            )

        else:
            spare_return.status = 'rejected'

        spare_return.save()

        messages.success(request, "Spare return status updated")
        return redirect(request.META.get('HTTP_REFERER'))

    return HttpResponseForbidden()

# =========================
@role_required('employee:engineer')
def engineer_dashboard(request):
    user = request.user

    #================= METRICS =================

    open_service_requests = ServiceRequest.objects.filter(
        assigned_engineer=user
    ).exclude(status='closed').count()

    assigned_services = ServiceRequest.objects.filter(
        assigned_engineer=user
    ).exclude(status='closed').count()

    closed_services = ServiceRequest.objects.filter(
        assigned_engineer=user,
        status='closed'
    ).count()

    context = {
        'closed_services':closed_services,
        'open_service_requests': open_service_requests,
        'assigned_services': assigned_services,
    }

    return render(request, 'services/engineer_dashboard.html', context)

@role_required('dealer', 'employee:service', 'employee:sales', 'admin')
def raise_service_request(request):
    if request.method == 'POST':
        serial_no = request.POST.get('product_serial')

        # Check block: any spare part not returned after 7 days
        blocked_spares = ServiceSparePart.objects.filter(
            service_request__product_serial=serial_no,
            status__in=['assigned', 'not_returned'],
            service_request__closure__closed_at__lt=timezone.now()  - timedelta(days=7)
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

                    ServiceStatusHistory.objects.create(
                        service_request=service_request,
                        old_status='raised',
                        new_status='raised',
                        changed_by=request.user
                    )

                messages.success(request, "Service request raised successfully.")
                return redirect('service_list')

            except Exception as e:
                # Show the actual error
                messages.error(
                    request,
                    f"Service request failed: {str(e)}"
                )
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

def order_item_api(request, pk):
    item = get_object_or_404(OrderItem, pk=pk)
    order = item.order

    return JsonResponse({
        'product_name': item.product.name,
        'product_model': item.product.product_model,
        'full_name': order.full_name,
        'company_name': order.company_name,
        'gstin': order.gstin,
        'phone': order.phone,
        'purchase_date': order.order_date.strftime('%Y-%m-%d') if order.order_date else ''
    })
# =========================
# SERVICE LIST 
# =========================
@role_required('admin', 'director', 'dealer', 'employee:service', 'employee:engineer', 'employee:sales')
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
        # Sales person → services raised by them
        services = ServiceRequest.objects.all()

    elif user.role == 'employee' and user.sub_employee_role == 'engineer':
        # Engineer person → ONLY services assigned to them
        services = ServiceRequest.objects.filter(assigned_engineer=user)

    else:
        services = ServiceRequest.objects.none()

    status = request.GET.get('status')
    engineer = request.GET.get('engineer')
    approve_reject_service = request.GET.get('approve_reject_service')
    if status:
        services = services.filter(status=status)

    if engineer:
        services = services.filter(assigned_engineer_id=engineer)

    if approve_reject_service:
        services = services.filter(approval_status=approve_reject_service)

    engineers = User.objects.filter(
        role='employee',
        sub_employee_role='engineer'
    )


    services = services.order_by('-created_at', '-id')
    page_obj = paginate_queryset(request, services, 10)

    return render(
        request,
        'services/admin/service_list.html',
        {'services': page_obj,'page_obj':page_obj, 'engineers': engineers}
    )

# =========================
# ASSIGN / REASSIGN ENGINEER
# =========================
@role_required('admin', 'employee:service')
def assign_service_engineer(request, pk):
    service = get_object_or_404(ServiceRequest, pk=pk)
    engineers = User.objects.all().filter(role='employee',sub_employee_role = 'engineer')
    # =========================
    if service.approval_status == 'rejected':
        messages.error(request, "Rejected service request cannot submit spare return.")
        return redirect(request.META.get('HTTP_REFERER'))
    
    # =========================
    if request.method == 'POST':
        engineer_id = request.POST.get('engineer_id')
        engineer = get_object_or_404(User, pk = engineer_id)
        service.assigned_engineer = engineer
        old_status=service.status
        service.status = 'assigned'
        service.save()

        ServiceLog.objects.create(
            service_request = service,
            updated_by = request.user,
            note = f"Engineer {engineer.get_full_name()} assigned"
        )
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
@role_required('admin','employee:engineer')
def change_service_status(request, pk):
    service = get_object_or_404(ServiceRequest, pk=pk)
    # =========================
    if service.approval_status == 'rejected':
        messages.error(request, "Rejected service request cannot submit spare return.")
        return redirect(request.META.get('HTTP_REFERER'))
    # =========================

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

        # Engineers can complete or close
        if request.user.sub_employee_role != 'engineer' and new_status in ['completed', 'closed']:
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
        if new_status == 'completed':
            service.spare_parts.filter(status='assigned').update(
                status='assigned',
                returned_at=timezone.now()
            )

        service.status = new_status
        service.updated_by = request.user
        service.save()

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
# CLOSE SERVICE (FINAL)
# =========================  

@role_required('admin', 'employee:engineer')
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
    # =========================
    if service.approval_status == 'rejected':
        messages.error(request, "Rejected service request cannot submit spare return.")
        return redirect(request.META.get('HTTP_REFERER'))
    # =========================

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
        old_status=service.status
        service.status = 'closed'
        service.updated_by = user
        service.save(update_fields=['status', 'updated_by'])
       
        ServiceStatusHistory.objects.create(
            service_request=service,
            old_status=old_status,
            new_status='closed',
            changed_by=user
        )
        # AUTO UPDATE SPARE PARTS
        service.spare_parts.filter(
            status='assigned'
        ).update(
            status='assigned',
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
@role_required('admin', 'director', 'dealer', 'employee:service','employee:engineer', 'employee:sales')
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
        service = get_object_or_404(ServiceRequest, pk=pk)

    elif user.role == 'employee' and user.sub_employee_role == 'engineer':
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

    # ---------- SPARE REQUESTS (ALL) ----------
    spare_requests = service.spare_requests.all().order_by('created_at')


    # ---------- FLAGS ----------
    is_engineer = user.role == 'employee' and user.sub_employee_role == 'engineer'
    is_service = user.role == 'employee' and user.sub_employee_role == 'service'
    is_dealer = user.role == 'dealer'
    is_admin = user.role in ['admin', 'director']


    can_edit_status = is_engineer or is_service or is_admin

    has_assigned_spares = service.spare_parts.filter(status='assigned').exists()
    is_service_final = service.status in ['completed', 'closed']

    returnable_spares_exist = service.spare_parts.filter(
    status='assigned'
    ).exists()

    # ---------- SPARE & BLOCK STATUS ----------
    machine_blocked = service.is_machine_blocked()

    overdue_spares_72 = service.spare_parts.filter(
        status='assigned',
        service_request__closure__closed_at__lt=timezone.now() - timedelta(hours=72)
    )

    overdue_spares_7days = service.spare_parts.filter(
        status='assigned',
        service_request__closure__closed_at__lt=timezone.now() - timedelta(days=7)
    )
    status_flow = ['raised', 'assigned', 'waiting_spare', 'in_progress', 'completed', 'closed']

    # Prepare mapping for template
    status_logs = {}
    for status in status_flow:
        log = service.status_history.filter(new_status=status).order_by('changed_at').first()
        status_logs[status] = log

    # ---------- SPARE PART INVENTORY (FOR DROPDOWN) ----------
    spare_parts = SparePart.objects.select_related(
    'sparepartstock'
    ).filter(
        sparepartstock__current_quantity__gt=0
    ).order_by('part_name')
    # ---------- CONTEXT ----------
    context = {
        'service': service,
        'order': order,
        'order_item': order_item,
        'customer': customer,
        'order_creator': order_creator,
        'spare_parts':spare_parts,
        'logs': service.service_logs.order_by('created_at'),
        'is_engineer': is_engineer,
        'is_dealer': is_dealer,
        'is_admin': is_admin,
        'is_service': is_service,
        'spares': service.spare_parts.all(),
        'can_edit_status': can_edit_status,
        'machine_blocked': machine_blocked,
        'overdue_spares_72': overdue_spares_72,
        'overdue_spares_7days': overdue_spares_7days,
        'has_assigned_spares': has_assigned_spares,
        'is_service_final': is_service_final,
        'spare_requests': spare_requests,
        'returnable_spares_exist': returnable_spares_exist,
        'status_logs': status_logs,
    }

    return render(request, 'services/admin/service_detail.html', context)

# Approve or Reject Service
@role_required('admin', 'employee:service')
def approve_reject_service(request, pk):
    service = get_object_or_404(ServiceRequest, pk=pk)

    # Only admin or service team can approve/reject
    if not (request.user.role == 'admin' or request.user.sub_employee_role == 'service'):
        messages.error(request, "You are not allowed to approve or reject service requests.")
        return redirect('service_detail', pk=pk)

    #  Prevent re-approval / re-rejection
    if service.approval_status != 'pending':
        messages.warning(request, "This service request is already processed.")
        return redirect('service_detail', pk=pk)

    if request.method == 'POST':
        decision = request.POST.get('approval_status')
        reason = request.POST.get('rejection_reason')

        # Only allow valid decisions
        if decision not in ['approved', 'rejected']:
            messages.error(request, "Invalid approval action.")
            return redirect('service_detail', pk=pk)
        
        #  REQUIRED reason only for rejection
        if decision == 'rejected' and not reason:
            messages.error(request, "Rejection reason is required.")
            return redirect('service_detail', pk=pk)

        service.approval_status = decision

        # If rejected, save rejection reason
        if decision == 'rejected':
            service.rejection_reason = reason
            messages.error(request, "Service request rejected.")
        else:
            service.rejection_reason = ""
            messages.success(request, "Service request approved successfully.")

        # Track who updated (optional audit)
        service.updated_by = request.user
        service.save()

    return redirect('service_detail', pk=pk)

# Service Dashboard
@role_required('employee:service')
def service_dashboard(request):
    # ================= METRICS =================
    total_services = ServiceRequest.objects.count()

    open_service_requests = ServiceRequest.objects.exclude(status='closed').count()

    assigned_services = ServiceRequest.objects.exclude(status='closed').count()

    context = {
        'total_services': total_services,
        'open_service_requests': open_service_requests,
        'assigned_services': assigned_services,
    }

    return render(request, 'services/service_dashboard.html', context)

# Spare Part List 
@role_required('employee:service', 'admin', 'director')
def sparepart_list(request):

    search_query = request.GET.get("q")
    status = request.GET.get("status")

    # Base queryset
    stocks = SparePartStock.objects.select_related("spare_part").all()

    # Search
    if search_query:
        stocks = stocks.filter(
            Q(spare_part__part_name__icontains=search_query) |
            Q(spare_part__part_number__icontains=search_query)
        )

    # Status Filter
    if status == "low":
        stocks = stocks.filter(
            current_quantity__lte=F("min_stock_level"),
            current_quantity__gt=0
        )

    elif status == "out":
        stocks = stocks.filter(current_quantity=0)

    elif status == "ok":
        stocks = stocks.filter(
            current_quantity__gt=F("min_stock_level")
        )

    # Get related spare parts
    spare_parts = SparePart.objects.filter(
        id__in=stocks.values_list("spare_part_id", flat=True)
    ).order_by("-id")

    # Pagination
    page_obj = paginate_queryset(request, spare_parts, 10)

    return render(
        request,
        "services/admin/sparepart_list.html",
        {
            "spare_parts": page_obj,
            "page_obj": page_obj,
            "search_query": search_query,
            "status": status
        }
    )

# @role_required('employee:service', 'admin','director')
# def sparepart_list(request):

#     stock_status = request.GET.get('stock_status')

#     spare_parts = SparePart.objects.select_related().all()

#     stocks = SparePartStock.objects.select_related('spare_part')

#     if stock_status == 'in':
#         stocks = stocks.filter(
#             current_quantity__gt=F('min_stock_level')
#         )

#     elif stock_status == 'low':
#         stocks = stocks.filter(
#             current_quantity__lte=F('min_stock_level'),
#             current_quantity__gt=0
#         )

#     elif stock_status == 'out':
#         stocks = stocks.filter(current_quantity=0)

#     spare_parts = spare_parts.filter(
#         id__in=stocks.values_list('spare_part_id', flat=True)
#     ).order_by('-id')

#     page_obj = paginate_queryset(request, spare_parts, 10)

#     return render(
#         request,
#         "services/admin/sparepart_list.html",
#         {
#             "spare_parts": page_obj,
#             "page_obj": page_obj,
#             "stock_status": stock_status
#         }
#     )

# ADD SPARE PART
@role_required('employee:service','admin')
def add_spare_part(request):

    if request.method == "POST":

        part_name = request.POST.get("part_name")
        part_number = request.POST.get("part_number")
        price = request.POST.get("price")
        SparePart.objects.create(
            part_name=part_name,
            part_number=part_number,
            price=price,
        )

        messages.success(request, "Spare part added successfully")

    return redirect("sparepart_list")


# UPDATE SPARE PART
@role_required('employee:service','admin')
def update_spare_part(request, id):

    spare = get_object_or_404(SparePart, id=id)

    if request.method == "POST":

        spare.part_name = request.POST.get("part_name")
        spare.part_number = request.POST.get("part_number")
        spare.price = request.POST.get("price")

        spare.save()

        messages.success(request, "Spare part updated successfully")

    return redirect("sparepart_list")


# DELETE SPARE PART
@role_required('employee:service','admin')
def delete_spare_part(request, id):

    spare = get_object_or_404(SparePart, id=id)

    spare.delete()

    messages.success(request, "Spare part deleted successfully")

    return redirect("sparepart_list")

# Spare Part Inventory
@role_required('employee:service','admin','director')
def spare_inventory(request):

    status = request.GET.get("status")
    search_query = request.GET.get("q")
    stocks = SparePartStock.objects.select_related("spare_part").all()

    # Search Bar
    if search_query:
        stocks = stocks.filter(
            Q(spare_part__part_name__icontains=search_query) |
            Q(spare_part__part_number__icontains=search_query)
        )

    # Search Filter (Dropdown)
    if status == "low":
        stocks = stocks.filter(
            current_quantity__lte=models.F("min_stock_level"),
            current_quantity__gt=0
        )

    elif status == "out":
        stocks = stocks.filter(current_quantity=0)

    elif status == "ok":
        stocks = stocks.filter(
            current_quantity__gt=models.F("min_stock_level")
        )

    low_stocks = SparePartStock.objects.filter(
        current_quantity__lte=models.F("min_stock_level")
    )

    context = {
        "stocks": stocks,
        "low_stocks": low_stocks,
        "low_stock_count": low_stocks.count(),
        "search_query":search_query,
    }

    return render(request,"services/admin/spare_inventory.html",context)

# Update Inventory
@role_required('employee:service','admin')
def update_spare_inventory(request,id):

    stock = get_object_or_404(SparePartStock,id=id)

    if request.method == "POST":

        new_shipment = int(request.POST.get("new_stock_shippment",0))

        stock.new_stock_shipment = new_shipment
        stock.location = request.POST.get("location")

        stock.save()

        messages.success(request,"Inventory updated successfully")

    return redirect("spare_inventory")


