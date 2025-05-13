# inspect_lookups.py
# Script to inspect existing lookup tables in the cdb database

import os
import django

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from cdb_app import models as cdb

print("Inspecting existing lookup tables...\n")

# 1. Check Standards
print("Existing Standards:")
for std in cdb.Standard.objects.using("cdb").all().order_by('standard_id'):
    print(f"ID {std.standard_id}: {std.code} - {std.title}")

# 2. Check Units
print("\nExisting Units:")
for unit in cdb.UnitLookup.objects.using("cdb").all().order_by('unit_id'):
    print(f"ID {unit.unit_id}: {unit.unit_symbol} - {unit.description}")

# 3. Check Test Methods
print("\nExisting Test Methods:")
for test in cdb.TestMethod.objects.using("cdb").all().order_by('test_method_id'):
    std_code = test.standard.code if test.standard else "None"
    print(f"ID {test.test_method_id}: {test.description} - Standard: {std_code}, Unit: {test.default_unit_id}")

# 4. Check Curing Regimes
print("\nExisting Curing Regimes:")
for regime in cdb.CuringRegime.objects.using("cdb").all().order_by('curing_id'):
    print(f"ID {regime.curing_id}: {regime.regime_name} - {regime.description}")

# 5. Check Specimens
print("\nExisting Specimens:")
for specimen in cdb.Specimen.objects.using("cdb").all().order_by('specimen_id'):
    dimensions = f"{specimen.width_mm}×{specimen.height_mm}×{specimen.length_mm}" if specimen.width_mm else "Variable"
    print(f"ID {specimen.specimen_id}: {specimen.name} - Dimensions: {dimensions}, Type: {specimen.type_code}")
