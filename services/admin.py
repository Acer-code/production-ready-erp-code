from django.contrib import admin
from .models import ServiceRequest,ServiceLog,ServiceSparePart,ServiceClosure,ServiceAttachment,ServiceStatusHistory,ServiceFeedback,SparePartReturn,SparePartRequest
# Register your models here.

admin.site.register(ServiceRequest)
admin.site.register(ServiceLog)
admin.site.register(ServiceSparePart)
admin.site.register(ServiceClosure)
admin.site.register(ServiceAttachment)
admin.site.register(ServiceStatusHistory)
admin.site.register(ServiceFeedback)
admin.site.register(SparePartRequest)
admin.site.register(SparePartReturn)