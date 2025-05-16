import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import models
from cdb_app.models import ConcreteMix, PerformanceResult, TestMethod, UnitLookup
from django.db.models import Field

# Print model field information
def print_model_info(model_class):
    print(f"Model: {model_class.__name__}")
    print(f"Primary key field: {model_class._meta.pk.name}")
    print("Fields:")
    for field in model_class._meta.get_fields():
        if isinstance(field, Field):
            print(f"  - {field.name}: {field.__class__.__name__} {'(Primary Key)' if field.primary_key else ''}")
    print()

# Check all relevant models
for model in [PerformanceResult, UnitLookup, TestMethod]:
    print_model_info(model)

# Check existing unit lookups
print("\nExisting UnitLookup records:")
for unit in UnitLookup.objects.all():
    unit_dict = {field.name: getattr(unit, field.name) for field in UnitLookup._meta.fields}
    print(f"- {unit_dict}")

# Check test methods
print("\nExisting TestMethod records:")
for method in TestMethod.objects.all()[:5]:  # Limit to first 5 for brevity
    test_dict = {field.name: getattr(method, field.name) for field in TestMethod._meta.fields}
    print(f"- {test_dict}")

# Check if a specific test method exists
print("\nLooking for 'EN 12390-3 Compressive Test' method:")
compressive_tests = TestMethod.objects.filter(description__icontains="compressive")
for method in compressive_tests:
    print(f"- {method.id}: {method.description}")

# Check if a specific unit exists
print("\nLooking for 'MPa' unit:")
mpa_units = UnitLookup.objects.filter(unit_symbol__iexact="MPa")
for unit in mpa_units:
    unit_dict = {field.name: getattr(unit, field.name) for field in UnitLookup._meta.fields}
    print(f"- {unit_dict}")
