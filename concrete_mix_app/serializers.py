# concrete_mix_app/serializers.py
from rest_framework import serializers
from .models import (
    Material, Concretemix, Mixcomposition, 
    Performanceresult, Durabilityresult, Sustainabilitymetrics,
    Specimen, Bibliographicreference
)

class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = '__all__'

class BibliographicReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bibliographicreference
        fields = '__all__'

class SpecimenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specimen
        fields = '__all__'

class MixCompositionSerializer(serializers.ModelSerializer):
    material_details = MaterialSerializer(source='material', read_only=True)
    
    class Meta:
        model = Mixcomposition
        fields = ['composition_id', 'mix', 'material', 'material_details', 'quantity_kg_m3', 
                  'percentage_by_weight', 'replacement_percentage', 'w_c_ratio', 'w_b_ratio', 'is_wb_ratio']

class PerformanceResultSerializer(serializers.ModelSerializer):
    specimen_details = SpecimenSerializer(source='specimen', read_only=True)
    
    class Meta:
        model = Performanceresult
        fields = ['result_id', 'mix', 'test_type', 'test_age_days', 'test_value', 
                  'test_unit', 'test_conditions', 'curing_regime', 'specimen', 'specimen_details']

class DurabilityResultSerializer(serializers.ModelSerializer):
    specimen_details = SpecimenSerializer(source='specimen', read_only=True)
    
    class Meta:
        model = Durabilityresult
        fields = ['result_id', 'mix', 'test_type', 'test_age_days', 'test_value', 
                  'test_unit', 'test_conditions', 'specimen', 'specimen_details']

class SustainabilityMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sustainabilitymetrics
        fields = ['metric_id', 'mix', 'co2_footprint_kg_per_m3', 'cost_per_m3', 'clinker_factor',
                  'scm_percentage', 'recyclability_index', 'embodied_energy_mj_per_m3', 
                  'global_warming_potential_kg_co2e']

class ConcreteMixSerializer(serializers.ModelSerializer):
    reference_details = BibliographicReferenceSerializer(source='reference', read_only=True)
    mix_compositions = MixCompositionSerializer(many=True, read_only=True)
    performance_results = PerformanceResultSerializer(many=True, read_only=True)
    durability_results = DurabilityResultSerializer(many=True, read_only=True)
    sustainability_metrics = SustainabilityMetricsSerializer(many=True, read_only=True)
    
    class Meta:
        model = Concretemix
        fields = ['mix_id', 'mix_code', 'date_created', 'source_dataset', 'region',
                  'target_strength_mpa', 'target_workability_mm', 'notes', 'reference',
                  'reference_details', 'mix_compositions', 'performance_results',
                  'durability_results', 'sustainability_metrics']

class ConcreteMixListSerializer(serializers.ModelSerializer):
    reference_details = BibliographicReferenceSerializer(source='reference', read_only=True)
    
    class Meta:
        model = Concretemix
        fields = ['mix_id', 'mix_code', 'date_created', 'source_dataset', 'region',
                  'target_strength_mpa', 'target_workability_mm', 'reference', 'reference_details']
