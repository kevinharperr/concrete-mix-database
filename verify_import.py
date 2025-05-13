# verify_import.py
# Script to verify the imported data

import os
import django

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from cdb_app import models as cdb
from django.db.models import Count, Avg, Max, Min

# Check how many mixes were imported
mix_count = cdb.ConcreteMix.objects.using("cdb").filter(dataset__dataset_name="DS1").count()
print(f"\nTotal DS1 mixes imported: {mix_count}")

# Check mix components
component_count = cdb.MixComponent.objects.using("cdb").filter(
    mix__dataset__dataset_name="DS1"
).count()
print(f"Total mix components created: {component_count}")

# Average components per mix
avg_components = cdb.MixComponent.objects.using("cdb").filter(
    mix__dataset__dataset_name="DS1"
).values('mix_id').annotate(count=Count('component_id')).aggregate(Avg('count'))
print(f"Average components per mix: {avg_components['count__avg']:.2f}")

# Check performance results
perf_count = cdb.PerformanceResult.objects.using("cdb").filter(
    mix__dataset__dataset_name="DS1"
).count()
print(f"Total performance results created: {perf_count}")

# Materials created
material_count = cdb.Material.objects.using("cdb").filter(
    source_dataset="DS1"
).count()
print(f"\nMaterials created/used: {material_count}")

# Distribution by material class
print("\nMaterial distribution by class:")
class_counts = cdb.Material.objects.using("cdb").values(
    'material_class_id'
).annotate(count=Count('material_id')).order_by('material_class_id')
for c in class_counts:
    print(f"  {c['material_class_id']}: {c['count']} materials")

# Mix properties summary
w_c_stats = cdb.ConcreteMix.objects.using("cdb").filter(
    dataset__dataset_name="DS1",
    w_c_ratio__isnull=False
).aggregate(Min('w_c_ratio'), Max('w_c_ratio'), Avg('w_c_ratio'))
# Handle if no mixes have w_c_ratio set
if w_c_stats['w_c_ratio__min'] is None:
    print(f"\nNo water-cement ratio data available")
else:
    print(f"\nWater-cement ratio range: {w_c_stats['w_c_ratio__min']} - {w_c_stats['w_c_ratio__max']} (avg: {w_c_stats['w_c_ratio__avg']:.2f})")

# Check strength results
strength_stats = cdb.PerformanceResult.objects.using("cdb").filter(
    mix__dataset__dataset_name="DS1",
    test_method_id=2,  # Compressive strength - Cylinder
    category="hardened"
).aggregate(
    Min('value_num'), 
    Max('value_num'), 
    Avg('value_num')
)
# Handle if no performance results exist
if strength_stats['value_num__min'] is None:
    print(f"No strength test results found")
else:
    print(f"Strength range: {strength_stats['value_num__min']} - {strength_stats['value_num__max']} MPa (avg: {strength_stats['value_num__avg']:.2f} MPa)")

# Check for any mixes without components
mixes_without_components = cdb.ConcreteMix.objects.using("cdb").filter(
    dataset__dataset_name="DS1"
).annotate(comp_count=Count('components')).filter(comp_count=0).count()
print(f"\nMixes without any components: {mixes_without_components}")

# Check for any duplicate mix codes
duplicate_mix_codes = cdb.ConcreteMix.objects.using("cdb").filter(
    dataset__dataset_name="DS1"
).values('mix_code').annotate(count=Count('mix_id')).filter(count__gt=1).count()
print(f"Duplicate mix codes found: {duplicate_mix_codes}")
