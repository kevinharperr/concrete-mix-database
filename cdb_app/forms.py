# cdb_app/forms.py
from django import forms
from .models import (
    Material, ConcreteMix, MixComponent, PerformanceResult, 
    BibliographicReference, Dataset, MaterialClass, MaterialProperty,
    CuringRegime, TestMethod, Specimen, Standard, UnitLookup, SustainabilityMetric
)

# --- Material Forms --- #
class MaterialForm(forms.ModelForm):
    """Form for creating and editing materials."""
    class Meta:
        model = Material
        fields = ['material_class', 'subtype_code', 'specific_name', 'manufacturer', 'source_dataset']
        widgets = {
            'specific_name': forms.TextInput(),
            'manufacturer': forms.TextInput(),
        }
        labels = {
            'material_class': 'Material Class',
            'subtype_code': 'Subtype',
            'specific_name': 'Name',
            'source_dataset': 'Source Dataset',
        }
        help_texts = {
            'subtype_code': 'Specific type (e.g., CEM I, GGBS, NCA)',
            'specific_name': 'Descriptive name of the material'
        }

class MaterialPropertyForm(forms.ModelForm):
    """Form for adding/editing material properties."""
    class Meta:
        model = MaterialProperty
        fields = ['property_name', 'value_num', 'unit']
        widgets = {
            'value_num': forms.NumberInput(attrs={'step': 'any'}),
        }
        labels = {
            'value_num': 'Value',
            'property_name': 'Property',
        }

# --- Concrete Mix Forms --- #
class ConcreteMixForm(forms.ModelForm):
    """Form for creating and editing concrete mixes."""
    # Replace the dataset field with a CharField for direct entry
    dataset_name = forms.CharField(max_length=60, required=True, help_text="Enter dataset name directly")
    
    class Meta:
        model = ConcreteMix
        fields = ['mix_code', 'region_country', 'w_c_ratio', 'w_b_ratio', 
                 'target_slump_mm', 'strength_class', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'w_c_ratio': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '2'}),
            'w_b_ratio': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '2'}),
            'target_slump_mm': forms.NumberInput(attrs={'step': '1', 'min': '0'}),
        }
        labels = {
            'w_c_ratio': 'Water/Cement Ratio',
            'w_b_ratio': 'Water/Binder Ratio',
            'target_slump_mm': 'Target Slump (mm)',
            'strength_class': 'Strength Class',
            'region_country': 'Region/Country',
        }
    
    def __init__(self, *args, **kwargs):
        # Get the initial dataset instance if provided
        instance = kwargs.get('instance')
        if instance and instance.dataset:
            # Set initial value for dataset_name field from the instance
            kwargs.setdefault('initial', {}).update({'dataset_name': instance.dataset.dataset_name})
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data
    
    def save(self, commit=True):
        # Get the dataset_name from the form data
        dataset_name = self.cleaned_data.get('dataset_name')
        
        # Get or create the Dataset instance
        if dataset_name:
            dataset, created = Dataset.objects.get_or_create(
                dataset_name=dataset_name,
            )
            
            # Set the dataset for the mix
            self.instance.dataset = dataset
        
        return super().save(commit)

class MixComponentForm(forms.ModelForm):
    """Form for adding/editing mix components."""
    class Meta:
        model = MixComponent
        fields = ['material', 'dosage_kg_m3', 'is_cementitious']
        widgets = {
            'dosage_kg_m3': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
        labels = {
            'dosage_kg_m3': 'Dosage (kg/m³)',
            'is_cementitious': 'Is Cementitious Material',
        }

# --- Performance and Testing Forms --- #
class PerformanceResultForm(forms.ModelForm):
    """Form for recording performance test results."""
    class Meta:
        model = PerformanceResult
        fields = ['category', 'test_method', 'age_days', 'value_num', 'unit', 
                 'specimen', 'curing_regime', 'test_conditions']
        widgets = {
            'age_days': forms.NumberInput(attrs={'step': '1', 'min': '0'}),
            'value_num': forms.NumberInput(attrs={'step': 'any'}),
            'test_conditions': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'age_days': 'Test Age (days)',
            'value_num': 'Test Value',
            'test_conditions': 'Test Conditions/Notes',
        }

class SpecimenForm(forms.ModelForm):
    """Form for specimen details."""
    class Meta:
        model = Specimen
        fields = ['shape', 'nominal_length_mm', 'nominal_diameter_mm', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
            'nominal_length_mm': forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
            'nominal_diameter_mm': forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
        }
        labels = {
            'nominal_length_mm': 'Length (mm)',
            'nominal_diameter_mm': 'Diameter (mm)',
        }
        help_texts = {
            'shape': 'e.g., Cylinder, Cube, Prism',
            'nominal_length_mm': 'Length for prism/cube, height for cylinder',
            'nominal_diameter_mm': 'Diameter for cylinder, width for cube/prism',
        }

# --- Reference Forms --- #
class BibliographicReferenceForm(forms.ModelForm):
    """Form for bibliographic references."""
    class Meta:
        model = BibliographicReference
        fields = ['citation_text', 'author', 'year', 'title', 'publication', 'doi']
        widgets = {
            'citation_text': forms.Textarea(attrs={'rows': 3}),
            'year': forms.NumberInput(attrs={'min': '1900', 'max': '2100'}),
        }

# --- Dataset Form --- #
class DatasetForm(forms.ModelForm):
    """Form for creating and editing datasets."""
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    source = forms.CharField(required=False, help_text='Origin of the dataset (e.g., research paper, industry source)')
    license_info = forms.CharField(required=False, help_text='Licensing information for this dataset')
    
    class Meta:
        model = Dataset
        fields = ['dataset_name', 'license']
        labels = {
            'dataset_name': 'Dataset Name',
            'license': 'License Information',
        }

# --- Sustainability Metrics Form --- #
class SustainabilityMetricsForm(forms.ModelForm):
    """Form for adding/editing sustainability metrics."""
    class Meta:
        model = SustainabilityMetric  # Using SustainabilityMetric (singular) model
        fields = ['metric_code', 'value_num', 'unit', 'method_ref']
        widgets = {
            'value_num': forms.NumberInput(attrs={'step': 'any'}),
        }
        labels = {
            'metric_code': 'Metric Type',
            'value_num': 'Value',
            'method_ref': 'Calculation Method',
        }
        help_texts = {
            'metric_code': 'E.g., GWP (CO₂ equivalent), Embodied Energy, Water Usage',
            'method_ref': 'Calculation method or reference standard'
        }
