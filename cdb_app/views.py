# cdb_app/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.urls import reverse
import csv
from functools import wraps

from .models import (
    Material, ConcreteMix, MixComponent, PerformanceResult, 
    BibliographicReference, Dataset, MaterialClass, MaterialProperty,
    CuringRegime, TestMethod, Specimen, SustainabilityMetric, UnitLookup
)
from .forms import (
    MaterialForm, ConcreteMixForm, MixComponentForm, PerformanceResultForm,
    SpecimenForm, BibliographicReferenceForm, SustainabilityMetricsForm,
    DatasetForm
)

from django.db.models import (
    Count, Avg, Prefetch, Max, OuterRef, Subquery, F, Value, CharField, BigIntegerField,
    ExpressionWrapper, Q
)
# Using RawSQL for natural sorting (matching functionality from original app)
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# Custom decorator to check if user can contribute data
def contributor_required(view_func):
    """
    Decorator that checks if the user is a Data Contributor or Admin
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Check if user is in the Data Contributors group or is an admin
        if not request.user.is_superuser and not request.user.groups.filter(name__in=['Data Contributors', 'Admins']).exists():
            messages.error(request, 'You do not have permission to contribute data. Please contact an administrator to request access.')
            return HttpResponseForbidden('Permission denied: You must be a Data Contributor or Admin to perform this action.')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# --- Dashboard --- #
@login_required
def dashboard(request):
    """Dashboard view for the CDB app."""
    # Get counts of various entities
    mix_count = ConcreteMix.objects.count()
    material_count = Material.objects.count()
    dataset_count = Dataset.objects.count()
    performance_count = PerformanceResult.objects.count()
    
    # Get recent mixes
    recent_mixes = ConcreteMix.objects.order_by('-mix_id')[:5]
    
    context = {
        'mix_count': mix_count,
        'material_count': material_count,
        'dataset_count': dataset_count,
        'performance_count': performance_count,
        'recent_mixes': recent_mixes,
        'app_name': 'cdb_app',  # For template context
    }
    
    return render(request, 'cdb_app/dashboard.html', context)

# --- Material Views --- #
@login_required
def material_list_view(request):
    """Display a list of all materials in the database."""
    materials = Material.objects.select_related('material_class').order_by('material_class', 'subtype_code')
    
    # Get statistics on materials
    material_class_stats = MaterialClass.objects.annotate(
        material_count=Count('materials')  # Changed from 'material' to 'materials' to match related_name
    ).order_by('class_code')
    
    context = {
        'materials': materials,
        'material_class_stats': material_class_stats,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/material_list.html', context)

@login_required
@contributor_required
def add_material(request):
    """Add a new material to the database."""
    if request.method == 'POST':
        form = MaterialForm(request.POST)
        if form.is_valid():
            material = form.save(commit=False)
            # Save to the 'cdb' database
            material.save(using='cdb')
            messages.success(request, f'Material {material.specific_name} created successfully!')
            return redirect('cdb_app:material_detail', pk=material.material_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MaterialForm()
    
    context = {
        'form': form,
        'form_title': 'Add Material',
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/generic_form.html', context)

@login_required
def material_detail(request, pk):
    """Display details of a specific material."""
    material = get_object_or_404(Material.objects.select_related('material_class'), pk=pk)
    
    # Get associated properties
    properties = MaterialProperty.objects.filter(material=material)
    
    # Get mixes that use this material
    mix_components = MixComponent.objects.filter(material=material).select_related('mix')
    
    context = {
        'material': material,
        'properties': properties,
        'mix_components': mix_components,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/material_detail.html', context)

@login_required
@contributor_required
def edit_material_view(request, pk):
    """Edit an existing material with permission checks."""
    material = get_object_or_404(Material.objects, pk=pk)
    
    if request.method == 'POST':
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            # Save to the 'cdb' database
            form.save(using='cdb')
            messages.success(request, f'Material {material.specific_name} updated successfully!')
            return redirect('cdb_app:material_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MaterialForm(instance=material)
    
    context = {
        'form': form,
        'form_title': f'Edit Material: {material.specific_name}',
        'is_edit': True,
        'material': material,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/generic_form.html', context)

@login_required
def delete_material_view(request, pk):
    """Delete a material with permission checks - Admin only."""
    material = get_object_or_404(Material.objects, pk=pk)
    
    # Only allow admins to delete materials
    if not request.user.is_superuser and not request.user.groups.filter(name='Admins').exists():
        messages.error(request, 'Only administrators can delete materials.')
        return HttpResponseForbidden('Permission denied: Only administrators can delete materials.')
    
    if request.method == 'POST':
        # Check if this material is used in any mixes
        if MixComponent.objects.filter(material=material).exists():
            messages.error(request, f'Cannot delete material {material.specific_name} because it is used in concrete mixes.')
            return redirect('cdb_app:material_detail', pk=pk)
        
        # Store name for success message
        material_name = material.specific_name or f'ID: {material.pk}'
        
        # Delete the material from 'cdb' database
        material.delete(using='cdb')
        
        messages.success(request, f'Material {material_name} deleted successfully!')
        return redirect('cdb_app:material_list')
    
    context = {
        'material': material,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/material_confirm_delete.html', context)

# --- Concrete Mix Views --- #
@login_required
def mix_list_view(request):
    """Display a filterable list of mixes, handles sorting and CSV export."""
    # Get all mixes with prefetched components and dataset for efficiency
    mixes = ConcreteMix.objects.select_related('dataset').all()
    
    # Apply filters from query parameters
    filters_applied = False
    
    # Filter by dataset name if provided
    dataset_filter = request.GET.get('dataset')
    if dataset_filter:
        mixes = mixes.filter(dataset__dataset_name=dataset_filter)
        filters_applied = True
    
    # Filter by region/country if provided
    region_filter = request.GET.get('region')
    if region_filter:
        mixes = mixes.filter(region_country__icontains=region_filter)
        filters_applied = True
    
    # Filter by minimum strength from test results
    min_strength = request.GET.get('min_strength')
    if min_strength and min_strength.isdigit():
        # Join with performance results and filter by 28-day compressive strength
        # Use union to combine different category filters instead of Q objects
        mixes_compressive = mixes.filter(
            performance_results__category__icontains='compressive',
            performance_results__age_days=28,
            performance_results__value_num__gte=min_strength
        )
        mixes_strength = mixes.filter(
            performance_results__category__icontains='strength',
            performance_results__age_days=28,
            performance_results__value_num__gte=min_strength
        )
        mixes_hardened = mixes.filter(
            performance_results__category__icontains='hardened',
            performance_results__age_days=28,
            performance_results__value_num__gte=min_strength
        )
        # Combine the results
        mixes = mixes_compressive.union(mixes_strength, mixes_hardened).distinct()
        filters_applied = True
    
    # Filter by strength class
    strength_class = request.GET.get('strength_class')
    if strength_class:
        # Parse the strength class filter (e.g., "EN:C25/30" or "ASTM:4000")
        try:
            standard, class_code = strength_class.split(':')
            
            # Import utility functions for strength classification
            from .utils import EN_STRENGTH_CLASSES, ASTM_STRENGTH_CLASSES, MPA_TO_PSI, PSI_TO_MPA
            
            min_strength_value = None
            
            # Find the minimum strength value for the selected class
            if standard == 'EN':
                for en_class in EN_STRENGTH_CLASSES:
                    if en_class[0] == class_code:
                        min_strength_value = en_class[1]  # MPa value
                        break
            elif standard == 'ASTM':
                for astm_class in ASTM_STRENGTH_CLASSES:
                    if astm_class[0] == class_code:
                        # Convert from psi to MPa for database query
                        min_strength_value = float(astm_class[1]) * float(PSI_TO_MPA)
                        break
            
            if min_strength_value:
                # Filter by calculated minimum strength using union to avoid Q objects
                mixes_compressive = mixes.filter(
                    performance_results__category__icontains='compressive',
                    performance_results__age_days=28,
                    performance_results__value_num__gte=min_strength_value
                )
                mixes_strength = mixes.filter(
                    performance_results__category__icontains='strength',
                    performance_results__age_days=28,
                    performance_results__value_num__gte=min_strength_value
                )
                mixes_hardened = mixes.filter(
                    performance_results__category__icontains='hardened',
                    performance_results__age_days=28,
                    performance_results__value_num__gte=min_strength_value
                )
                # Combine the results
                mixes = mixes_compressive.union(mixes_strength, mixes_hardened).distinct()
                filters_applied = True
        except (ValueError, IndexError):
            # If the strength class format is invalid, ignore this filter
            pass
    
    # Filter by maximum water/binder ratio
    max_wb = request.GET.get('max_wb')
    if max_wb and max_wb.replace('.', '', 1).isdigit():
        mixes = mixes.filter(w_b_ratio__lte=max_wb)
        filters_applied = True
    
    # Check for sorting parameter
    sort_param = request.GET.get('sort', 'mix_id')  # Default to ID sorting
    
    # If natural sorting is requested for mix_code
    if sort_param == 'mix_code_natural':
        # Use a Raw SQL expression to achieve natural sorting of mix codes
        # This uses PostgreSQL's ability to extract numeric parts of strings
        mixes = mixes.annotate(
            mix_code_numeric=RawSQL(
                "REGEXP_REPLACE(mix_code, '[^0-9]', '', 'g')::integer", []
            )
        ).order_by('mix_code_numeric', 'mix_code')
        # If annotation fails, fallback to mix_id
        if 'natural' in sort_param:
            sort_param = 'mix_id'
    
    # Determine final ordering
    if sort_param == 'mix_code_natural' and can_natural_sort:
        ordered_qs = annotated_qs.order_by('dataset', 'mix_code_number')
    elif sort_param == '-mix_code_natural' and can_natural_sort:
        ordered_qs = annotated_qs.order_by('-dataset', '-mix_code_number')
    else:
        ordered_qs = annotated_qs.order_by('mix_id')
        if not (sort_param == 'mix_code_natural' and can_natural_sort):
            sort_param = 'mix_id'
    
    # CSV Export
    if request.GET.get('export') == 'csv' and request.user.is_authenticated:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="concrete_mixes_export.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Mix ID', 'Mix Code', 'Dataset', 'Region', 'W/C Ratio', 'W/B Ratio',
            'Target Strength (MPa)', 'Target Slump (mm)', 'Notes',
        ])
        
        for mix in ordered_qs:
            writer.writerow([
                mix.mix_id, mix.mix_code, 
                mix.dataset.dataset_name if mix.dataset else None,
                mix.region_country, mix.w_c_ratio, mix.w_b_ratio,
                mix.target_strength_mpa, mix.target_slump_mm, mix.notes,
            ])
        return response
    
    # Pagination
    try:
        page_size = int(request.GET.get('page_size', 25))
        page_size = min(max(page_size, 10), 100)  # Between 10 and 100
    except (ValueError, TypeError):
        page_size = 25  # Default if invalid
    
    paginator = Paginator(ordered_qs, page_size)
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'page_obj': page_obj,
        'current_ordering': sort_param,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/mix_list.html', context)

@login_required
@contributor_required
def add_mix(request):
    """Add a new concrete mix to the database."""
    if request.method == 'POST':
        form = ConcreteMixForm(request.POST)
        if form.is_valid():
            mix = form.save(commit=False)
            # Save to the 'cdb' database
            mix.save(using='cdb')
            messages.success(request, f'Mix {mix.mix_code} created successfully!')
            return redirect('cdb_app:mix_detail', pk=mix.mix_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ConcreteMixForm()
    
    context = {
        'form': form,
        'form_title': 'Add Concrete Mix',
        'app_name': 'cdb_app',
    }
    
def mix_detail(request, pk):
    import logging
    logger = logging.getLogger(__name__)
    """Display details of a specific concrete mix."""
    mix = get_object_or_404(ConcreteMix.objects.select_related('dataset'), pk=pk)
    
    # Get mix components
    components = MixComponent.objects.filter(
        mix=mix
    ).select_related('material', 'material__material_class')
    
    # Get performance results
    performance_results = PerformanceResult.objects.filter(
        mix=mix
    ).select_related('test_method', 'unit', 'specimen').order_by('category', 'test_method', 'age_days')
    
    # Get reference, if any
    references = BibliographicReference.objects.filter(pk__in=mix.references.all())
    
    # Get sustainability metrics if available
    try:
        sustainability_metrics = SustainabilityMetric.objects.select_related('unit').filter(mix=mix)
    except:
        sustainability_metrics = []
    
    # Add total cementitious content calculation
    cementitious_components = components.filter(is_cementitious=True)
    total_cementitious = sum(comp.dosage_kg_m3 or 0 for comp in cementitious_components)
    
    # Calculate water to cementitious ratio if not provided
    if not mix.w_b_ratio and total_cementitious > 0:
        water_components = components.filter(material__material_class__class_code='WATER')
        total_water = sum(comp.dosage_kg_m3 or 0 for comp in water_components)
        calculated_wb_ratio = total_water / total_cementitious if total_cementitious > 0 else None
    else:
        calculated_wb_ratio = None
    
    # Add strength classification information
    from .utils import classify_strength_by_reported_class, classify_strength_by_test_result
    
    # Initialize strength classification data
    strength_class_info = {
        'reported_classification': None,
        'calculated_classification': None,
        'has_28d_strength': False,
        'strength_28d_value': None,
        'strength_28d_unit': 'MPa'
    }
    
    # Check for reported strength class
    if mix.strength_class:
        strength_class_info['reported_classification'] = classify_strength_by_reported_class(mix.strength_class)
    
    # Look for 28-day compression test results for classification
    # First filter by age_days=28
    compressive_tests = performance_results.filter(age_days=28)
    
    # Then filter by category using a method that doesn't require Q objects
    compressive_tests = compressive_tests.filter(
        category__icontains='compressive'
    ).union(
        performance_results.filter(age_days=28, category__icontains='strength')
    ).union(
        performance_results.filter(age_days=28, category__icontains='hardened')
    ).order_by('-value_num')  # Get the highest value if multiple tests exist
    
    if compressive_tests.exists():
        strength_28d = compressive_tests.first()
        strength_class_info['has_28d_strength'] = True
        strength_class_info['strength_28d_value'] = strength_28d.value_num
        if strength_28d.unit:
            strength_class_info['strength_28d_unit'] = strength_28d.unit.unit_symbol
        
        # Classify based on test result (assuming MPa, which is standard for concrete testing)
        strength_class_info['calculated_classification'] = classify_strength_by_test_result(strength_28d.value_num)
    
    context = {
        'mix': mix,
        'components': components,
        'performance_results': performance_results,
        'references': references,
        'sustainability_metrics': sustainability_metrics,
        'total_cementitious': total_cementitious,
        'calculated_wb_ratio': calculated_wb_ratio,
        'strength_class_info': strength_class_info,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/mix_detail.html', context)

@login_required
@contributor_required
def edit_mix_view(request, pk):
    """Edit an existing concrete mix with permission checks."""
    mix = get_object_or_404(ConcreteMix.objects, pk=pk)
    
    if request.method == 'POST':
        form = ConcreteMixForm(request.POST, instance=mix)
        if form.is_valid():
            # Save to the 'cdb' database
            form.save(using='cdb')
            messages.success(request, f'Mix {mix.mix_code} updated successfully!')
            return redirect('cdb_app:mix_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ConcreteMixForm(instance=mix)
    
    context = {
        'form': form,
        'form_title': f'Edit Mix: {mix.mix_code}',
        'is_edit': True,
        'mix': mix,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/generic_form.html', context)

@login_required
def delete_mix_view(request, pk):
    """Delete a concrete mix with permission checks - Admin only."""
    mix = get_object_or_404(ConcreteMix.objects, pk=pk)
    
    # Only allow admins to delete mixes
    if not request.user.is_superuser and not request.user.groups.filter(name='Admins').exists():
        messages.error(request, 'Only administrators can delete mixes.')
        return HttpResponseForbidden('Permission denied: Only administrators can delete mixes.')
    
    if request.method == 'POST':
        # Store the mix code for the success message before deletion
        mix_code = mix.mix_code or f'ID: {mix.pk}'
        
        # Delete the mix from 'cdb' database
        mix.delete(using='cdb')
        
        messages.success(request, f'Mix {mix_code} deleted successfully!')
        return redirect('cdb_app:mix_list')
    
    context = {
        'mix': mix,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/mix_confirm_delete.html', context)

# --- Mix Component Views --- #
@login_required
@contributor_required
def add_component_view(request, mix_pk):
    """Add a new mix component to a concrete mix."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    
    if request.method == 'POST':
        form = MixComponentForm(request.POST)
        if form.is_valid():
            component = form.save(commit=False)
            component.mix = mix
            # Save to the 'cdb' database
            component.save(using='cdb')
            messages.success(request, 'Material component added successfully!')
            return redirect('cdb_app:mix_detail', pk=mix_pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MixComponentForm()
    
    context = {
        'form': form,
        'form_title': f'Add Component to Mix: {mix.mix_code}',
        'mix': mix,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/generic_form.html', context)

@login_required
@contributor_required
def edit_component_view(request, mix_pk, comp_pk):
    """Edit an existing mix component with permission checks."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    component = get_object_or_404(MixComponent.objects.select_related('material'), pk=comp_pk, mix=mix)
    
    if request.method == 'POST':
        form = MixComponentForm(request.POST, instance=component)
        if form.is_valid():
            # Save to the 'cdb' database
            form.save(using='cdb')
            messages.success(request, 'Material component updated successfully!')
            return redirect('cdb_app:mix_detail', pk=mix_pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MixComponentForm(instance=component)
    
    context = {
        'form': form,
        'form_title': f'Edit Component: {component.material.specific_name}',
        'is_edit': True,
        'mix': mix,
        'component': component,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/generic_form.html', context)

@login_required
def delete_component_view(request, mix_pk, comp_pk):
    """Delete a mix component with permission checks - Admin only."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    component = get_object_or_404(MixComponent.objects.select_related('material'), pk=comp_pk, mix=mix)
    
    # Only allow admins to delete components
    if not request.user.is_superuser and not request.user.groups.filter(name='Admins').exists():
        messages.error(request, 'Only administrators can delete mix components.')
        return HttpResponseForbidden('Permission denied: Only administrators can delete mix components.')
    
    if request.method == 'POST':
        material_name = component.material.specific_name or f'ID: {component.material.pk}'
        
        # Delete the component from 'cdb' database
        component.delete(using='cdb')
        
        messages.success(request, f'Component {material_name} deleted successfully!')
        return redirect('cdb_app:mix_detail', pk=mix_pk)
    
    context = {
        'mix': mix,
        'component': component,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/component_confirm_delete.html', context)

# --- Performance Result Views --- #
@login_required
@contributor_required
def add_performance_result_view(request, mix_pk):
    """Add a new performance result to a concrete mix."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    
    if request.method == 'POST':
        form = PerformanceResultForm(request.POST)
        if form.is_valid():
            result = form.save(commit=False)
            result.mix = mix
            # Save to the 'cdb' database
            result.save(using='cdb')
            messages.success(request, 'Performance result added successfully!')
            return redirect('cdb_app:mix_detail', pk=mix_pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PerformanceResultForm()
    
    context = {
        'form': form,
        'form_title': f'Add Performance Result to Mix: {mix.mix_code}',
        'mix': mix,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/generic_form.html', context)

@login_required
@contributor_required
def edit_performance_result_view(request, mix_pk, perf_pk):
    """Edit an existing performance result with permission checks."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    result = get_object_or_404(PerformanceResult.objects, pk=perf_pk, mix=mix)
    
    if request.method == 'POST':
        form = PerformanceResultForm(request.POST, instance=result)
        if form.is_valid():
            # Save to the 'cdb' database
            form.save(using='cdb')
            messages.success(request, 'Performance result updated successfully!')
            return redirect('cdb_app:mix_detail', pk=mix_pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PerformanceResultForm(instance=result)
    
    context = {
        'form': form,
        'form_title': f'Edit Performance Result',
        'is_edit': True,
        'mix': mix,
        'result': result,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/generic_form.html', context)

@login_required
def delete_performance_result_view(request, mix_pk, perf_pk):
    """Delete a performance result with permission checks - Admin only."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    result = get_object_or_404(PerformanceResult.objects, pk=perf_pk, mix=mix)
    
    # Only allow admins to delete results
    if not request.user.is_superuser and not request.user.groups.filter(name='Admins').exists():
        messages.error(request, 'Only administrators can delete performance results.')
        return HttpResponseForbidden('Permission denied: Only administrators can delete performance results.')
    
    if request.method == 'POST':
        # Delete the result from 'cdb' database
        result.delete(using='cdb')
        
        messages.success(request, 'Performance result deleted successfully!')
        return redirect('cdb_app:mix_detail', pk=mix_pk)
    
    context = {
        'mix': mix,
        'result': result,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/result_confirm_delete.html', context)

# --- Bibliographic Reference Views --- #
@login_required
@contributor_required
def add_reference_view(request, mix_pk):
    """Add a new bibliographic reference to a concrete mix."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    
    if request.method == 'POST':
        form = BibliographicReferenceForm(request.POST)
        if form.is_valid():
            reference = form.save(commit=False)
            reference.mix = mix
            # Save to the 'cdb' database
            reference.save(using='cdb')
            messages.success(request, 'Bibliographic reference added successfully!')
            return redirect('cdb_app:mix_detail', pk=mix_pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BibliographicReferenceForm()
    
    context = {
        'form': form,
        'form_title': f'Add Bibliographic Reference to Mix: {mix.mix_code}',
        'mix': mix,
        'app_name': 'cdb_app',
        'is_edit': False
    }
    
    return render(request, 'cdb_app/reference_form.html', context)

@login_required
@contributor_required
def edit_reference_view(request, mix_pk, ref_pk):
    """Edit an existing bibliographic reference with permission checks."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    reference = get_object_or_404(BibliographicReference.objects, pk=ref_pk, mix=mix)
    
    if request.method == 'POST':
        form = BibliographicReferenceForm(request.POST, instance=reference)
        if form.is_valid():
            # Save to the 'cdb' database
            form.save(using='cdb')
            messages.success(request, 'Bibliographic reference updated successfully!')
            return redirect('cdb_app:mix_detail', pk=mix_pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BibliographicReferenceForm(instance=reference)
    
    context = {
        'form': form,
        'form_title': f'Edit Bibliographic Reference',
        'is_edit': True,
        'mix': mix,
        'reference': reference,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/reference_form.html', context)

@login_required
def delete_reference_view(request, mix_pk, ref_pk):
    """Delete a bibliographic reference with permission checks - Admin only."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    reference = get_object_or_404(BibliographicReference.objects, pk=ref_pk, mix=mix)
    
    # Only allow admins to delete references
    if not request.user.is_superuser and not request.user.groups.filter(name='Admins').exists():
        messages.error(request, 'Only administrators can delete bibliographic references.')
        return HttpResponseForbidden('Permission denied: Only administrators can delete bibliographic references.')
    
    if request.method == 'POST':
        # Delete the reference from 'cdb' database
        reference.delete(using='cdb')
        
        messages.success(request, 'Bibliographic reference deleted successfully!')
        return redirect('cdb_app:mix_detail', pk=mix_pk)
    
    context = {
        'object_type': 'bibliographic reference',
        'object_name': reference.title or f'Reference ID: {reference.pk}',
        'extra_info': f'Citation: {reference.citation_text[:100]}...' if len(reference.citation_text) > 100 else reference.citation_text,
        'cancel_url': reverse('cdb_app:mix_detail', kwargs={'pk': mix_pk}),
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/delete_confirmation.html', context)

# --- Dataset Views --- #
@login_required
def dataset_list_view(request):
    """Display a list of all datasets in the database."""
    datasets = Dataset.objects.all().order_by('dataset_name')
    
    # Search functionality
    query = request.GET.get('q')
    if query:
        datasets = datasets.filter(dataset_name__icontains=query) | datasets.filter(description__icontains=query)
    
    # Pagination
    paginator = Paginator(datasets, 10)  # 10 datasets per page
    page_number = request.GET.get('page')
    try:
        datasets = paginator.page(page_number)
    except PageNotAnInteger:
        datasets = paginator.page(1)
    except EmptyPage:
        datasets = paginator.page(paginator.num_pages)
    
    context = {
        'datasets': datasets,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/dataset_list.html', context)

@login_required
def dataset_detail(request, pk):
    """Display details of a specific dataset."""
    dataset = get_object_or_404(Dataset.objects, pk=pk)
    
    # Get mixes in this dataset with pagination
    mixes = ConcreteMix.objects.filter(dataset=dataset).order_by('mix_code')
    
    # Get statistics
    total_mixes = mixes.count()
    total_materials = Material.objects.filter(mix_usages__mix__dataset=dataset).distinct().count()
    total_results = PerformanceResult.objects.filter(mix__dataset=dataset).count()
    
    # Get average compressive strength if available
    strength_results = PerformanceResult.objects.filter(
        mix__dataset=dataset, 
        category__icontains='strength'
    )
    strength_avg = strength_results.aggregate(avg_strength=Avg('value_num'))['avg_strength']
    
    # Pagination for mixes
    paginator = Paginator(mixes, 10)  # 10 mixes per page
    page_number = request.GET.get('page')
    try:
        mixes = paginator.page(page_number)
    except PageNotAnInteger:
        mixes = paginator.page(1)
    except EmptyPage:
        mixes = paginator.page(paginator.num_pages)
    
    context = {
        'dataset': dataset,
        'mixes': mixes,
        'total_mixes': total_mixes,
        'total_materials': total_materials,
        'total_results': total_results,
        'strength_avg': strength_avg,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/dataset_detail.html', context)

@login_required
@contributor_required
def add_dataset(request):
    """Add a new dataset to the database."""
    if request.method == 'POST':
        form = DatasetForm(request.POST)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.created_by = request.user
            # Save to the 'cdb' database
            dataset.save(using='cdb')
            messages.success(request, f'Dataset {dataset.dataset_name} created successfully!')
            return redirect('cdb_app:dataset_detail', pk=dataset.dataset_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DatasetForm()
    
    context = {
        'form': form,
        'form_title': 'Add Dataset',
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/generic_form.html', context)

@login_required
@contributor_required
def edit_dataset_view(request, pk):
    """Edit an existing dataset with permission checks."""
    dataset = get_object_or_404(Dataset.objects, pk=pk)
    
    if request.method == 'POST':
        form = DatasetForm(request.POST, instance=dataset)
        if form.is_valid():
            # Save to the 'cdb' database
            form.save(using='cdb')
            messages.success(request, f'Dataset {dataset.dataset_name} updated successfully!')
            return redirect('cdb_app:dataset_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DatasetForm(instance=dataset)
    
    context = {
        'form': form,
        'form_title': f'Edit Dataset: {dataset.dataset_name}',
        'is_edit': True,
        'dataset': dataset,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/generic_form.html', context)

@login_required
def delete_dataset_view(request, pk):
    """Delete a dataset with permission checks - Admin only."""
    dataset = get_object_or_404(Dataset.objects, pk=pk)
    
    # Only allow admins to delete datasets
    if not request.user.is_superuser and not request.user.groups.filter(name='Admins').exists():
        messages.error(request, 'Only administrators can delete datasets.')
        return HttpResponseForbidden('Permission denied: Only administrators can delete datasets.')
    
    # Check if dataset has associated mixes
    has_mixes = ConcreteMix.objects.filter(dataset=dataset).exists()
    
    if request.method == 'POST':
        # If it has mixes and we're not forcing deletion, show warning
        if has_mixes and not request.POST.get('confirm_delete_all'):
            messages.error(request, 'This dataset contains mixes. Please confirm deletion of all associated mixes.')
            context = {
                'object_type': 'dataset',
                'object_name': dataset.dataset_name,
                'extra_info': f'Warning: This dataset contains {ConcreteMix.objects.using("cdb").filter(dataset=dataset).count()} mixes that will also be deleted.',
                'cancel_url': reverse('cdb_app:dataset_detail', kwargs={'pk': pk}),
                'show_force_delete': True,
                'app_name': 'cdb_app',
            }
            return render(request, 'cdb_app/delete_confirmation.html', context)
        
        # Delete the dataset from 'cdb' database
        dataset.delete(using='cdb')
        
        messages.success(request, f'Dataset {dataset.dataset_name} deleted successfully!')
        return redirect('cdb_app:dataset_list')
    
    context = {
        'object_type': 'dataset',
        'object_name': dataset.dataset_name,
        'extra_info': f'This will delete all related data.' + (f' Including {ConcreteMix.objects.using("cdb").filter(dataset=dataset).count()} mixes!' if has_mixes else ''),
        'cancel_url': reverse('cdb_app:dataset_detail', kwargs={'pk': pk}),
        'show_force_delete': has_mixes,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/delete_confirmation.html', context)

# --- Sustainability Metrics Views --- #
@login_required
def sustainability_metrics_view(request, mix_pk):
    """Display sustainability metrics for a concrete mix."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    
    # Get sustainability metrics for this mix
    metrics = SustainabilityMetrics.objects.filter(mix=mix).select_related('unit')
    
    # Calculate totals
    gwp_total = metrics.filter(metric_type__icontains='gwp').aggregate(total=Sum('value'))['total']
    energy_total = metrics.filter(metric_type__icontains='energy').aggregate(total=Sum('value'))['total']
    water_total = metrics.filter(metric_type__icontains='water').aggregate(total=Sum('value'))['total']
    
    context = {
        'mix': mix,
        'metrics': metrics,
        'gwp_total': gwp_total,
        'energy_total': energy_total,
        'water_total': water_total,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/sustainability_metrics.html', context)

@login_required
@contributor_required
def add_sustainability_metric_view(request, mix_pk):
    """Add a new sustainability metric to a concrete mix."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    
    if request.method == 'POST':
        form = SustainabilityMetricsForm(request.POST)
        if form.is_valid():
            metric = form.save(commit=False)
            metric.mix = mix
            # Save to the 'cdb' database
            metric.save(using='cdb')
            messages.success(request, 'Sustainability metric added successfully!')
            return redirect('cdb_app:sustainability_metrics', mix_pk=mix_pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SustainabilityMetricsForm()
    
    context = {
        'form': form,
        'form_title': f'Add Sustainability Metric to Mix: {mix.mix_code}',
        'mix': mix,
        'app_name': 'cdb_app',
        'is_edit': False
    }
    
    return render(request, 'cdb_app/sustainability_metric_form.html', context)

@login_required
@contributor_required
def edit_sustainability_metric_view(request, mix_pk, metric_pk):
    """Edit an existing sustainability metric with permission checks."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    metric = get_object_or_404(SustainabilityMetrics.objects, pk=metric_pk, mix=mix)
    
    if request.method == 'POST':
        form = SustainabilityMetricsForm(request.POST, instance=metric)
        if form.is_valid():
            # Save to the 'cdb' database
            form.save(using='cdb')
            messages.success(request, 'Sustainability metric updated successfully!')
            return redirect('cdb_app:sustainability_metrics', mix_pk=mix_pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SustainabilityMetricsForm(instance=metric)
    
    context = {
        'form': form,
        'form_title': f'Edit Sustainability Metric',
        'is_edit': True,
        'mix': mix,
        'metric': metric,
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/sustainability_metric_form.html', context)

@login_required
def delete_sustainability_metric_view(request, mix_pk, metric_pk):
    """Delete a sustainability metric with permission checks - Admin only."""
    mix = get_object_or_404(ConcreteMix.objects, pk=mix_pk)
    metric = get_object_or_404(SustainabilityMetrics.objects, pk=metric_pk, mix=mix)
    
    # Only allow admins to delete metrics
    if not request.user.is_superuser and not request.user.groups.filter(name='Admins').exists():
        messages.error(request, 'Only administrators can delete sustainability metrics.')
        return HttpResponseForbidden('Permission denied: Only administrators can delete sustainability metrics.')
    
    if request.method == 'POST':
        # Delete the metric from 'cdb' database
        metric.delete(using='cdb')
        
        messages.success(request, 'Sustainability metric deleted successfully!')
        return redirect('cdb_app:sustainability_metrics', mix_pk=mix_pk)
    
    context = {
        'object_type': 'sustainability metric',
        'object_name': f'{metric.metric_type}: {metric.value} {metric.unit.unit_symbol if metric.unit else ""}',
        'cancel_url': reverse('cdb_app:sustainability_metrics', kwargs={'mix_pk': mix_pk}),
        'app_name': 'cdb_app',
    }
    
    return render(request, 'cdb_app/delete_confirmation.html', context)
