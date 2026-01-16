from django.urls import path
from .views import (
    update_order_tracking,
    order_detail,update_order_status,delete_user,edit_user,create_user,create_order,inventory_list, 
    update_inventory_stock, add_product, edit_product, delete_product,admin_dashboard, user_list, 
    product_list, order_list,sales_dashboard
)
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    # Admin URLs Start
    path('admin/dashboard/',admin_dashboard, name='admin_dashboard'),
    path('user/create-new/', create_user, name='create_user'),
    path('user/update/<int:pk>',edit_user, name='edit_user'),
    path('user/delete/<int:pk>', delete_user, name='delete_user'),
    path('users/',user_list, name='user_list'),

    # Product Urls
    path('add-product/',add_product, name='add_product'),
    path('edit-product/edit/<slug:slug>/0ofp df?09ds/', edit_product, name='edit_product'),
    path('delete/<slug:slug>', delete_product, name='delete_product'),
    path('products/',product_list, name='product_list'),
    # Product Urls End

    # Inventory Urls Start
    path('inventory/', inventory_list, name='inventory_list'),
    path('inventory/update/<int:pk>/', update_inventory_stock, name='update_inventory_stock'),
    # Inventory Urls End

    path('orders/',order_list,name='order_list'),
    path('orders/create-new/', create_order, name='create_order'),
    path('orders/update-status/<int:pk>', update_order_status, name='update_order_status'),
    path('orders/order-detail/od0-5? dpw /<int:id>/094fd 43df?', order_detail, name='order_detail'),
    path('orders/O0r8 der?932/<int:pk>/update-tracking/',update_order_tracking, name='update_order_tracking'),

    # SALES
    path('dashboard/',sales_dashboard, name = 'sales_dashboard')


] +static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


