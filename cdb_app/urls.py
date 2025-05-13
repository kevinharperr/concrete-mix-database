# cdb_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api_views

# Set up the API router
router = DefaultRouter()
router.register(r'materials', api_views.MaterialViewSet)
router.register(r'references', api_views.BibliographicReferenceViewSet)
router.register(r'mixes', api_views.ConcreteMixViewSet)
router.register(r'components', api_views.MixComponentViewSet)
router.register(r'performance', api_views.PerformanceResultViewSet)
router.register(r'datasets', api_views.DatasetViewSet)
router.register(r'sustainability', api_views.SustainabilityMetricsViewSet)

# Define the app name for namespacing
app_name = 'cdb_app'

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
    
    # Mix Component URLs
    path('mixes/<int:mix_pk>/component/add/', views.add_component_view, name='add_component'),
    path('mixes/<int:mix_pk>/component/<int:comp_pk>/edit/', views.edit_component_view, name='edit_component'),
    path('mixes/<int:mix_pk>/component/<int:comp_pk>/delete/', views.delete_component_view, name='delete_component'),
    
    # Performance Result URLs
    path('mixes/<int:mix_pk>/performance/add/', views.add_performance_result_view, name='add_performance_result'),
    path('mixes/<int:mix_pk>/performance/<int:perf_pk>/edit/', views.edit_performance_result_view, name='edit_performance_result'),
    path('mixes/<int:mix_pk>/performance/<int:perf_pk>/delete/', views.delete_performance_result_view, name='delete_performance_result'),
    
    # Bibliographic Reference URLs
    path('mixes/<int:mix_pk>/reference/add/', views.add_reference_view, name='add_reference'),
    path('mixes/<int:mix_pk>/reference/<int:ref_pk>/edit/', views.edit_reference_view, name='edit_reference'),
    path('mixes/<int:mix_pk>/reference/<int:ref_pk>/delete/', views.delete_reference_view, name='delete_reference'),
    
    # Dataset URLs
    path('datasets/', views.dataset_list_view, name='dataset_list'),
    path('datasets/add/', views.add_dataset, name='add_dataset'),
    path('datasets/<int:pk>/', views.dataset_detail, name='dataset_detail'),
    path('datasets/<int:pk>/edit/', views.edit_dataset_view, name='edit_dataset'),
    path('datasets/<int:pk>/delete/', views.delete_dataset_view, name='delete_dataset'),
    
    # Sustainability Metrics URLs
    path('mixes/<int:mix_pk>/sustainability/', views.sustainability_metrics_view, name='sustainability_metrics'),
    path('mixes/<int:mix_pk>/sustainability/add/', views.add_sustainability_metric_view, name='add_sustainability_metric'),
    path('mixes/<int:mix_pk>/sustainability/<int:metric_pk>/edit/', views.edit_sustainability_metric_view, name='edit_sustainability_metric'),
    path('mixes/<int:mix_pk>/sustainability/<int:metric_pk>/delete/', views.delete_sustainability_metric_view, name='delete_sustainability_metric'),
]
