from django.urls import path
from .views_director import director_dashboard

urlpatterns=[
    path('director/dashboard/', director_dashboard, name='director_dashboard'),
]