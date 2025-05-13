"""
URL configuration for concrete_mix_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Django admin site
    path('accounts/', include('allauth.urls')),  # Django-allauth URLs
    path('select2/', include('django_select2.urls')),  # Django-select2 URLs
    
    # Original concrete_mix_app URLs (using original database)
    path('', include('concrete_mix_app.urls')),  # Original app URLs at root
    
    # New CDB app URLs (using improved database schema)
    path('cdb/', include('cdb_app.urls')),  # New app URLs under /cdb/ prefix
]
