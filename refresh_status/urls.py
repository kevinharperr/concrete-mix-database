from django.urls import path
from . import views

app_name = 'refresh_status'

urlpatterns = [
    path('', views.StatusPageView.as_view(), name='status'),
    path('admin/', views.AdminStatusView.as_view(), name='admin_status'),
    path('api/update/', views.update_status, name='update_status'),
    path('api/status/', views.get_status_json, name='get_status_json'),
]
