from django.db import models
from accounts.models import User, Dealer

# Create your models here.

#############################################################

# Product & Inventory Start
class Product(models.Model):
    TAX_RATE = [
        (18,'18%'),
        (12,'12%'),
        (5,'5%'),
    ]
    name= models.CharField(max_length=200,blank=False)
    product_model = models.CharField(max_length =20, blank=True, null=True)
    category = models.CharField(max_length=150, blank=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=5, decimal_places=2, default=18, choices=TAX_RATE)
    img = models.ImageField(upload_to='product/images/')
    # desc = models.TextField(blank=True)
    slug = models.SlugField(unique=True)


    def __str__(self):
        if self.product_model:
            return f"{self.product_model} ({self.name})"
        else:
            return self.name
# Product & Inventory End

# Stock Start
class Stock(models.Model):
    product= models.OneToOneField(Product, on_delete=models.CASCADE)
    min_stock_level = models.PositiveIntegerField(default=10)
    new_stock_shippment = models.PositiveIntegerField(default=0)
    total_stock = models.PositiveIntegerField(default=0)   
    # DISPLAY / FILTER FIELD (persistent)
    last_shipment_qty = models.PositiveIntegerField(default=0)
    current_quantity = models.PositiveIntegerField(default=0)
    location = models.CharField(max_length=100, default="ABM Warehouse")

    def is_low_stock(self):
        return self.current_quantity <= self.min_stock_level
    
    # def save(self, *args, **kwargs):
    #     if self._state.adding:
    #         self.current_quantity = self.total_stock
    #     super().save(*args, **kwargs)

    # def __str__(self):
    #     return f"{self.product.name} - {self.total_stock}"
    def save(self, *args, **kwargs):
        if self.pk:  
            # existing stock → add new shipment
            self.total_stock = self.current_quantity + self.new_stock_shippment
            self.current_quantity = self.total_stock
            self.last_shipment_qty = self.new_stock_shippment
        else:
            # first time creation
            self.total_stock = self.new_stock_shippment
            self.current_quantity = self.total_stock
            self.last_shipment_qty = self.new_stock_shippment

        # reset shipment so it doesn't re-add next save
        self.new_stock_shippment = 0

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.current_quantity}"
# Stock End

# Order Start
class Order(models.Model):
    ORDER_STATUS =[
        ('pending','Pending'),
        ('approved','Approved'),
        ('rejected','Rejected'),
        ('dispatched','Dispatched'), 
        ('delivered','Delivered'),
    ]
    PAYMENT_MODES = [
        ('cash','Cash'),
        ('upi','UPI'),
        ('card','Card'),
        ('bank transfer','Bank Transfer'),
    ]

    dealer = models.ForeignKey(Dealer, on_delete=models.SET_NULL, null=True, blank=True, related_name='dealer_orders', limit_choices_to={'user__role':'dealer'})
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders', null=True, blank=True)

    sales_person = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='sales_orders'
    )
    full_name = models.CharField(max_length=255,blank=True)
    phone = models.CharField(max_length=10,blank=True)
    email= models.EmailField(blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    gstin = models.CharField(max_length=15,blank=True)

    # courier details
    courier = models.CharField(max_length=100,blank=True,null=True)
    tracking_number = models.CharField(max_length=100,blank=True,null=True)

    # Shipping address
    shipp_building = models.CharField(max_length=255,blank=True)
    shipp_city = models.CharField(max_length=100,blank=True)
    shipp_state = models.CharField(max_length=100,blank=True)
    shipp_zip = models.CharField(max_length=6,blank=True)
    shipp_country = models.CharField(max_length=100, default='india')
    # Billing address
    bill_building = models.CharField(max_length=255, blank=True)
    bill_city = models.CharField(max_length=100, blank=True)
    bill_state = models.CharField(max_length=100, blank=True)
    bill_zip = models.CharField(max_length=6, blank=True)
    bill_country = models.CharField(max_length=100, default='india', blank=True)

    order_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    payment_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_MODES,
        null=True,
        blank=True
    )
    # Storing Total 
    sub_total = models.DecimalField(max_digits=12, decimal_places=2,default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2,default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def calculate_totals(self):
        sub_total = sum(item.base_amount for item in self.items.all())
        tax_total = sum(item.gst_amount for item in self.items.all())

        self.sub_total = sub_total
        self.tax_total = tax_total
        self.grand_total = sub_total + tax_total
        self.save(update_fields=['sub_total','tax_total','grand_total'])
    
    
    @property
    def creator_display(self):
        """
        Returns a dictionary with creator info for template rendering.
        """
        if not self.created_by:
            return None

        user = self.created_by

        # Dealer
        if user.role == 'dealer' and hasattr(user, 'dealer_profile'):
            dealer = user.dealer_profile
            return {
                'type': 'Dealer',
                'name': f"{user.first_name} {user.last_name}",
                'company': dealer.firm_name,
                'phone': user.phone,
                'email': user.email,
                'gstin': dealer.gst_number,
            }

        # Sales Employee
        if user.role == 'employee' and user.sub_employee_role == 'sales':
            return {
                'type': 'Sales',
                'name': f"{user.first_name} {user.last_name}",
                'company': user.company,
                'phone': user.phone,
                'email': user.email,
            }

        # Admin/Director
        return {
            'type': user.role.title(),
            'name': f"{user.first_name} {user.last_name}",
            'company': user.company,
            'phone': user.phone,
            'email': user.email,
        }

    @property
    def creator_summary(self):
        """
        Simple string for template display
        """
        display = self.creator_display
        if not display:
            return "System generated"
        return f"{display['type']} - {display['name']} ({display.get('company', '')})"


    def __str__(self):
        return f"{self.id} - {self.full_name}"
    
    def save(self, *args, **kwargs):
        if self.pk:
            old_order = Order.objects.get(pk=self.pk)
            if old_order.status != 'rejected' and self.status == 'rejected':
                # restore stock for all other orders
                for item in self.items.all():
                    stock =Stock.objects.get(product=item.product)
                    stock.current_quantity += item.qty
                    stock.save()
        super().save(*args, **kwargs)
 
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.PositiveBigIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2,blank=True,default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2,blank=True,default=0)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    @property
    def final_unit_price(self):
        return self.unit_price - self.discount
    
    @property
    def base_amount(self):
        return self.qty * self.final_unit_price

    @property
    def gst_amount(self):
        return self.base_amount * (self.gst_rate/100)
    
    @property
    def total_amount(self):
        return self.base_amount + self.gst_amount

    def __str__(self):
        return f"{self.product.name} x {self.qty}"

# Order End

# SERVICE REQUEST MODEL End

# DISPACTH MODEL START
class Dispatch(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    courier_name = models.CharField(max_length=150)
    tracking_no = models.CharField(max_length=200)
    dispatch_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"dispatch for Order #{self.order.id}"

# DISPACTH MODEL END


