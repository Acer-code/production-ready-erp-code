from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
# Create your models here.
from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)
    
class User(AbstractUser):
    ROLE_CHOICES =[
        ('admin','Admin'),
        ('director','Director'),
        ('employee','Employee'),
        ('dealer','Dealer'),
    ]
    SUB_EMPLOYEE_CHOICES=[
        ('sales', 'Sales'),
        ('service','Service'),
        ('engineer','Engineer'),
        ('inventory', 'Inventory'),
        ('dispatch', 'Dispatch'),
    ]
    
    username= None
    email = models.EmailField(unique=True)

    role = models.CharField(max_length=20,choices=ROLE_CHOICES)
    sub_employee_role = models.CharField(max_length=20,choices=SUB_EMPLOYEE_CHOICES, blank=True, null=True)
    # email = models.EmailField()
    phone = models.CharField(max_length=10,blank=True)
    company = models.CharField(max_length=100,blank=True)
    is_suspended = models.BooleanField(default=False)

    USERNAME_FIELD = "email"             # LOGIN USING EMAIL
    REQUIRED_FIELDS = []                 # No username required
    objects = UserManager()

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = f"{self.first_name}_{self.last_name}".lower()
        super().save(*args,**kwargs)

    def __str__(self):
        return self.email


class Dealer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dealer_profile')

    # Dealer specific details 
    firm_name = models.CharField(max_length=255)
    gst_number = models.CharField(max_length=15, null=True, blank=True)
    pan_number = models.CharField(max_length=10, null=True, blank=True)
    # Billing Address
    bill_address_line1 = models.CharField(max_length=255)
    bill_address_line2 = models.CharField(max_length=255, blank=True, null=True)
    bill_city = models.CharField(max_length=100)
    bill_state = models.CharField(max_length=100)
    bill_pincode = models.CharField(max_length=6)
    bill_country = models.CharField(max_length=50, default='India')

    # Shipping Address
    ship_address_line1 = models.CharField(max_length=255)
    ship_address_line2 = models.CharField(max_length=255, blank=True, null=True)
    ship_city = models.CharField(max_length=100)
    ship_state = models.CharField(max_length=100)
    ship_pincode = models.CharField(max_length=6)
    ship_country = models.CharField(max_length=50, default='India')

    credit_limit = models.DecimalField(decimal_places=2,max_digits=12, default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.user.role != 'dealer':
            raise ValueError('Dealer profile can only be created for dealer users!')
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    def __str__(self):
        return f"{self.firm_name} - {self.user.email}"
