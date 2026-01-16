from django.contrib import admin
from .models import User, Dealer

# Register your models here.
admin.site.register(Dealer)
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display =('first_name','last_name','role','email','phone','company')