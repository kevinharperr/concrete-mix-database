# concrete_mix_app/api_views.py
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Material, Concretemix, Mixcomposition, 
    Performanceresult, Durabilityresult, Sustainabilitymetrics,
    Specimen, Bibliographicreference
)
from .serializers import (
    MaterialSerializer, ConcreteMixSerializer, ConcreteMixListSerializer,
    MixCompositionSerializer, PerformanceResultSerializer,
    DurabilityResultSerializer, SustainabilityMetricsSerializer,
    SpecimenSerializer, BibliographicReferenceSerializer
)
from .utils import track_object_creation

# Custom permission class for API
class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Allow read access to authenticated users, and write access only to authenticated users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['material_type', 'subtype', 'source_dataset']
    search_fields = ['name', 'material_type', 'subtype', 'manufacturer']
    ordering_fields = ['material_id', 'material_type', 'name']
    
    def perform_create(self, serializer):
        material = serializer.save()
        track_object_creation(self.request.user, material)

class BibliographicReferenceViewSet(viewsets.ModelViewSet):
    queryset = Bibliographicreference.objects.all()
    serializer_class = BibliographicReferenceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['source_dataset', 'year']
    search_fields = ['author', 'title', 'publication']
    ordering_fields = ['reference_id', 'author', 'year']
    
    def perform_create(self, serializer):
        reference = serializer.save()
        track_object_creation(self.request.user, reference)

class ConcreteMixViewSet(viewsets.ModelViewSet):
    queryset = Concretemix.objects.all().select_related('reference')
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['source_dataset', 'region']
    search_fields = ['mix_code', 'notes', 'source_dataset', 'region']
    ordering_fields = ['mix_id', 'mix_code', 'source_dataset', 'date_created']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ConcreteMixListSerializer
        return ConcreteMixSerializer
    
    def perform_create(self, serializer):
        mix = serializer.save()
        track_object_creation(self.request.user, mix)
    
    @action(detail=True, methods=['get'])
    def compositions(self, request, pk=None):
        mix = self.get_object()
        compositions = mix.mix_compositions.select_related('material').all()
        serializer = MixCompositionSerializer(compositions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        mix = self.get_object()
        results = mix.performance_results.select_related('specimen').all()
        serializer = PerformanceResultSerializer(results, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def durability(self, request, pk=None):
        mix = self.get_object()
        results = mix.durability_results.select_related('specimen').all()
        serializer = DurabilityResultSerializer(results, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def sustainability(self, request, pk=None):
        mix = self.get_object()
        metrics = mix.sustainability_metrics.all()
        serializer = SustainabilityMetricsSerializer(metrics, many=True)
        return Response(serializer.data)

class MixCompositionViewSet(viewsets.ModelViewSet):
    queryset = Mixcomposition.objects.all().select_related('mix', 'material')
    serializer_class = MixCompositionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['mix', 'material']
    ordering_fields = ['composition_id', 'mix', 'material']
    
    def perform_create(self, serializer):
        composition = serializer.save()
        track_object_creation(self.request.user, composition)

class PerformanceResultViewSet(viewsets.ModelViewSet):
    queryset = Performanceresult.objects.all().select_related('mix', 'specimen')
    serializer_class = PerformanceResultSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['mix', 'test_type', 'test_age_days']
    search_fields = ['test_type', 'test_conditions']
    ordering_fields = ['result_id', 'mix', 'test_age_days', 'test_value']
    
    def perform_create(self, serializer):
        result = serializer.save()
        track_object_creation(self.request.user, result)
