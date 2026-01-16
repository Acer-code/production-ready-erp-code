from django.contrib import admin
from .models import Product, Stock, Order, OrderItem, Dispatch

# Register your models here.

# admin.site.register(Product)
admin.site.register(Stock)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Dispatch)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display=('name', 'product_model', 'price')
    prepopulated_fields={'slug':('name','product_model')}