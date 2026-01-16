from django import forms
from django.utils import timezone
from .models import ServiceRequest
from erp.models import OrderItem
from accounts.models import Dealer

class ServiceRequestForm(forms.ModelForm):
    order_item = forms.ModelChoiceField(
        queryset=OrderItem.objects.none(),
        label='Select delivered product',
        required=True
    )

    purchase_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'max': timezone.now().date()
            }
        )
    )

    class Meta:
        model = ServiceRequest
        fields = [
            'order_item',
            'product_serial',
            'purchase_date',
            'issue_desc',
            'issue_image',
            'issue_video'
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

        # Add CSS classes
        for field in self.fields.values():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs.update({'class': css})

        order_filter = {'order__status': 'delivered'}

        # Filter based on user role
        if self.user.role == 'dealer':
            try:
                dealer = self.user.dealer_profile
                order_filter['order__dealer'] = dealer
            except Dealer.DoesNotExist:
                self.fields['order_item'].queryset = OrderItem.objects.none()
                return

        elif self.user.role == 'employee' and self.user.sub_employee_role == 'sales':
            order_filter['order__created_by'] = self.user

        elif self.user.role == 'employee' and self.user.sub_employee_role == 'service':
            order_filter['order__created_by'] = self.user

        elif self.user.role == 'admin':
            order_filter['order__created_by'] = self.user

        else:
            self.fields['order_item'].queryset = OrderItem.objects.none()
            return

        self.fields['order_item'].queryset = (
            OrderItem.objects
            .filter(**order_filter)
            .select_related('order', 'product')
        )
        self.fields['order_item'].label_from_instance = self.order_item_label

    def order_item_label(self, obj):
        product = obj.product
        if product.product_model:
            return f"{product.name} ({product.product_model})"
        return product.name

    def clean_product_serial(self):
        serial = self.cleaned_data.get('product_serial')
        if ServiceRequest.objects.filter(product_serial__iexact=serial).exists():
            raise forms.ValidationError(
                "Service request already exists for this product serial number."
            )
        return serial

    def save(self, commit=True):
        instance = super().save(commit=False)
        order_item = self.cleaned_data['order_item']

        instance.order = order_item.order
        instance.product_name = order_item.product.name
        instance.product_model = order_item.product.product_model
        instance.raised_by = self.user

        if commit:
            instance.save()
        return instance
