from datetime import timedelta
from django.utils import timezone
from django.db import models
from accounts.models import User
from erp.models import Order, OrderItem
# Create your models here.

class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('raised','Raised'),
        ('assigned','Assigned'),
        ('waiting_spare','Waiting for Spare'),
        ('in_progress','In Progress'),
        ('completed','Completed'),
        ('closed','closed'),
    ]
    APPROVAL_CHOICES = [
        ('pending','Pending'),
        ('approved','Approved'),
        ('rejected','Rejected'),
    ]

    PAYMENT_MODES = [
        ('cash','Cash'),
        ('upi','UPI'),
        ('card','Card'),
        ('bank transfer','Bank Transfer'),
    ]

    # who raise the request (employee/ dealer)
    raised_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_requests')
    # order = models.ForeignKey( Order, on_delete=models.PROTECT, related_name='services', null=True, blank=True )
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='services',
        null=True,
        blank=True
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.PROTECT,
        related_name='service_requests',
        null=True,
        blank=True
    )
    # Customer details (can be auto-filled from order or manually entered)
    full_name = models.CharField(max_length=150, blank=True, null=True)
    company_name = models.CharField(max_length=150, blank=True, null=True) 
    gstin = models.CharField(max_length=50, blank=True, null=True) 
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Product Details
    product_name = models.CharField(max_length=150)
    product_model = models.CharField(max_length=100)
    product_serial = models.CharField(max_length=100)
    purchase_date = models.DateField(blank=True, null=True)
    
    # Issue/Problem in machine
    issue_desc = models.TextField()
    issue_image = models.ImageField(upload_to='service/images/',blank=True)
    issue_video = models.FileField(upload_to='service/videos/',blank=True)

    # admin control fields
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='raised')

    assigned_engineer = models.ForeignKey(User, on_delete=models.SET, related_name='assigned_engineer', blank=True, null=True)

    warranty = models.BooleanField(default=False)
    proof_of_warranty = models.FileField(upload_to='service/warranty/', blank=True, null=True)
    payment_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_MODES,
        null=True,
        blank=True
    )
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)

    # Tracking service
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_updates'
    )
    def is_locked(self):
        return self.approval_status == 'rejected'

    def is_machine_blocked(self):
        if self.status != 'closed':
            return False
        return ServiceSparePart.objects.filter(
            service_request__product_serial=self.product_serial,
            status__in=['assigned', 'not_returned'],
            returned_at__isnull=True,
            service_request__closure__closed_at__lt=timezone.now() - timedelta(days=7)
        ).exists()

    @property
    def customer(self):
        """
        Returns the Order object which contains customer details
        """
        return self.order

    def __str__(self):
        if self.product_model:
            return f" SR-{self.id} | {self.product_model} {self.product_name} | {self.status}"
        return f" SR-{self.id} | {self.product_name} | {self.status}"
    
# for multi status stages of spare part request
class SparePartRequest(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'), 
        ('requested', 'Requested'),
        ('dispatched', 'Dispatched'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='spare_requests'
    )

    requested_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'sub_employee_role': 'service'}
    )

    part_name = models.CharField(max_length=255)
    part_number = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Admin dispatch info
    courier_partner = models.CharField(max_length=100, blank=True, null=True)
    docket_number = models.CharField(max_length=100, blank=True, null=True)
    dispatched_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(blank=True, null=True)

class SparePartReturn(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='spare_returns'
    )

    engineer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'sub_employee_role': 'service'}
    )
    part_name = models.CharField(max_length=255, blank=True, null=True)
    part_number = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    remark = models.TextField(blank=True, null=True)

    courier_partner = models.CharField(max_length=100)
    docket_number = models.CharField(max_length=100)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='submitted'
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(blank=True, null=True)

# for spare parts assigned to service requests
class ServiceSparePart(models.Model):
    PART_STATUS = (
        ('assigned', 'Assigned'),
        ('returned', 'Returned'),
        ('not_returned', 'Not Returned'),
    )

    service_request = models.ForeignKey(
        ServiceRequest, on_delete=models.CASCADE, related_name='spare_parts'
    )

    part_name = models.CharField(max_length=150)
    part_number = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=PART_STATUS,
        default='assigned'
    )

    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    # cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def is_overdue_72hr(self):
        return self.status == 'assigned' and timezone.now() > self.assigned_at + timedelta(hours=72)

    def is_overdue_7days(self):
        return self.status != 'returned' and timezone.now() > self.assigned_at + timedelta(days=7)

class ServiceLog(models.Model):
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE,related_name='service_logs')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class ServiceClosure(models.Model):
    service_request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name='closure')
    resolution_summary = models.TextField()
    engineer_remark = models.CharField(blank=True, null=True)
    closed_by = models.ForeignKey(User, models.SET_NULL, null=True, related_name='closed_service')
    closed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Closure for {self.service_request.id}"
    
class ServiceAttachment(models.Model):
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to='service/attachment/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

class ServiceStatusHistory(models.Model):
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=25)
    new_status = models.CharField(max_length=25)

    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

class ServiceFeedback(models.Model):
    service_request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name="feedback")
    rating = models.PositiveSmallIntegerField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

