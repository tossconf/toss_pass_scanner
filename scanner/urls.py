from django.urls import path
from . import views

urlpatterns = [
    path('', views.scan_view, name='scan'),
    path('api/scan', views.process_qr, name='process_qr'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]
