from django import forms
from django.utils import timezone
from .models import ServiceRequest, SparePartStock
from erp.models import OrderItem
from accounts.models import Dealer
from dal import autocomplete
from .models import SparePart

class ServiceRequestForm(forms.ModelForm):

    order_item = forms.ModelChoiceField(
        queryset=OrderItem.objects.none(),
        label='Select delivered product',
        required=False
    )

    # NEW: allow manual entry if no order selected
    purchase_date = forms.DateField(
        required=False,
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
            'product_name',
            'product_model',
            'product_serial',
            'full_name',
            'company_name',
            'gstin',
            'phone',
            'purchase_date',
            'payment_mode',
            'warranty',
            'proof_of_warranty',
            'issue_desc',
            'issue_image',
            'issue_video'
        ]
        widgets = {
            'spare_part': autocomplete.ModelSelect2(
                url='spare-part-autocomplete'
            )
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['product_model'].required = False
        required_fields = [
            'product_name',
            'product_serial',
            'full_name',
            'company_name',
            'phone',
        ]

        for field in required_fields:
            self.fields[field].required = True

        # CSS 
        for name, field in self.fields.items():
            if field.widget.__class__ == forms.CheckboxInput:
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
                field.widget.attrs.update({'class': css})

        # Hide payment mode initially
        # self.fields['payment_mode'].widget.attrs['style'] = 'display:none'

        order_filter = {'order__status': 'delivered'}

        # Role-based filtering (UNCHANGED)
        if self.user.role == 'dealer':
            try:
                dealer = self.user.dealer_profile
                order_filter['order__dealer'] = dealer
            except Dealer.DoesNotExist:
                self.fields['order_item'].queryset = OrderItem.objects.none()
                return

        elif self.user.role == 'employee' and self.user.sub_employee_role in ['sales', 'service']:
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

    # Custom dropdown label (UNCHANGED)
    def order_item_label(self, obj):
        order = obj.order
        product = obj.product

        customer = (
            order.company_name
            or order.full_name
        )
        order_date = order.order_date.strftime('%d-%b-%Y') if order.order_date else ''

        return (
            f"Order #{order.id} | "
            f"{product.name}"
            f"{f' ({product.product_model})' if product.product_model else ''} | "
            f"{customer} | "
            f"{order_date}"
        )

    # Serial duplication check (UNCHANGED)
    def clean_product_serial(self):
        serial = self.cleaned_data.get('product_serial')

        if not serial:
            return serial

        active_service_exists = ServiceRequest.objects.filter(
            product_serial__iexact=serial
        ).exclude(status='closed').exists()

        if active_service_exists:
            raise forms.ValidationError(
                "Service request already raised for this product. "
                "Please close the existing service before creating a new one."
            )
        return serial

    #validation
    def clean(self):
        data = super().clean()

        if not data.get('order_item'):
            required_fields = ['product_name', 'product_model', 'product_serial', 'full_name', 'phone']
            for f in required_fields:
                if not data.get(f):
                    self.add_error(f, "This field is required when no delivered product is selected.")

        if not data.get('warranty'):
      
            if not data.get('payment_mode'):
                raise forms.ValidationError("Payment mode is required for non-warranty service.")

        return data
    

    # Save logic (extended, not replaced)
    def save(self, commit=True):
        instance = super().save(commit=False)
        order_item = self.cleaned_data.get('order_item')

        if order_item:
            instance.order = order_item.order
            instance.product_name = order_item.product.name
            instance.product_model = order_item.product.product_model

        instance.raised_by = self.user

        if commit:
            instance.save()
        return instance


class SparePartForm(forms.ModelForm):

    class Meta:
        model = SparePart
        fields = [
            "part_name",
            "part_number",
            "price"
        ]
class SparePartStockForm(forms.ModelForm):
    class Meta:
        model = SparePartStock
        fields = ['current_quantity', 'min_stock_level', 'new_stock_shipment', 'total_stock', 'location']
