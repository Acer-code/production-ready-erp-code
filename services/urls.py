from django.urls import path
from .views import (
    service_list,service_detail,assign_service_engineer, change_service_status, add_spare_parts, close_service,
    raise_service_request,service_dashboard,remove_spare_part, dispatch_dashboard, inventory_dashboard,update_spare_part_status
)

urlpatterns =[
    path('dashboard',service_dashboard,name='service_dashboard'),
    path('raise-request/',raise_service_request, name='raise_service'),
    path('service-list/', service_list, name='service_list'),
    path('service/service-detail/de088?dwe/<int:pk>/099sdsd?mk', service_detail, name='service_detail'),
    path('service/assign-service-engineer/a0dsod?0e/<int:pk>/eo093?o34', assign_service_engineer, name='assign_service_engineer'),
    path('service/change-status/sev0834i/<int:pk>/0045oi3', change_service_status, name='change_service_status'),
    path('add-spare-parts/io098sd23/<int:pk>/08jsd08/', add_spare_parts, name='add_spare_parts'),
    path('update-spare-part-status/io098sd23/<int:spare_id>/08jsd08/', update_spare_part_status, name='update_spare_part_status'),

    path('service/closed/<int:pk>', close_service, name='close_service'),
  
    path('service/remove-spare/<int:service_id>/-034 sdf032 4ft?34z /<int:spare_id>/oewq 2dd3e3?df3/', remove_spare_part, name='remove_spare_part'),

    path('dispatch/dashboard',dispatch_dashboard, name='dispatch_dashboard'),
    path('inventory/dashboard',inventory_dashboard, name ='inventory_dashboard'),


]