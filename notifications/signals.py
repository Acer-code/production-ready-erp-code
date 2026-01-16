
from django.db.models.signals import post_save
from django.dispatch import receiver
from services.models import ServiceRequest
from erp.models import Product, Stock, Order
from accounts.models import User
from .utils import create_notification
from .recipients import admins_and_directors, all_except_dealers, dispatch_team, service_team

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
# @receiver(post_save, sender=ServiceRequest)
# def service_request_notification(sender, instance, created, **kwargs):
#     text = f"Service request raised for {instance.product_model} by {user_display(instance.requested_by)}"
#     create_notification(
#         service_team(),
#         title="Service Request",
#         message=text,
#         n_type="service",
#         url=f"/service/{instance.id}/"
#     )


@receiver(post_save, sender=ServiceRequest)
def service_request_notification(sender, instance, created, **kwargs):
    """
    Notify relevant users in-app when a new service request is raised.
    """
    if created:
        service_request = instance

        # Message text
        text = f"Service request raised for {service_request.product_model or ''} {service_request.product_name} by {user_display(service_request.raised_by)}"

        # Notify all service team members (admins, directors, maybe engineers)
        create_notification(
            users=service_team(),
            title="New Service Request",
            message=f"New service request {service_request.id} raised",
            n_type="service_request",
            url=f"/service/{service_request.id}/"
        )


        # Optionally notify dealer who raised request
        if service_request.raised_by.role == 'dealer':
            create_notification(
                users=[service_request.raised_by],  # put the user in a list
                title="Service Request Raised",
                message=f"Your service request SR-{service_request.id} has been successfully raised.",
                n_type="service",
                url=f"/service/{service_request.id}/"
        )


# ----------------------------
# Stock Notifications
# ----------------------------
@receiver(post_save, sender=Stock)
def stock_notification(sender, instance, created, **kwargs):
    product_name = instance.product.name
    model_name = getattr(instance.product, 'product_model', '')
    model_text = f" ({model_name})" if model_name else ""

    # Low Stock
    if instance.is_low_stock():
        text = f"{product_name}{model_text} stock is low ({instance.current_quantity})"
        create_notification(
            all_except_dealers(),
            title="Low Stock Alert",
            message=text,
            n_type="stock",
            url="/inventory/products/"
        )

    # Stock Updated
    if not created:
        text = f"{product_name}{model_text} stock updated to {instance.current_quantity}"
        create_notification(
            all_except_dealers(),
            title="Stock Updated",
            message=text,
            n_type="stock",
            url="/inventory/products/"
        )

# ----------------------------
# Product Notifications
# ----------------------------
@receiver(post_save, sender=Product)
def product_notification(sender, instance, created, **kwargs):
    product_name = instance.name
    model_name = getattr(instance, 'product_model', '')
    model_text = f" ({model_name})" if model_name else ""

    if created:
        text = f"New product added: {product_name}{model_text}"
        create_notification(
            all_except_dealers(),
            title="New Product Added",
            message=text,
            n_type="product",
            url="/products/"
        )
        # Automatically create Stock record if missing
        Stock.objects.get_or_create(product=instance)
    else:
        text = f"Product updated: {product_name}{model_text}"
        create_notification(
            all_except_dealers(),
            title="Product Updated",
            message=text,
            n_type="product",
            url="/products/"
        )

# ----------------------------
# Order Notifications
# ----------------------------
@receiver(post_save, sender=Order)
def order_notification(sender, instance, created, **kwargs):
    order_id = instance.id
    if created:
        text = f"New order received: Order #{order_id}"
        create_notification(
            dispatch_team(),
            title="New Order",
            message=text,
            n_type="order",
            url=f"/orders/{order_id}/"
        )
    else:
        text = f"Order #{order_id} updated. Status: {instance.status}"
        create_notification(
            dispatch_team(),
            title="Order Status Updated",
            message=text,
            n_type="order",
            url=f"/orders/{order_id}/"
        )

# ----------------------------
# User Notifications
# ----------------------------
@receiver(post_save, sender=User)
def user_notification(sender, instance, created, **kwargs):
    display = user_display(instance)
    if created:
        text = f"New user registered: {display}"
        create_notification(
            admins_and_directors(),
            title="New User Created",
            message=text,
            n_type="user",
            url="/users/"
        )
    else:
        text = f"User updated: {display}"
        create_notification(
            admins_and_directors(),
            title="User Updated",
            message=text,
            n_type="user",
            url="/users/"
        )
