"""
URL配置
"""
from django.urls import path
from . import views

urlpatterns = [
    path('generate-preview/', views.generate_preview, name='generate_preview'),
    path('generate-pdf/', views.generate_pdf, name='generate_pdf'),
]
