from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Dealer

@receiver(post_save, sender=User)
def create_dealer_profile(sender, instance, created, **kwargs):
    if created and instance.role == 'dealer':
        Dealer.objects.create(user = instance, firm_name=instance.company or "")