# cdb_app/api_views.py
from rest_framework import viewsets, permissions
from .models import (
    Material, ConcreteMix, MixComponent, PerformanceResult, 
    BibliographicReference, Dataset, MaterialClass, SustainabilityMetric
)
from rest_framework import serializers

# Serializers
class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = '__all__'

class ConcreteMixSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConcreteMix
        fields = '__all__'

class MixComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MixComponent
        fields = '__all__'

class PerformanceResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceResult
        fields = '__all__'

class BibliographicReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BibliographicReference
        fields = '__all__'

class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = '__all__'

class SustainabilityMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SustainabilityMetric
        fields = '__all__'

# ViewSets
class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.using('cdb').all()
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]

class ConcreteMixViewSet(viewsets.ModelViewSet):
    queryset = ConcreteMix.objects.using('cdb').all()
    serializer_class = ConcreteMixSerializer
    permission_classes = [permissions.IsAuthenticated]

class MixComponentViewSet(viewsets.ModelViewSet):
    queryset = MixComponent.objects.using('cdb').all()
    serializer_class = MixComponentSerializer
    permission_classes = [permissions.IsAuthenticated]

class PerformanceResultViewSet(viewsets.ModelViewSet):
    queryset = PerformanceResult.objects.using('cdb').all()
    serializer_class = PerformanceResultSerializer
    permission_classes = [permissions.IsAuthenticated]

class BibliographicReferenceViewSet(viewsets.ModelViewSet):
    queryset = BibliographicReference.objects.using('cdb').all()
    serializer_class = BibliographicReferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.using('cdb').all()
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated]

class SustainabilityMetricsViewSet(viewsets.ModelViewSet):
    queryset = SustainabilityMetric.objects.using('cdb').all()
    serializer_class = SustainabilityMetricsSerializer
    permission_classes = [permissions.IsAuthenticated]
