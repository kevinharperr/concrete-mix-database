# concrete_mix_app/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.urls import reverse
import csv
from functools import wraps
from .models import (
    Concretemix, Material, Performanceresult, Bibliographicreference, Specimen,
    Mixcomposition, Durabilityresult, Sustainabilitymetrics, Materialproperty,
    Chemicalcomposition, UserObjectTracking
)
from .utils import track_object_creation, get_object_creator, user_can_edit_object, user_can_contribute_data
from django.db.models import (
    Count, Prefetch, Max, OuterRef, Subquery, F, Value, CharField, BigIntegerField,
    ExpressionWrapper
)
# Using RawSQL for natural sorting
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce

# Custom decorator to check if user can contribute data
def contributor_required(view_func):
    """
    Decorator that checks if the user is a Data Contributor or Admin
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not user_can_contribute_data(request.user):
            messages.error(request, 'You do not have permission to contribute data. Please contact an administrator to request access.')
            return HttpResponseForbidden('Permission denied: You must be a Data Contributor or Admin to perform this action.')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view
from .forms import (
    MaterialForm, ConcreteMixForm, MixCompositionForm, PerformanceResultForm,
    DurabilityResultForm, SustainabilityMetricsForm
)
from .filters import ConcreteMixFilter
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import datetime
from django.db import connection

# --- CRUD Helper Views --- #
@login_required
@contributor_required
def edit_mix_view(request, pk):
    '''Edit an existing concrete mix with permission checks'''
    # Get the mix object or return 404
    mix_object = get_object_or_404(Concretemix, pk=pk)
    
    # Check if user has permission to edit this mix
    if not user_can_edit_object(request.user, mix_object):
        messages.error(request, 'You do not have permission to edit this mix.')
        return HttpResponseForbidden('Permission denied: You can only edit mixes you created or if you are an Admin.')
    
    if request.method == 'POST':
        form = ConcreteMixForm(request.POST, instance=mix_object)
        if form.is_valid():
            form.save()
            messages.success(request, f'Mix {mix_object.mix_code} updated successfully!')
            return redirect('concrete_mix_app:mix_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ConcreteMixForm(instance=mix_object)
    
    context = {
        'form_title': f'Edit Mix: {mix_object.mix_code}',
        'form': form,
        'is_edit': True,
        'mix': mix_object
    }
    return render(request, 'concrete_mix_app/generic_form.html', context)

@login_required
def delete_mix_view(request, pk):
    '''Delete a concrete mix with permission checks - Admin only'''
    # Get the mix object or return 404
    mix_object = get_object_or_404(Concretemix, pk=pk)
    
    # Only allow admins to delete mixes
    if not request.user.is_superuser and not request.user.groups.filter(name='Admins').exists():
        messages.error(request, 'Only administrators can delete mixes.')
        return HttpResponseForbidden('Permission denied: Only administrators can delete mixes.')
    
    if request.method == 'POST':
        # Store the mix code for the success message before deletion
        mix_code = mix_object.mix_code or f'ID: {mix_object.pk}'
        
        # Delete the mix
        mix_object.delete()
        
        messages.success(request, f'Mix {mix_code} has been deleted.')
        return redirect('concrete_mix_app:mix_list')
    
    context = {
        'mix': mix_object,
    }
    return render(request, 'concrete_mix_app/delete_mix_confirm.html', context)

# --- Dashboard --- #
@login_required
def dashboard(request):
    total_mixes = Concretemix.objects.count()
    total_materials = Material.objects.count()
    total_performance_results = Performanceresult.objects.count()
    recent_mixes = Concretemix.objects.order_by('-mix_id').prefetch_related(
        Prefetch('mix_compositions', queryset=Mixcomposition.objects.select_related('material'))
    )[:5]
    context = {
        'total_mixes': total_mixes,
        'total_materials': total_materials,
        'total_performance_results': total_performance_results,
        'recent_mixes': recent_mixes,
    }
    return render(request, 'concrete_mix_app/dashboard.html', context)

# --- Material Views --- #
@login_required
def material_list_view(request):
    """
    Display a list of all materials in the database.
    """
    # Get all materials ordered by type and name
    materials = Material.objects.all().order_by('material_type', 'name')
    
    # Get page size from request or use default (25)
    try:
        page_size = int(request.GET.get('page_size', 25))
        # Limit page size to reasonable values
        page_size = min(max(page_size, 10), 100)  # Between 10 and 100
    except (ValueError, TypeError):
        page_size = 25  # Default if invalid
        
    # Set up pagination
    paginator = Paginator(materials, page_size)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
        
    context = {
        'page_obj': page_obj,
        'material_count': materials.count(),
        'can_contribute': user_can_contribute_data(request.user),
    }
    return render(request, 'concrete_mix_app/material_list.html', context)

@login_required
@contributor_required
def add_material(request):
    if request.method == 'POST':
        form = MaterialForm(request.POST)
        if form.is_valid():
            material = form.save(commit=False)
            material.date_added = datetime.date.today()
            material.save()
            
            # Track object creation by the current user
            track_object_creation(request.user, material)
            
            messages.success(request, f'Material "{material.name}" added successfully!')
            return redirect('concrete_mix_app:material_detail', pk=material.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MaterialForm()
    
    context = {
        'form_title': 'Add New Material', 
        'form': form
    }
    return render(request, 'concrete_mix_app/generic_form.html', context)

@login_required
def material_detail(request, pk):
    material = get_object_or_404(Material, pk=pk)
    # Check if user can edit this material (for template rendering purposes)
    can_edit = user_can_edit_object(request.user, material)
    # Check if user is an admin (for delete permission)
    is_admin = request.user.is_superuser or request.user.groups.filter(name='Admins').exists()
    
    material_properties = material.material_properties.all()
    chemical_compositions = material.chemical_compositions.all()
    mixes_using_material = material.mix_compositions.select_related('mix').all()
    context = {
        'material': material, 
        'material_properties': material_properties,
        'chemical_compositions': chemical_compositions, 
        'mixes_using_material': mixes_using_material,
        'can_edit': can_edit, 
        'can_contribute': user_can_contribute_data(request.user),
        'is_admin': is_admin,
    }
    return render(request, 'concrete_mix_app/material_detail.html', context)

@login_required
@contributor_required
def edit_material_view(request, pk):
    '''Edit an existing material with permission checks'''
    # Get the material object or return 404
    material_object = get_object_or_404(Material, pk=pk)
    
    # Check if user has permission to edit this material
    if not user_can_edit_object(request.user, material_object):
        messages.error(request, 'You do not have permission to edit this material.')
        return HttpResponseForbidden('Permission denied: You can only edit materials you created or if you are an Admin.')
    
    if request.method == 'POST':
        form = MaterialForm(request.POST, instance=material_object)
        if form.is_valid():
            form.save()
            messages.success(request, f'Material {material_object.name} updated successfully!')
            return redirect('concrete_mix_app:material_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MaterialForm(instance=material_object)
    
    context = {
        'form_title': f'Edit Material: {material_object.name}',
        'form': form,
        'is_edit': True,
        'material': material_object
    }
    return render(request, 'concrete_mix_app/generic_form.html', context)

@login_required
def delete_material_view(request, pk):
    '''Delete a material with permission checks - Admin only'''
    # Get the material object or return 404
    material_object = get_object_or_404(Material, pk=pk)
    
    # Only allow admins to delete materials
    if not request.user.is_superuser and not request.user.groups.filter(name='Admins').exists():
        messages.error(request, 'Only administrators can delete materials.')
        return HttpResponseForbidden('Permission denied: Only administrators can delete materials.')
    
    # Check if material is used in any mixes before allowing deletion
    mixes_using_material = material_object.mix_compositions.count()
    
    if request.method == 'POST':
        # Store the material name for the success message before deletion
        material_name = material_object.name or f'ID: {material_object.pk}'
        
        # Delete the material
        material_object.delete()
        
        messages.success(request, f'Material {material_name} has been deleted.')
        return redirect('concrete_mix_app:material_list')
    
    context = {
        'material': material_object,
        'mixes_using_material': mixes_using_material,
    }
    return render(request, 'concrete_mix_app/delete_material_confirm.html', context)

# --- Mix Composition Views --- #
@login_required
@contributor_required
def edit_composition_view(request, mix_pk, comp_pk):
    '''Edit an existing mix composition entry with permission checks'''
    # Get the parent mix object or return 404
    mix_object = get_object_or_404(Concretemix, pk=mix_pk)
    
    # Get the specific composition object or return 404
    composition_object = get_object_or_404(Mixcomposition, pk=comp_pk)
    
    # Verify this composition actually belongs to the specified mix
    if composition_object.mix.pk != mix_pk:
        messages.error(request, 'Invalid request: The specified composition does not belong to this mix.')
        return HttpResponseForbidden('Permission denied: The composition does not belong to the specified mix.')
    
    # Check if user has permission to edit this mix
    if not user_can_edit_object(request.user, mix_object):
        messages.error(request, 'You do not have permission to edit this mix composition.')
        return HttpResponseForbidden('Permission denied: You can only edit mixes you created or if you are an Admin.')
    
    if request.method == 'POST':
        form = MixCompositionForm(request.POST, instance=composition_object)
        if form.is_valid():
            form.save()
            messages.success(request, f'Composition entry for {composition_object.material.name} updated successfully!')
            return redirect('concrete_mix_app:mix_detail', pk=mix_pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MixCompositionForm(instance=composition_object)
    
    context = {
        'form_title': f'Edit Composition Entry: {composition_object.material.name}',
        'form': form,
        'is_edit': True,
        'mix': mix_object,
        'composition': composition_object
    }
    return render(request, 'concrete_mix_app/generic_form.html', context)

@login_required
def delete_composition_view(request, mix_pk, comp_pk):
    '''Delete a mix composition entry with permission checks - Admin only'''
    # Get the parent mix object or return 404
    mix_object = get_object_or_404(Concretemix, pk=mix_pk)
    
    # Get the specific composition object or return 404
    composition_object = get_object_or_404(Mixcomposition, pk=comp_pk)
    
    # Verify this composition actually belongs to the specified mix
    if composition_object.mix.pk != mix_pk:
        messages.error(request, 'Invalid request: The specified composition does not belong to this mix.')
        return HttpResponseForbidden('Permission denied: The composition does not belong to the specified mix.')
    
    # Only allow admins to delete compositions
    if not request.user.is_superuser and not request.user.groups.filter(name='Admins').exists():
        messages.error(request, 'Only administrators can delete composition entries.')
        return HttpResponseForbidden('Permission denied: Only administrators can delete composition entries.')
    
    if request.method == 'POST':
        # Store the material name for the success message before deletion
        material_name = composition_object.material.name or f'ID: {composition_object.material.pk}'
        
        # Delete the composition
        composition_object.delete()
        
        messages.success(request, f'Composition entry for {material_name} has been removed from this mix.')
        return redirect('concrete_mix_app:mix_detail', pk=mix_pk)
    
    context = {
        'mix': mix_object,
        'composition': composition_object,
    }
    return render(request, 'concrete_mix_app/delete_composition_confirm.html', context)

# --- Add new dedicated view for adding mix compositions --- #
@login_required
@contributor_required
def add_composition_view(request, mix_pk):
    '''
    Dedicated view for adding a new mix composition entry to a concrete mix.
    Uses Django's standard approach for model creation and primary key handling.
    '''
    # Get the parent mix object
    mix_object = get_object_or_404(Concretemix, pk=mix_pk)
    
    # Only process POST requests
    if request.method == 'POST':
        form = MixCompositionForm(request.POST)
        if form.is_valid():
            try:
                # Standard Django pattern for saving a form with a foreign key
                new_composition = form.save(commit=False)
                new_composition.mix = mix_object  # Assign the parent mix
                new_composition.save()  # Let Django/DB handle the primary key automatically
                
                # Track object creation
                track_object_creation(request.user, new_composition)
                
                messages.success(request, 'Material added successfully.')
            except Exception as e:
                # Handle any database errors
                messages.error(request, f'Error adding material: {str(e)}')
        else:
            # Form validation failed
            messages.error(request, 'Error adding material: ' + ', '.join([f'{field}: {error[0]}' for field, error in form.errors.items()]))
    
    # Always redirect back to the mix detail page
    return redirect('concrete_mix_app:mix_detail', pk=mix_pk)

# --- Performance Result Views --- #
@login_required
@contributor_required
def edit_performance_result_view(request, mix_pk, perf_pk):
    '''Edit an existing performance result entry with permission checks'''
    # Get the parent mix object or return 404
    mix_object = get_object_or_404(Concretemix, pk=mix_pk)
    
    # Get the specific performance result object or return 404
    result_object = get_object_or_404(Performanceresult, pk=perf_pk)
    
    # Verify this result actually belongs to the specified mix
    if result_object.mix.pk != mix_pk:
        messages.error(request, 'Invalid request: The specified performance result does not belong to this mix.')
        return HttpResponseForbidden('Permission denied: The performance result does not belong to the specified mix.')
    
    # Check if user has permission to edit this mix
    if not user_can_edit_object(request.user, mix_object):
        messages.error(request, 'You do not have permission to edit this mix\'s performance results.')
        return HttpResponseForbidden('Permission denied: You can only edit mixes you created or if you are an Admin.')
    
    if request.method == 'POST':
        form = PerformanceResultForm(request.POST, instance=result_object)
        if form.is_valid():
            form.save()
            messages.success(request, f'Performance result updated successfully!')
            return redirect('concrete_mix_app:mix_detail', pk=mix_pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PerformanceResultForm(instance=result_object)
    
    context = {
        'form_title': f'Edit Performance Result: {result_object.test_type} ({result_object.test_age_days} days)',
        'form': form,
        'is_edit': True,
        'mix': mix_object,
        'result': result_object
    }
    return render(request, 'concrete_mix_app/generic_form.html', context)

@login_required
def delete_performance_result_view(request, mix_pk, perf_pk):
    '''Delete a performance result entry with permission checks - Admin only'''
    # Get the parent mix object or return 404
    mix_object = get_object_or_404(Concretemix, pk=mix_pk)
    
    # Get the specific performance result object or return 404
    result_object = get_object_or_404(Performanceresult, pk=perf_pk)
    
    # Verify this result actually belongs to the specified mix
    if result_object.mix.pk != mix_pk:
        messages.error(request, 'Invalid request: The specified performance result does not belong to this mix.')
        return HttpResponseForbidden('Permission denied: The performance result does not belong to the specified mix.')
    
    # Only allow admins to delete performance results
    if not request.user.is_superuser and not request.user.groups.filter(name='Admins').exists():
        messages.error(request, 'Only administrators can delete performance results.')
        return HttpResponseForbidden('Permission denied: Only administrators can delete performance results.')
    
    if request.method == 'POST':
        # Delete the performance result
        result_object.delete()
        
        messages.success(request, f'Performance result has been deleted successfully.')
        return redirect('concrete_mix_app:mix_detail', pk=mix_pk)
    
    context = {
        'mix': mix_object,
        'result': result_object,
    }
    return render(request, 'concrete_mix_app/delete_performance_result_confirm.html', context)

# --- Concrete Mix Views --- #
@login_required
@contributor_required
def add_mix(request):
    if request.method == 'POST':
        # Check if user has permission to add data
        if not user_can_contribute_data(request.user):
            messages.error(request, 'You do not have permission to contribute data. Please contact an administrator to request access.')
            return HttpResponseForbidden('Permission denied: You must be a Data Contributor or Admin to perform this action.')
            
        form = ConcreteMixForm(request.POST)
        if form.is_valid():
            mix = form.save(commit=False)
            mix.date_created = datetime.date.today()
            mix.save()
            
            # Track object creation by the current user
            track_object_creation(request.user, mix)
            
            messages.success(request, f'Concrete Mix "{mix.mix_code or mix.mix_id}" added successfully!')
            return redirect('concrete_mix_app:mix_detail', pk=mix.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ConcreteMixForm()
    
    context = {
        'form_title': 'Add New Concrete Mix', 
        'form': form
    }
    return render(request, 'concrete_mix_app/generic_form.html', context)

@login_required
def mix_detail(request, pk):
    mix = get_object_or_404(Concretemix, pk=pk)
    
    # Only initialize forms if user has permission to contribute data
    if user_can_contribute_data(request.user):
        composition_form = MixCompositionForm()
        performance_form = PerformanceResultForm()
        durability_form = DurabilityResultForm()
        sustainability_form = SustainabilityMetricsForm()
    else:
        composition_form = None
        performance_form = None
        durability_form = None
        sustainability_form = None
    if request.method == 'POST':
        if 'add_performance' in request.POST:
            performance_form = PerformanceResultForm(request.POST)
            if performance_form.is_valid():
                # Create a new object instance but don't save it yet
                performance_result = performance_form.save(commit=False)
                # Ensure we're creating a new record by setting pk to None
                performance_result.pk = None  # Force a new primary key to be generated
                performance_result.result_id = None  # Also clear the result_id if it exists
                # Set the foreign key relationship
                performance_result.mix = mix
                # Now save, allowing the database to generate a new primary key
                performance_result.save()
                
                # Track object creation
                track_object_creation(request.user, performance_result)
                
                messages.success(request, 'Performance result added.')
                return redirect('concrete_mix_app:mix_detail', pk=pk)
            else:
                messages.error(request, 'Error adding performance result.')
        elif 'add_durability' in request.POST:
            durability_form = DurabilityResultForm(request.POST)
            if durability_form.is_valid():
                # Create a new object instance but don't save it yet
                durability_result = durability_form.save(commit=False)
                # Ensure we're creating a new record by setting pk to None
                durability_result.pk = None  # Force a new primary key to be generated
                durability_result.result_id = None  # Also clear the result_id if it exists
                # Set the foreign key relationship
                durability_result.mix = mix
                # Now save, allowing the database to generate a new primary key
                durability_result.save()
                
                # Track object creation
                track_object_creation(request.user, durability_result)
                
                messages.success(request, 'Durability result added.')
                return redirect('concrete_mix_app:mix_detail', pk=pk)
            else:
                messages.error(request, 'Error adding durability result.')
        elif 'add_sustainability' in request.POST:
            sustainability_form = SustainabilityMetricsForm(request.POST)
            if sustainability_form.is_valid():
                # Create a new object instance but don't save it yet
                sustainability_metric = sustainability_form.save(commit=False)
                # Ensure we're creating a new record by setting pk to None
                sustainability_metric.pk = None  # Force a new primary key to be generated
                sustainability_metric.metric_id = None  # Also clear the metric_id if it exists
                # Set the foreign key relationship
                sustainability_metric.mix = mix
                # Now save, allowing the database to generate a new primary key
                sustainability_metric.save()
                
                # Track object creation
                track_object_creation(request.user, sustainability_metric)
                
                messages.success(request, 'Sustainability metrics added.')
                return redirect('concrete_mix_app:mix_detail', pk=pk)
            else:
                messages.error(request, 'Error adding sustainability metrics.')

    mix_compositions = mix.mix_compositions.select_related('material').order_by('material__material_type', 'material__name')
    performance_results = mix.performance_results.select_related('specimen').order_by('test_age_days')
    durability_results = mix.durability_results.select_related('specimen').order_by('test_age_days')
    sustainability_metrics = mix.sustainability_metrics.all()
    # Check if user can edit this mix (for template rendering purposes)
    can_edit = user_can_edit_object(request.user, mix)
    can_contribute = user_can_contribute_data(request.user)
    # Check if user is an admin (for delete permission)
    is_admin = request.user.is_superuser or request.user.groups.filter(name='Admins').exists()
    
    context = {
        'mix': mix, 
        'compositions': mix_compositions,
        'performance_results': performance_results,
        'durability_results': durability_results,
        'sustainability_metrics': sustainability_metrics,
        'composition_form': composition_form,
        'performance_form': performance_form,
        'durability_form': durability_form,
        'sustainability_form': sustainability_form,
        'can_edit': can_edit,
        'can_contribute': can_contribute,
        'is_admin': is_admin,
    }
    return render(request, 'concrete_mix_app/mix_detail.html', context)

@login_required
def mix_list_view(request):
    """Displays a filterable list of mixes, handles sorting and CSV export."""

    # --- Base Queryset --- #
    mix_list_base = Concretemix.objects.select_related('reference').all()

    # --- Apply Filters --- #
    mix_filter = ConcreteMixFilter(request.GET, queryset=mix_list_base)
    filtered_qs = mix_filter.qs

    # --- Apply Ordering --- #
    # Use a different parameter name for sorting to avoid conflict with filter fields
    sort_param = request.GET.get('sort', 'mix_code_natural') # Default to natural sort asc

    # Annotate for natural sorting
    try:
        # Improved natural sorting logic with dataset-first approach
        # 1. For sorting, prioritize the source_dataset value first (DS1, DS2, etc.)
        # 2. Within each dataset, sort by the numeric suffix
        # 
        # Example: For mix code format "DS1-123"
        # We sort first by the dataset (DS1),
        # Then by the numeric part (123)
        annotated_qs = filtered_qs.annotate(
            # Extract the trailing number for secondary sorting
            mix_code_number=RawSQL(
                "COALESCE(NULLIF(SUBSTRING(mix_code FROM '([0-9]+)$'), ''), '0')::bigint",
                [],
                output_field=BigIntegerField()
            )
        )
        # We'll order by source_dataset first, then by numeric part
        can_natural_sort = True
    except Exception as e:
        print(f"Warning: Could not annotate for natural sorting: {e}")
        annotated_qs = filtered_qs # Fallback if annotation fails
        can_natural_sort = False
        # If annotation fails, ensure we don't try to sort by natural fields
        if 'natural' in sort_param:
            sort_param = 'mix_id' # Default fallback sort

    # Determine final ordering based on the 'sort' parameter
    ordering_param = sort_param
    if sort_param == 'mix_code_natural' and can_natural_sort:
        ordered_qs = annotated_qs.order_by('source_dataset', 'mix_code_number')
    elif sort_param == '-mix_code_natural' and can_natural_sort:
        ordered_qs = annotated_qs.order_by('-source_dataset', '-mix_code_number')
    else:
        # Allow sorting by other valid model fields if needed in future, or default
        # For now, default to mix_id if natural sort fails or isn't requested
        ordered_qs = annotated_qs.order_by('mix_id')
        # Ensure the template knows the actual sort applied
        if not (ordering_param == 'mix_code_natural' and can_natural_sort):
            sort_param = 'mix_id' 

    # --- Handle CSV Export --- #
    if request.GET.get('export') == 'csv' and request.user.is_authenticated:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="concrete_mixes_export.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Mix ID', 'Mix Code', 'Date Created', 'Source Dataset', 'Region',
            'Notes', 'Reference ID',
            'Comp Str (MPa)', 'Test Age (Days)',
        ])
        mixes_to_export = ordered_qs.prefetch_related(
             Prefetch('performance_results', queryset=Performanceresult.objects.filter(test_type__icontains='compressive').order_by('test_age_days'))
        )
        for mix in mixes_to_export:
            first_perf_result = mix.performance_results.all().first()
            writer.writerow([
                mix.mix_id, mix.mix_code, mix.date_created, mix.source_dataset,
                mix.region, mix.notes, mix.reference_id,
                first_perf_result.test_value if first_perf_result else None,
                first_perf_result.test_age_days if first_perf_result else None,
            ])
        return response

    # --- Normal HTML view with pagination --- #
    prefetch_display = Prefetch(
        'performance_results',
        queryset=Performanceresult.objects.filter(test_type__icontains='compressive').order_by('test_age_days')
    )
    display_qs = ordered_qs.prefetch_related(prefetch_display)
    
    # Get page size from request or use default (25)
    try:
        page_size = int(request.GET.get('page_size', 25))
        # Limit page size to reasonable values
        page_size = min(max(page_size, 10), 100)  # Between 10 and 100
    except (ValueError, TypeError):
        page_size = 25  # Default if invalid
        
    paginator = Paginator(display_qs, page_size)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'filter': mix_filter,
        'page_obj': page_obj,
        'current_ordering': sort_param # Pass the effective sort parameter
    }
    return render(request, 'concrete_mix_app/mix_list.html', context)
