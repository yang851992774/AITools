from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/check-env', views.check_environment, name='check_environment'),
    path('api/check-device', views.check_device, name='check_device'),
    path('api/upload', views.upload_file, name='upload_file'),
    path('api/install', views.install_file, name='install_file'),
    path('api/download-xapk', views.download_xapk_file, name='download_xapk_file'),
    path('api/download-progress', views.get_download_progress, name='get_download_progress'),
    path('api/install-xapk', views.install_xapk_file, name='install_xapk_file'),
    path('api/list-xapk', views.list_xapk_files, name='list_xapk_files'),
    path('api/delete-xapk', views.delete_xapk_file, name='delete_xapk_file'),
]

