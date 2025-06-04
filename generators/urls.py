from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('invoice/', views.invoice, name='invoice'),
    path('generate-invoice/', views.invoice, name='generate_invoice'),
]
