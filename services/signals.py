from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SparePart, ServiceSparePart, SparePartStock


# AUTO CREATE STOCK WHEN NEW SPARE PART IS CREATED
@receiver(post_save, sender=SparePart)
def create_spare_stock(sender, instance, created, **kwargs):

    if created:
        SparePartStock.objects.create(
            spare_part=instance,
            current_quantity=0,
            total_stock=0,
            min_stock_level=5
        )

# REDUCE STOCK WHEN SPARE IS ASSIGNED TO ENGINEER
@receiver(post_save, sender=ServiceSparePart)
def reduce_inventory_stock(sender, instance, created, **kwargs):

    if created and instance.status == "received":

        stock = SparePartStock.objects.filter(
            spare_part=instance.spare_part
        ).first()

        if stock:
            stock.current_quantity -= instance.quantity
            stock.save()


# INCREASE STOCK WHEN SPARE IS RETURNED
@receiver(post_save, sender=ServiceSparePart)
def increase_inventory_stock(sender, instance, **kwargs):

    if instance.status == "returned":

        stock = SparePartStock.objects.filter(
            spare_part=instance.spare_part
        ).first()

        if stock:
            stock.current_quantity += instance.quantity
            stock.save()
            