# concrete_mix_app/forms.py
from django import forms
from django_select2 import forms as s2forms
# Make sure to import all required models
from .models import (
    Material,
    Concretemix,
    Bibliographicreference,
    Mixcomposition,
    Performanceresult,
    Durabilityresult,
    Sustainabilitymetrics,
    Specimen
)

# Define Select2 widgets
class MaterialWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        'name__icontains',
        'material_type__icontains',
        'subtype__icontains',
    ]

class ReferenceWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        'author__icontains',
        'title__icontains',
        'publication__icontains',
    ]

class SpecimenWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        'specimen_type__icontains',
        'specimen_dimensions__icontains',
    ]

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = [
            'material_type',
            'subtype',
            'name',
            'manufacturer',
            'standard_reference',
            'source_dataset',
        ]

class ConcreteMixForm(forms.ModelForm):
    reference = forms.ModelChoiceField(
        queryset=Bibliographicreference.objects.all(),
        required=False,
        label="Bibliographic Reference",
        widget=ReferenceWidget
    )

    class Meta:
        model = Concretemix
        fields = [
            'mix_code',
            'source_dataset',
            'region',
            'target_strength_mpa',
            'target_workability_mm',
            'notes',
            'reference',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'mix_code': 'Mix Code/Identifier',
            'target_strength_mpa': 'Target Strength (MPa)',
            'target_workability_mm': 'Target Workability (mm)',
            'source_dataset': 'Source Dataset Label',
        }

class MixCompositionForm(forms.ModelForm):
    material = forms.ModelChoiceField(
        queryset=Material.objects.order_by('material_type', 'name'),
        label="Material",
        widget=MaterialWidget
    )

    class Meta:
        model = Mixcomposition
        fields = [
            'material',
            'quantity_kg_m3',
        ]
        labels = {
            'quantity_kg_m3': 'Quantity (kg/m³)',
        }

class PerformanceResultForm(forms.ModelForm):
    specimen = forms.ModelChoiceField(
        queryset=Specimen.objects.all(),
        required=False,
        label="Specimen Used",
        widget=SpecimenWidget
    )

    class Meta:
        model = Performanceresult
        fields = [
            'test_type',
            'test_age_days',
            'test_value',
            'test_unit',
            'test_conditions',
            'curing_regime',
            'specimen',
        ]
        widgets = {
            'test_age_days': forms.NumberInput(attrs={'min': 0}),
            'test_value': forms.NumberInput(),
        }
        labels = {
            'test_type': 'Test Type',
            'test_age_days': 'Test Age (Days)',
            'test_value': 'Test Value',
            'test_unit': 'Unit',
            'test_conditions': 'Test Conditions',
            'curing_regime': 'Curing Regime',
        }

# --- Add DurabilityResultForm --- #
class DurabilityResultForm(forms.ModelForm):
    specimen = forms.ModelChoiceField(
        queryset=Specimen.objects.all(),
        required=False, # Based on model allowing null
        label="Specimen Used",
        widget=SpecimenWidget
    )

    class Meta:
        model = Durabilityresult
        # Exclude result_id (auto-generated) and mix (set in view)
        fields = [
            'test_type',
            'test_age_days',
            'test_value',
            'test_unit',
            'test_conditions',
            'specimen',
        ]
        widgets = {
            'test_age_days': forms.NumberInput(attrs={'min': 0}),
            'test_value': forms.NumberInput(),
        }
        labels = {
            'test_type': 'Test Type',
            'test_age_days': 'Test Age (Days)',
            'test_value': 'Test Value',
            'test_unit': 'Unit',
            'test_conditions': 'Test Conditions',
        }

# --- Add SustainabilityMetricsForm --- #
class SustainabilityMetricsForm(forms.ModelForm):
    class Meta:
        model = Sustainabilitymetrics
        # Exclude metric_id (auto-generated) and mix (set in view)
        fields = [
            'co2_footprint_kg_per_m3',
            'cost_per_m3',
            'clinker_factor',
            'scm_percentage',
            'recyclability_index',
            'embodied_energy_mj_per_m3',
            'global_warming_potential_kg_co2e',
        ]
        widgets = {
            'co2_footprint_kg_per_m3': forms.NumberInput(attrs={'step': '0.01'}),
            'cost_per_m3': forms.NumberInput(attrs={'step': '0.01'}),
            'clinker_factor': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '1'}),
            'scm_percentage': forms.NumberInput(attrs={'step': '0.1', 'min': '0', 'max': '100'}),
            'recyclability_index': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '1'}),
            'embodied_energy_mj_per_m3': forms.NumberInput(attrs={'step': '0.1'}),
            'global_warming_potential_kg_co2e': forms.NumberInput(attrs={'step': '0.01'}),
        }
        labels = {
            'co2_footprint_kg_per_m3': 'CO₂ Footprint (kg/m³)',
            'cost_per_m3': 'Cost (per m³)',
            'clinker_factor': 'Clinker Factor (0-1)',
            'scm_percentage': 'SCM Percentage (%)',
            'recyclability_index': 'Recyclability Index (0-1)',
            'embodied_energy_mj_per_m3': 'Embodied Energy (MJ/m³)',
            'global_warming_potential_kg_co2e': 'Global Warming Potential (kg CO₂e)',
        }
