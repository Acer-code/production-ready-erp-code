from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product, Stock

@receiver(post_save, sender=Product)
def create_stock_for_new_product(sender, instance, created, **kwargs):
    if created:
        Stock.objects.get_or_create(product=instance, defaults={'total_stock':0})


 