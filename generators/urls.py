from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('invoice/', views.invoice, name='invoice'),
    path('generate-invoice/', views.invoice, name='generate_invoice'),
    path('salary-slip/', views.salary_slip, name='salary_slip'),
    path('generate-salary-slip/', views.salary_slip, name='generate_salary_slip'),
]
