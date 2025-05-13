# concrete_mix_app/filters.py
import django_filters
from django import forms
from .models import Concretemix, Material, Performanceresult
from django.db.models import Q

TEST_AGE_CHOICES = [
    ('', 'Any Age'),
    (3, '3 Days'), (7, '7 Days'), (14, '14 Days'), (28, '28 Days'),
    (56, '56 Days'), (90, '90 Days'), (180, '180 Days'), (365, '365 Days'),
]

class ConcreteMixFilter(django_filters.FilterSet):
    # Basic filters
    mix_code = django_filters.CharFilter(lookup_expr='icontains', label='Mix Code/ID')
    region = django_filters.CharFilter(lookup_expr='icontains', label='Region')
    source_dataset = django_filters.CharFilter(lookup_expr='icontains', label='Source Dataset')

    # Strength filters - use both target_strength_mpa and performance test results
    min_strength = django_filters.NumberFilter(
        method='filter_by_strength',
        label='Min Comp. Strength (MPa)'
    )
    max_strength = django_filters.NumberFilter(
        method='filter_by_strength',
        label='Max Comp. Strength (MPa)'
    )
    
    # This is for backward compatibility with existing URLs that might use the old parameter names
    # Use widget=forms.HiddenInput to hide these from the form
    compressive_strength_mpa__gte = django_filters.NumberFilter(
        field_name='target_strength_mpa',
        lookup_expr='gte',
        label='Min Comp. Strength (MPa)',
        widget=forms.HiddenInput()
    )
    compressive_strength_mpa__lte = django_filters.NumberFilter(
        field_name='target_strength_mpa',
        lookup_expr='lte',
        label='Max Comp. Strength (MPa)',
        widget=forms.HiddenInput()
    )
    
    # Test age filter - this still uses the custom method as it filters on related models
    test_age_days = django_filters.ChoiceFilter(
        choices=TEST_AGE_CHOICES,
        method='filter_by_performance',
        label='Test Age',
        empty_label=None,
        required=False
    )

    # Material type filter
    material_type = django_filters.ModelChoiceFilter(
        queryset=Material.objects.values_list('material_type', flat=True).distinct(),
        field_name='mix_compositions__material__material_type',
        label='Material Type in Mix',
        to_field_name='material_type',
        empty_label="Any Material Type",
        required=False
    )

    # Ordering
    ordering = django_filters.OrderingFilter(
        fields=(
            ('mix_code', 'mix_code'), # Standard lexical sort
            ('date_created', 'date_created'),
            ('region', 'region'),
        ),
        field_labels={
            'mix_code': 'Mix Code',
            'date_created': 'Date Created',
            'region': 'Region',
        },
        empty_label="Default Order"
    )

    def filter_by_strength(self, queryset, name, value):
        min_strength = self.form.cleaned_data.get('min_strength')
        max_strength = self.form.cleaned_data.get('max_strength')
        
        # Also check for the old parameter names for backward compatibility
        if min_strength is None:
            min_strength = self.form.cleaned_data.get('compressive_strength_mpa__gte')
        if max_strength is None:
            max_strength = self.form.cleaned_data.get('compressive_strength_mpa__lte')
        
        if min_strength is not None or max_strength is not None:
            # Start with no filters
            combined_filter = Q()
            
            # Build filters for target_strength_mpa field (if it exists)
            target_strength_filter = Q()
            if min_strength is not None:
                target_strength_filter &= Q(target_strength_mpa__gte=min_strength)
            if max_strength is not None:
                target_strength_filter &= Q(target_strength_mpa__lte=max_strength)
            
            # Build filters for performance results
            performance_filter = Q(performance_results__test_type__icontains='compressive')
            if min_strength is not None:
                performance_filter &= Q(performance_results__test_value__gte=min_strength)
            if max_strength is not None:
                performance_filter &= Q(performance_results__test_value__lte=max_strength)
            
            # Combine with OR: match either target_strength OR performance result
            combined_filter |= target_strength_filter
            combined_filter |= performance_filter
            
            # Apply the combined filter
            queryset = queryset.filter(combined_filter).distinct()
            
        return queryset
        
    def filter_by_performance(self, queryset, name, value):
        # This method is now only used for test_age_days filtering
        age = self.form.cleaned_data.get('test_age_days')
        
        if age:
            performance_filters = Q(performance_results__test_type__icontains='compressive')
            performance_filters &= Q(performance_results__test_age_days=age)
            queryset = queryset.filter(performance_filters).distinct()
        return queryset

    class Meta:
        model = Concretemix
        # Include all filter fields, both new and legacy
        fields = [
            'mix_code', 'region', 'source_dataset', 'material_type',
            'min_strength', 'max_strength',
            'compressive_strength_mpa__gte', 'compressive_strength_mpa__lte',
            'test_age_days'
        ]