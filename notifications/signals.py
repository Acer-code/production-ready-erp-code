
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from services.models import ServiceRequest
from erp.models import Product, Stock, Order
from accounts.models import User
from .utils import create_notification
from .recipients import admins_and_directors, dispatch_team, inventory_team, product_notification_users, stock_notification_users
from django.core.mail import send_mail
from accounts.models import User
from django.conf import settings

# Helper for user display
def user_display(user):
    if user.role != 'employee':
        return f"{user.first_name} {user.last_name} ({user.role})"
    elif user.sub_employee_role:
        return f"{user.first_name} {user.last_name} ({user.sub_employee_role})"
    else:
        return f"{user.first_name} {user.last_name}"

# ----------------------------
# Service Request Notifications
# ----------------------------
@receiver(post_save, sender=ServiceRequest)
def service_created_notification(sender, instance, created, **kwargs):
    if not created:
        return

    # Admin & Director always
    recipients = set(admins_and_directors())

    # Sales employee who raised it
    if instance.raised_by.role == "employee" and instance.raised_by.sub_employee_role == "sales":
        recipients.add(instance.raised_by)

    # Dealer who raised it
    if instance.raised_by.role == "dealer":
        recipients.add(instance.raised_by)

    create_notification(
        users=recipients,
        title="Service Request Raised",
        message=f"Service request #{instance.id} raised by {user_display(instance.raised_by)}",
        n_type="service",
        url=f"/service/{instance.id}/"
    )

# Signal for assignment change
@receiver(pre_save, sender=ServiceRequest)
def service_assignment_notification(sender, instance, **kwargs):
    if not instance.pk:
        return

    old = ServiceRequest.objects.get(pk=instance.pk)

    if old.assigned_engineer != instance.assigned_engineer and instance.assigned_engineer:
        create_notification(
            users=[instance.assigned_engineer],
            title="Service Assigned",
            message=f"Service #{instance.id} has been assigned to you",
            n_type="service",
            url=f"/service/{instance.id}/"
        )

# Signal for status change
@receiver(pre_save, sender=ServiceRequest)
def service_status_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    old = ServiceRequest.objects.get(pk=instance.pk)

    if old.status != instance.status:
        recipients = set(admins_and_directors())

        # Sales / Dealer who raised it
        recipients.add(instance.raised_by)

        # Assigned engineer
        if instance.assigned_engineer:
            recipients.add(instance.assigned_engineer)

        create_notification(
            users=recipients,
            title="Service Status Updated",
            message=f"Service #{instance.id} status changed from {old.status} → {instance.status}",
            n_type="service",
            url=f"/service/{instance.id}/"
        )


# ----------------------------
# Stock Notifications
# ----------------------------
@receiver(post_save, sender=Stock)
def stock_notifications(sender, instance, created, **kwargs):
    product_name = instance.product.name

    model_name = instance.product.product_model or ""
    model_text = f" ({model_name})" if model_name else ""
    if instance.is_low_stock():
        create_notification(
            users=stock_notification_users(),
            title="Low Stock Alert",
            message=f"{product_name}{model_text} stock is low",
            n_type="stock",
            url="/inventory/"
        )

    if not created:
        create_notification(
            users=stock_notification_users(),
            title="Stock Updated",
            message=f"{product_name}{model_text} stock updated",
            n_type="stock",
            url="/inventory/"
        )


# ----------------------------
# Product Notifications
# ----------------------------
@receiver(post_save, sender=Product)
def product_notifications(sender, instance, created, **kwargs):
    product_name = instance.name
    model_name = getattr(instance, 'product_model', '')
    model_text = f" ({model_name})" if model_name else ""
    text = f"New product added: {product_name}{model_text}" if created else f"Product updated: {product_name}{model_text}"
    create_notification(
        users=product_notification_users(),
        title="Product Added" if created else "Product Updated",
        message=text,
        n_type="product",
        url="/products/"
    )

# ----------------------------
# Order Notifications
# ----------------------------
@receiver(post_save, sender=Order)
def order_created_notification(sender, instance, created, **kwargs):
    if not created:
        return

    recipients = set(dispatch_team())
    recipients.update(admins_and_directors())

    # Creator (sales or dealer)
    if instance.created_by:
        recipients.add(instance.created_by)

    create_notification(
        users=recipients,
        title="New Order Created",
        message=f"Order #{instance.id} created",
        n_type="order",
        url=f"/orders/{instance.id}/"
    )

@receiver(pre_save, sender=Order)
def order_status_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    old = Order.objects.get(pk=instance.pk)

    if old.status != instance.status:
        recipients = set(dispatch_team())
        recipients.update(admins_and_directors())

        # Dealer
        if instance.dealer and instance.dealer.user:
            recipients.add(instance.dealer.user)

        # Sales creator
        if instance.created_by:
            recipients.add(instance.created_by)

        create_notification(
            users=recipients,
            title="Order Status Updated",
            message=f"Order #{instance.id} status changed from {old.status} → {instance.status}",
            n_type="order",
            url=f"/orders/{instance.id}/"
        )

# ----------------------------
# User Notifications
# ----------------------------
@receiver(post_save, sender=User)
def user_created_notification(sender, instance, created, **kwargs):
    if created:
        create_notification(
            admins_and_directors(),
            title="New User Created",
            message=f"New user registered: {user_display(instance)}",
            n_type="user",
            url="/users/"
        )

@receiver(pre_save, sender=User)
def user_profile_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    old = User.objects.get(pk=instance.pk)

    tracked_fields = ["first_name", "last_name", "email", "role", "sub_employee_role"]

    if any(getattr(old, f) != getattr(instance, f) for f in tracked_fields):
        create_notification(
            admins_and_directors(),
            title="User Profile Updated",
            message=f"User profile updated: {user_display(instance)}",
            n_type="user",
            url="/users/"
        )

