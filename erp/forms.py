from django import forms 
from .models import Product, Stock, Order, OrderItem
from django.utils.text import slugify
from django.forms import inlineformset_factory
from accounts.models import Dealer

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        exclude = ['slug']   # IMPORTANT

        widgets ={
            'name':forms.TextInput(attrs={'class':'form-control'}),
            'product_model':forms.TextInput(attrs={'class':'form-control'}),
            'category':forms.TextInput(attrs={'class':'form-control'}),
            'price':forms.NumberInput(attrs={'class':'form-control'}),''
            'img':forms.ClearableFileInput(attrs={'class':'form-control'}),
            # 'desc':forms.Textarea(attrs={'class':'form-control','rows':3}),
            
        }
        

    def save(self, commit=True):
        product = super().save(commit=False)

        if not product.slug:
            base_slug = slugify(product.product_model or product.name)
            slug = base_slug
            counter = 1

            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            product.slug = slug

        if commit:
            product.save()

        return product

class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['current_quantity', 'min_stock_level', 'new_stock_shippment', 'total_stock', 'location']


class OrderForm(forms.ModelForm):
    # checkbox for telling billing is same as shipping
    billing_same_as_shipping =forms.BooleanField(
        required=False,
        label='Billing is same as shipping'
    )  

    class Meta:
        model = Order
        exclude = [       
        'created_by',
        'sales_person',
        'status',
        'sub_total',
        'tax_total',
        'grand_total',
        'order_date',
        ]
        
        widgets={ 
            'full_name': forms.TextInput(attrs={'class':'form-control','placeholder':'full name'}),
            'phone':forms.TextInput(attrs={'class':'form-control','placeholder':'phone'}),
            'email': forms.EmailInput(attrs={'class':'form-control','placeholder':'email'}),
            'company_name':forms.TextInput(attrs={'class':'form-control','placeholder':'company name'}),
            'gstin': forms.TextInput(attrs={'class':'form-control','placeholder':'GSTIN'}),
            'payment_mode':forms.Select(attrs={'class':'form-control form-select'}),
            'bill_building':forms.TextInput(attrs={'class':'form-control','placeholder':'billing address'}),
            'bill_city': forms.TextInput(attrs={'class':'form-control','placeholder':'billing city'}),
            'bill_state':forms.TextInput(attrs={'class':'form-control','placeholder':'billing state'}),
            'bill_zip':forms.NumberInput(attrs={'class':'form-control','placeholder':'billing pincode'}),
            'bill_country':forms.TextInput(attrs={'class':'form-control','placeholder':'billing country'}),
            'shipp_building':forms.TextInput(attrs={'class':'form-control','placeholder':'shipping address'}),
            'shipp_city': forms.TextInput(attrs={'class':'form-control','placeholder':'shipping city'}),
            'shipp_state':forms.TextInput(attrs={'class':'form-control','placeholder':'shipping state'}),
            'shipp_zip':forms.NumberInput(attrs={'class':'form-control','placeholder':'shipping pincode'}),
            'shipp_country':forms.TextInput(attrs={'class':'form-control','placeholder':'shipping country'}),
        }


    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user',None)
        super().__init__(*args, **kwargs)
        required_fields = [
            'full_name','phone','email','company_name','gstin','payment_mode',
            'shipp_building','shipp_city','shipp_state','shipp_zip','shipp_country',
            'bill_building','bill_city','bill_state','bill_zip','bill_country',
        ]

        for field in required_fields:
            self.fields[field].required = True

        if user and user.role == 'dealer':
            self.fields.pop('dealer')

        # Sales + Admin CAN select dealer
        if user and user.role in ['employee', 'admin']:
            self.fields['dealer'].queryset = Dealer.objects.filter(is_active=True)
            self.fields['dealer'].label_from_instance = (
                lambda obj: f"{obj.get_full_name()} | {obj.user.email}"
            )

        if 'dealer' in self.fields:
            self.fields['dealer'].label_from_instance = (
                        lambda obj: f"{obj.get_full_name()} | {obj.user.email}"
                )
        for name, field in self.fields.items():

            # Checkbox → different class
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.setdefault('class', 'form-control form-select')
    

class OrderItemForm(forms.ModelForm):
    product = forms.ModelChoiceField(queryset=Product.objects.all(), empty_label='select product',widget=forms.Select(attrs={'class':'form-control'}))
    qty = forms.IntegerField(
        initial=1,
        min_value=1,
        widget=forms.NumberInput(attrs={'min':1,'class':'form-control'})
    )
    class Meta:
        model = OrderItem
        fields =[
            'product','qty'
        ]
       
OrderItemFormSet = inlineformset_factory(Order, OrderItem, form=OrderItemForm, extra=0, can_delete=True)