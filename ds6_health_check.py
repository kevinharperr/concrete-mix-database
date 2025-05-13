import os
import sys
import csv
import django
from decimal import Decimal
from datetime import datetime
from collections import defaultdict, Counter

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import Django models
from cdb_app import models as cdb

def run_health_check(dataset_name='DS6', output_file='ds6_health_check.csv'):
    """Run health checks on DS6 dataset and report results to CSV"""
    print(f"Running health check for {dataset_name} dataset...")
    
    # Get the dataset record
    try:
        dataset = cdb.Dataset.objects.using('cdb').get(dataset_name=dataset_name)
        print(f"Found {dataset_name} dataset: {dataset}")
    except cdb.Dataset.DoesNotExist:
        print(f"Error: {dataset_name} dataset not found")
        return
    
    # Initialize metrics dictionary
    metrics = defaultdict(list)
    
    # 1. Basic count metrics
    mixes = cdb.ConcreteMix.objects.using('cdb').filter(dataset=dataset)
    mix_count = mixes.count()
    metrics['count'].append(('total_mixes', mix_count))
    print(f"Found {mix_count} mixes")
    
    # 2. Check mix components
    total_components = 0
    component_counts = Counter()
    material_ids = set()
    for mix in mixes:
        components = cdb.MixComponent.objects.using('cdb').filter(mix=mix)
        mix_component_count = components.count()
        total_components += mix_component_count
        for comp in components:
            component_counts[comp.material.material_class.class_code] += 1
            material_ids.add(comp.material.material_id)
    
    metrics['count'].append(('total_components', total_components))
    metrics['count'].append(('average_components_per_mix', round(total_components / mix_count if mix_count else 0, 2)))
    metrics['count'].append(('unique_materials', len(material_ids)))
    print(f"Found {total_components} components using {len(material_ids)} unique materials")
    
    # Component type distribution
    for material_class, count in component_counts.items():
        metrics['component_distribution'].append((material_class, count))
    
    # 3. Check material properties
    properties_count = 0
    property_types = Counter()
    property_by_material = defaultdict(int)
    
    for material_id in material_ids:
        try:
            material = cdb.Material.objects.using('cdb').get(material_id=material_id)
            props = cdb.MaterialProperty.objects.using('cdb').filter(material=material)
            material_props_count = props.count()
            properties_count += material_props_count
            property_by_material[material.specific_name] = material_props_count
            
            for prop in props:
                property_types[prop.property_name.property_name] += 1
        except Exception as e:
            print(f"Error checking properties for material {material_id}: {e}")
    
    metrics['count'].append(('total_material_properties', properties_count))
    metrics['count'].append(('unique_property_types', len(property_types)))
    metrics['count'].append(('average_properties_per_material', 
                            round(properties_count / len(material_ids) if material_ids else 0, 2)))
    print(f"Found {properties_count} material properties of {len(property_types)} different types")
    
    # 4. Check aggregate details
    agg_details_count = 0
    agg_detail_fields = Counter()
    agg_by_material = defaultdict(int)
    
    for material_id in material_ids:
        try:
            material = cdb.Material.objects.using('cdb').get(material_id=material_id)
            if material.material_class.class_code.startswith('AGGR'):
                details = cdb.AggregateDetail.objects.using('cdb').filter(material=material)
                details_count = details.count()
                agg_details_count += details_count
                agg_by_material[material.specific_name] = details_count
                
                for detail in details:
                    # Count non-null fields
                    if detail.bulk_density_kg_m3:
                        agg_detail_fields['bulk_density_kg_m3'] += 1
                    if detail.water_absorption_pct:
                        agg_detail_fields['water_absorption_pct'] += 1
                    if detail.fineness_modulus:
                        agg_detail_fields['fineness_modulus'] += 1
                    if detail.d_upper_mm:
                        agg_detail_fields['d_upper_mm'] += 1
                    if detail.d_lower_mm:
                        agg_detail_fields['d_lower_mm'] += 1
        except Exception as e:
            print(f"Error checking aggregate details for material {material_id}: {e}")
    
    metrics['count'].append(('total_aggregate_details', agg_details_count))
    agg_materials = sum(1 for m_id in material_ids if 
                      cdb.Material.objects.using('cdb').get(material_id=m_id).material_class.class_code.startswith('AGGR'))
    metrics['count'].append(('aggregate_materials', agg_materials))
    metrics['count'].append(('average_details_per_aggregate', 
                            round(agg_details_count / agg_materials if agg_materials else 0, 2)))
    print(f"Found {agg_details_count} aggregate details for {agg_materials} aggregate materials")
    
    # 5. Check performance results
    results_count = 0
    result_categories = Counter()
    results_by_mix = defaultdict(int)
    
    for mix in mixes:
        results = cdb.PerformanceResult.objects.using('cdb').filter(mix=mix)
        mix_results_count = results.count()
        results_count += mix_results_count
        results_by_mix[mix.mix_code] = mix_results_count
        
        for result in results:
            result_categories[result.category] += 1
    
    metrics['count'].append(('total_performance_results', results_count))
    metrics['count'].append(('result_categories', len(result_categories)))
    metrics['count'].append(('average_results_per_mix', 
                           round(results_count / mix_count if mix_count else 0, 2)))
    print(f"Found {results_count} performance results in {len(result_categories)} categories")
    
    # 6. Check for issues
    issues_found = []
    
    # Check mixes with no components
    mixes_no_components = sum(1 for mix in mixes if 
                             cdb.MixComponent.objects.using('cdb').filter(mix=mix).count() == 0)
    metrics['issues'].append(('mixes_with_no_components', mixes_no_components))
    if mixes_no_components > 0:
        issues_found.append(f"{mixes_no_components} mixes have no components")
    
    # Check for materials with no properties
    materials_no_props = sum(1 for mat_id in material_ids if 
                           cdb.MaterialProperty.objects.using('cdb').filter(
                               material_id=mat_id).count() == 0)
    metrics['issues'].append(('materials_with_no_properties', materials_no_props))
    
    # Check for aggregate materials with no details
    agg_no_details = sum(1 for mat_id in material_ids if 
                        cdb.Material.objects.using('cdb').get(material_id=mat_id).material_class.class_code.startswith('AGGR') and
                        cdb.AggregateDetail.objects.using('cdb').filter(material_id=mat_id).count() == 0)
    metrics['issues'].append(('aggregates_with_no_details', agg_no_details))
    
    # Check for mixes with no performance results
    mixes_no_results = sum(1 for mix in mixes if 
                          cdb.PerformanceResult.objects.using('cdb').filter(mix=mix).count() == 0)
    metrics['issues'].append(('mixes_with_no_results', mixes_no_results))
    
    # Write results to CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Category', 'Metric', 'Value'])
        
        # Write all metrics
        for category, items in metrics.items():
            for metric, value in items:
                writer.writerow([category, metric, value])
        
        # Write component distribution
        for material_class, count in component_counts.items():
            writer.writerow(['component_distribution', material_class, count])
        
        # Write property type distribution
        for prop_name, count in property_types.items():
            writer.writerow(['property_type_distribution', prop_name, count])
        
        # Write aggregate detail field distribution
        for field_name, count in agg_detail_fields.items():
            writer.writerow(['aggregate_detail_fields', field_name, count])
        
        # Write result category distribution
        for category, count in result_categories.items():
            writer.writerow(['result_category_distribution', category, count])
    
    print(f"Health check complete. Results written to {output_file}")
    if issues_found:
        print("\nIssues found:")
        for issue in issues_found:
            print(f"- {issue}")
    else:
        print("\nNo major issues found.")

if __name__ == "__main__":
    run_health_check()
