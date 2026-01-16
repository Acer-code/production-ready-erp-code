from django import forms
from django.contrib.auth.forms import UserCreationForm
from accounts.models import User


class CreateUserForm(UserCreationForm):
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    company = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    role = forms.ChoiceField(
        required=True, 
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control form-select mb-3'})
    )

    sub_employee_role = forms.ChoiceField(
        choices=User.SUB_EMPLOYEE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-select'})
    )

    password1 = forms.CharField(
        required=True, 
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        required=True, 
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'company', 'role', 'sub_employee_role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['role'].choices = [('', '---------')] + list(self.fields['role'].choices)
        self.fields['sub_employee_role'].choices = [('', '---------')] + list(self.fields['sub_employee_role'].choices)    

    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        role= cleaned_data.get('role')
        sub_role = cleaned_data.get('sub_employee_role')

        if role == 'employee' and not sub_role:
            self.add_error(
                'sub_employee_role',
                'Sub employee role is required when role is Employee'
            )


        if password1:
            if password2:
                if password1 != password2:
                    raise forms.ValidationError('Passwords do not match!')
        return cleaned_data


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    # role = forms.ChoiceField(choices = User.ROLE_CHOICES, widget = forms.Select(attrs={'class':'form-control'}))
    # sub_employee_role = forms.ChoiceField(required=False,choices = User.SUB_EMPLOYEE_CHOICES, widget = forms.Select(attrs={'class':'form-control'}))
    # email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control','placeholder':'Email'}))
    # password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Password'}))

    # class Meta:
    #     model = User
    #     fields = '__all__'

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)

    #     self.fields['role'].choices = [('', 'select-role')] + list(self.fields['role'].choices)
    #     self.fields['sub_employee_role'].choices = [('', 'sub employee role')] + list(self.fields['sub_employee_role'].choices)    

    
