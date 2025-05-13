# finalize_lookups.py
# Script to finalize lookup tables for future imports

import os
import django

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from cdb_app import models as cdb

print("Starting lookup tables finalization...")

# Add additional units that don't already exist
additional_units = [
    (8, "N", "Newton"),
    (9, "kN", "Kilonewton"),
    (10, "L", "Liter"),
    (11, "mm/min", "Millimeters per minute"),
    (12, "°C", "Degrees Celsius"),
    (13, "%", "Percent"),
    (14, "cm", "Centimeter"),
    (15, "s", "Second"),
    (16, "hr", "Hour"),
    (17, "day", "Day"),
    (18, "m²/kg", "Square meters per kilogram"),
    (19, "mL/kg", "Milliliters per kilogram"),
]

print("\nAdding additional units...")
for unit_id, symbol, desc in additional_units:
    # Check if unit ID or symbol already exists
    if cdb.UnitLookup.objects.using("cdb").filter(unit_id=unit_id).exists():
        print(f"Unit ID {unit_id} already exists, skipping")
        continue
    if cdb.UnitLookup.objects.using("cdb").filter(unit_symbol=symbol).exists():
        print(f"Unit '{symbol}' already exists with different ID, skipping")
        continue
    
    # Create new unit
    cdb.UnitLookup.objects.using("cdb").create(
        unit_id=unit_id,
        unit_symbol=symbol,
        description=desc
    )
    print(f"Created Unit ID {unit_id}: {symbol} ({desc})")

# Add test methods that don't already exist
print("\nAdding test methods...")
test_methods = [
    # Using existing test methods with IDs 1 and 2 since they're already in use
    # Adding additional test methods - just name and standard
    (3, "Flexural strength", 2),
    (4, "Splitting tensile strength", 2),
    (5, "Elastic modulus", 2),
    (6, "Density of hardened concrete", 4),
    (7, "Slump test", 3),
    (8, "Flow table test", 3),
    (9, "Air content measurement", 5),
    (10, "Fresh concrete density", 4),
    (11, "Temperature measurement", None),
    (12, "Chloride migration coefficient", None),
    (13, "Carbonation depth", None),
    (14, "Freeze-thaw resistance", None),
    (15, "Water absorption", None),
]

for test_id, desc, std_id in test_methods:
    # Skip if already exists
    if cdb.TestMethod.objects.using("cdb").filter(test_method_id=test_id).exists():
        print(f"Test Method ID {test_id} already exists, skipping")
        continue
        
    # Get standard if specified
    standard = None
    if std_id:
        try:
            standard = cdb.Standard.objects.using("cdb").get(standard_id=std_id)
        except cdb.Standard.DoesNotExist:
            print(f"Warning: Standard ID {std_id} not found, skipping TestMethod ID {test_id}")
            continue
            
    # Create test method - only using fields that exist in the model
    cdb.TestMethod.objects.using("cdb").create(
        test_method_id=test_id,
        description=desc,
        standard=standard
    )
    print(f"Created Test Method ID {test_id}: {desc}")

# Add curing regimes - curing_regime_id is the primary key from the model
print("\nAdding curing regimes...")
curing_regimes = [
    (1, "Standard curing (20+/-2 C, RH >= 95%)"),
    (2, "Accelerated curing (60+/-2 C, water immersion)"),
    (3, "Accelerated steam curing (65+/-5 C, 100% RH)"),
    (4, "Air curing (20+/-2 C, RH 65+/-5%)"),
    (5, "Real-world exposure (Ambient outdoor conditions)"),
    (6, "Sealed curing (No moisture exchange with environment)"),
    (7, "Water immersion (20+/-2 C, completely submerged)"),
]

for regime_id, desc in curing_regimes:
    # Skip if already exists
    if cdb.CuringRegime.objects.using("cdb").filter(curing_regime_id=regime_id).exists():
        print(f"Curing Regime ID {regime_id} already exists, skipping")
        continue
        
    # Create new curing regime
    cdb.CuringRegime.objects.using("cdb").create(
        curing_regime_id=regime_id,
        description=desc
    )
    print(f"Created Curing Regime ID {regime_id}: {desc}")

# Note: Specimen types aren't standalone in the actual database - they must be linked to a ConcreteMix
# We'll create a documentation entry for standard specimen shapes instead
standard_specimens = [
    ("Cube 100mm", "Cube", 100, 100),  # shape, length, diameter
    ("Cube 150mm", "Cube", 150, 150),
    ("Cylinder 100x200mm", "Cylinder", 200, 100),
    ("Cylinder 150x300mm", "Cylinder", 300, 150),
    ("Beam 100x100x500mm", "Beam", 500, 100),
    ("Beam 150x150x750mm", "Beam", 750, 150),
    ("Cylinder 75x150mm", "Cylinder", 150, 75),
    ("Core sample", "Cylinder", None, None),
]

print("\nDocumenting standard specimen types in lookup file...")

print("\nLookup tables finalization complete!")

# Create documentation
doc_content = """
# Lookup Tables Reference

This document provides the canonical IDs for lookup tables used in the concrete database import process.

## Unit IDs

| ID | Symbol | Description |
|---|---|---|
{}

## Test Method IDs

| ID | Description | Standard |
|---|---|---|
{}

## Curing Regime IDs

| ID | Description |
|---|---|
{}

## Standard Specimen Shapes

| ID | Name | Shape | Dimensions |
|---|---|---|---|
{}
"""

# Format unit rows
unit_rows = []
for unit in cdb.UnitLookup.objects.using("cdb").all().order_by('unit_id'):
    unit_rows.append(f"| {unit.unit_id} | {unit.unit_symbol} | {unit.description} |")
unit_rows_str = "\n".join(unit_rows)

# Format test method rows
test_rows = []
for test in cdb.TestMethod.objects.using("cdb").all().order_by('test_method_id'):
    std_code = test.standard.code if test.standard else "N/A"
    test_rows.append(f"| {test.test_method_id} | {test.description} | {std_code} |")
test_rows_str = "\n".join(test_rows)

# Format curing regime rows
curing_rows = []
for regime in cdb.CuringRegime.objects.using("cdb").all().order_by('curing_regime_id'):
    curing_rows.append(f"| {regime.curing_regime_id} | {regime.description} |")
curing_rows_str = "\n".join(curing_rows)

# Format standard specimen shapes
specimen_rows = []
for i, (name, shape, length, diameter) in enumerate(standard_specimens, 1):
    if length is None:
        dimensions = "Variable"
    elif shape == "Cube":
        dimensions = f"{length}×{length}×{length} mm"
    elif shape == "Cylinder":
        dimensions = f"{diameter}×{length} mm (diameter×length)"
    else:  # Beam
        dimensions = f"{diameter}×{diameter}×{length} mm (width×height×length)"
    specimen_rows.append(f"| {i} | {name} | {shape} | {dimensions} |")
specimen_rows_str = "\n".join(specimen_rows)

# Fill in the document content
doc_content = doc_content.format(
    unit_rows_str,
    test_rows_str,
    curing_rows_str,
    specimen_rows_str
)

# Create docs directory if it doesn't exist
if not os.path.exists('docs'):
    os.makedirs('docs')

# Write the documentation file
with open('docs/lookup_ids.md', 'w', encoding='utf-8') as f:
    f.write(doc_content)

print("Created documentation file at docs/lookup_ids.md")
