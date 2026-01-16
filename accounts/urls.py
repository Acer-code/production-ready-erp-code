from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns =[
    #authentication
    path('',views.user_login, name='login'),
    path('logout',views.user_logout,name='logout'),

    # reset password
    path('forget-password/', auth_views.PasswordResetView.as_view(template_name='accounts/forget_password.html'),name='password_reset'),
    path('reset-password-sent/', auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_sent.html'),name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'),name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'),name='password_reset_complete'),

]