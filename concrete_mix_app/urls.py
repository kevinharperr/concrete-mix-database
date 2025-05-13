# concrete_mix_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views # Import views from the current app
from . import api_views

# Set up the API router
router = DefaultRouter()
router.register(r'materials', api_views.MaterialViewSet)
router.register(r'references', api_views.BibliographicReferenceViewSet)
router.register(r'mixes', api_views.ConcreteMixViewSet)
router.register(r'compositions', api_views.MixCompositionViewSet)
router.register(r'performance', api_views.PerformanceResultViewSet)

# Define the app name for namespacing
app_name = 'concrete_mix_app'

urlpatterns = [
    # Dashboard view at the root URL for this app
    path('', views.dashboard, name='dashboard'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),

    # Material URLs
    path('materials/', views.material_list_view, name='material_list'),
    path('materials/add/', views.add_material, name='add_material'),
    path('materials/<int:pk>/', views.material_detail, name='material_detail'),
    path('materials/<int:pk>/edit/', views.edit_material_view, name='edit_material'),
    path('materials/<int:pk>/delete/', views.delete_material_view, name='delete_material'),

    # Concrete Mix URLs
    path('mixes/', views.mix_list_view, name='mix_list'),
    path('mixes/add/', views.add_mix, name='add_mix'),
    path('mixes/<int:pk>/', views.mix_detail, name='mix_detail'),
    path('mixes/<int:pk>/edit/', views.edit_mix_view, name='edit_mix'),
    path('mixes/<int:pk>/delete/', views.delete_mix_view, name='delete_mix'),
    
    # Mix Composition URLs
    path('mixes/<int:mix_pk>/composition/add/', views.add_composition_view, name='add_composition'),
    path('mixes/<int:mix_pk>/composition/<int:comp_pk>/edit/', views.edit_composition_view, name='edit_composition'),
    path('mixes/<int:mix_pk>/composition/<int:comp_pk>/delete/', views.delete_composition_view, name='delete_composition'),
    
    # Performance Result URLs
    path('mixes/<int:mix_pk>/performance/<int:perf_pk>/edit/', views.edit_performance_result_view, name='edit_performance_result'),
    path('mixes/<int:mix_pk>/performance/<int:perf_pk>/delete/', views.delete_performance_result_view, name='delete_performance_result')
]
