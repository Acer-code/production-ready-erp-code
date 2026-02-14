from django.urls import path
from .views import (
    approve_reject_service, order_item_api, service_dashboard, service_list,service_detail,assign_service_engineer, change_service_status, close_service,
    raise_service_request,engineer_dashboard,
    # remove_spare_part,update_spare_part_status,add_spare_parts, 
    request_spare_parts,
    dispatch_spare_part,receive_spare_part,submit_spare_return,approve_spare_return,order_item_api
)

urlpatterns =[
    path('engineer/dashboard',engineer_dashboard,name='engineer_dashboard'),
    path('service/dashboard',service_dashboard,name='service_dashboard'),
    path('raise-request/',raise_service_request, name='raise_service'),

    path('api/order-item/<int:pk>/', order_item_api,name='order_item_api'),

    path('service-list/', service_list, name='service_list'),
    path('service/service-detail/de088?dwe/<int:pk>/099sdsd?mk', service_detail, name='service_detail'),
    path('service/assign-service-engineer/a0dsod?0e/<int:pk>/eo093?o34', assign_service_engineer, name='assign_service_engineer'),
    path('service/change-status/sev0834i/<int:pk>/0045oi3', change_service_status, name='change_service_status'),
    # path('add-spare-parts/io098sd23/<int:pk>/08jsd08/', add_spare_parts, name='add_spare_parts'),
    # path('update-spare-part-status/io098sd23/<int:spare_id>/08jsd08/', update_spare_part_status, name='update_spare_part_status'),

    path('service/closed/<int:pk>', close_service, name='close_service'),
  
    # path('service/remove-spare/<int:service_id>/-034 sdf032 4ft?34z /<int:spare_id>/oewq 2dd3e3?df3/', remove_spare_part, name='remove_spare_part'),

    # =========================
    # SPARE PART REQUEST FLOW (ENGINEER → ADMIN)
    # =========================
    path('<int:service_id>/spare/request/', request_spare_parts,  name='request_spare_parts'),

    path('spare/request/<int:request_id>/dispatch/', dispatch_spare_part, name='dispatch_spare_part'),

    path('spare/request/<int:request_id>/receive/', receive_spare_part, name='receive_spare_part'),

    # =========================
    # SPARE PART RETURN FLOW (ENGINEER → ADMIN)
    # =========================
    path('<int:service_id>/spare/return/',  submit_spare_return, name='submit_spare_return'),

    path('spare/return/<int:return_id>/approve/', approve_spare_return, name='approve_spare_return'),
    path('service/<int:pk>/approve-reject/', approve_reject_service, name='approve_reject_service'),


]