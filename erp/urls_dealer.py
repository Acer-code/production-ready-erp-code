from django.urls import path
from .views_dealer import (
    dealer_dashboard, dealer_order_history,edit_own_dealer_profile
)

urlpatterns =[
        # Dealer
    path('edit-profile/',edit_own_dealer_profile, name='edit_dealer_profile'),
    path('dashboard/', dealer_dashboard, name ='dealer_dashboard'),
    # path('order/order-detail/O03  dse?4-04 /<int:pk>/0o9 32hc 32e2', dealer_order_detail,name='vendor_order_detail'),
    path('order/order-history', dealer_order_history, name = 'dealer_order_history'),
    # path('order/create-order/', dealer_create_order, name='vendor_create_order'),
]