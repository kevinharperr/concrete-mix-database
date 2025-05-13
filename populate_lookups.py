# populate_lookups.py
# Script to populate standard lookup tables for future imports

import os
import django

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from cdb_app import models as cdb

print("Starting lookup tables population...")

# 1. Standards
standards = [
    # Standards related to concrete testing
    (1, "EN 12390-3", "Testing hardened concrete - Compressive strength of test specimens"),
    (2, "EN 12390-5", "Testing hardened concrete - Flexural strength of test specimens"),
    (3, "EN 12350-2", "Testing fresh concrete - Slump test"),
    (4, "EN 12350-6", "Testing fresh concrete - Density"),
    (5, "EN 12350-7", "Testing fresh concrete - Air content"),
    (6, "ASTM C39", "Standard Test Method for Compressive Strength of Cylindrical Concrete Specimens"),
    (7, "ASTM C78", "Standard Test Method for Flexural Strength of Concrete"),
    (8, "ASTM C143", "Standard Test Method for Slump of Hydraulic-Cement Concrete"),
    (9, "ASTM C231", "Standard Test Method for Air Content of Freshly Mixed Concrete"),
    # Standards related to cement
    (10, "EN 197-1", "Cement composition, specifications and conformity criteria"),
    (11, "ASTM C150", "Standard Specification for Portland Cement"),
    # Standards related to admixtures
    (12, "EN 934-2", "Admixtures for concrete, mortar and grout"),
    (13, "ASTM C494", "Standard Specification for Chemical Admixtures for Concrete"),
    # Standards for aggregates
    (14, "EN 12620", "Aggregates for concrete"),
    (15, "ASTM C33", "Standard Specification for Concrete Aggregates"),
]

print("\nPopulating Standards table...")
for std_id, code, title in standards:
    obj, created = cdb.Standard.objects.using("cdb").update_or_create(
        standard_id=std_id,
        defaults={
            "code": code,
            "title": title
        }
    )
    status = "Created" if created else "Updated"
    print(f"{status} Standard ID {std_id}: {code} - {title}")

# 2. Unit Lookup
units = [
    # Basic units
    (1, "kg", "Kilogram"),
    (2, "g", "Gram"),
    (3, "m", "Meter"),
    (4, "mm", "Millimeter"),
    (5, "L", "Liter"),
    (6, "MPa", "Megapascal"),
    (7, "psi", "Pounds per square inch"),
    (8, "N", "Newton"),
    (9, "kN", "Kilonewton"),
    # Derived units
    (10, "kg/m³", "Kilograms per cubic meter"),
    (11, "mm/min", "Millimeters per minute"),
    (12, "°C", "Degrees Celsius"),
    (13, "%", "Percent"),
    (14, "cm", "Centimeter"),
    (15, "s", "Second"),
    (16, "min", "Minute"),
    (17, "hr", "Hour"),
    (18, "day", "Day"),
    (19, "m²/kg", "Square meters per kilogram"),
    (20, "mL/kg", "Milliliters per kilogram"),
]

print("\nPopulating UnitLookup table...")
for unit_id, symbol, desc in units:
    # First check if unit with this symbol already exists
    try:
        existing_unit = cdb.UnitLookup.objects.using("cdb").get(unit_symbol=symbol)
        # If it exists but has a different ID, print a warning and skip
        if existing_unit.unit_id != unit_id:
            print(f"Warning: Unit '{symbol}' already exists with ID {existing_unit.unit_id} (attempted to assign ID {unit_id})")
            continue
        # Otherwise, update it
        existing_unit.description = desc
        existing_unit.save(using="cdb")
        print(f"Updated Unit ID {existing_unit.unit_id}: {symbol} ({desc})")
    except cdb.UnitLookup.DoesNotExist:
        # Unit doesn't exist, create it
        obj = cdb.UnitLookup.objects.using("cdb").create(
            unit_id=unit_id,
            unit_symbol=symbol,
            description=desc
        )
        print(f"Created Unit ID {unit_id}: {symbol} ({desc})")

# 3. Test Methods
test_methods = [
    # Hardened concrete tests
    (1, "Compressive strength - Cube", 1, 6, "hardened"),
    (2, "Compressive strength - Cylinder", 1, 6, "hardened"),
    (3, "Flexural strength", 2, 6, "hardened"),
    (4, "Splitting tensile strength", 2, 6, "hardened"),
    (5, "Elastic modulus", 2, 6, "hardened"),
    (6, "Density", 4, 10, "hardened"),
    # Fresh concrete tests
    (7, "Slump", 3, 4, "fresh"),
    (8, "Flow table", 3, 4, "fresh"),
    (9, "Air content", 5, 13, "fresh"),
    (10, "Fresh density", 4, 10, "fresh"),
    (11, "Temperature", None, 12, "fresh"),
    # Durability tests
    (12, "Chloride migration coefficient", None, 19, "durability"),
    (13, "Carbonation depth", None, 4, "durability"),
    (14, "Freeze-thaw resistance", None, 13, "durability"),
    (15, "Water absorption", None, 13, "durability"),
]

print("\nPopulating TestMethod table...")
for test_id, desc, std_id, unit_id, category in test_methods:
    standard = None
    if std_id:
        try:
            standard = cdb.Standard.objects.using("cdb").get(standard_id=std_id)
        except cdb.Standard.DoesNotExist:
            print(f"Warning: Standard ID {std_id} not found, skipping TestMethod ID {test_id}")
            continue
            
    # Check if test method already exists
    try:
        existing_test = cdb.TestMethod.objects.using("cdb").get(test_method_id=test_id)
        # Update existing test method
        existing_test.description = desc
        existing_test.standard = standard
        existing_test.default_unit_id = unit_id
        existing_test.category = category
        existing_test.save(using="cdb")
        print(f"Updated Test Method ID {test_id}: {desc}")
    except cdb.TestMethod.DoesNotExist:
        # Create new test method
        cdb.TestMethod.objects.using("cdb").create(
            test_method_id=test_id,
            description=desc,
            standard=standard,
            default_unit_id=unit_id,
            category=category
        )
        print(f"Created Test Method ID {test_id}: {desc}")

# 4. Curing Regimes
curing_regimes = [
    (1, "Standard", "20±2°C, RH ≥ 95%", "EN 12390-2"),
    (2, "Accelerated", "60±2°C, water immersion", None),
    (3, "Accelerated steam", "65±5°C, 100% RH", None),
    (4, "Air curing", "20±2°C, RH 65±5%", None),
    (5, "Real-world exposure", "Ambient outdoor conditions", None),
    (6, "Sealed curing", "No moisture exchange with environment", None),
    (7, "Water immersion", "20±2°C, completely submerged", None),
]

print("\nPopulating CuringRegime table...")
for regime_id, name, desc, reference in curing_regimes:
    # Check if curing regime already exists
    try:
        existing_regime = cdb.CuringRegime.objects.using("cdb").get(curing_id=regime_id)
        # Update existing regime
        existing_regime.regime_name = name
        existing_regime.description = desc
        existing_regime.reference = reference
        existing_regime.save(using="cdb")
        print(f"Updated Curing Regime ID {regime_id}: {name}")
    except cdb.CuringRegime.DoesNotExist:
        # Create new curing regime
        cdb.CuringRegime.objects.using("cdb").create(
            curing_id=regime_id,
            regime_name=name,
            description=desc,
            reference=reference
        )
        print(f"Created Curing Regime ID {regime_id}: {name}")

# 5. Specimen Types
specimen_types = [
    (1, "Cube 100mm", 100, 100, 100, 1),
    (2, "Cube 150mm", 150, 150, 150, 1),
    (3, "Cylinder 100x200mm", 100, 100, 200, 2),
    (4, "Cylinder 150x300mm", 150, 150, 300, 2),
    (5, "Beam 100x100x500mm", 100, 100, 500, 3),
    (6, "Beam 150x150x750mm", 150, 150, 750, 3),
    (7, "Cylinder 75x150mm", 75, 75, 150, 2),
    (8, "Core sample", None, None, None, 4),
]

print("\nPopulating Specimen table...")
for specimen_id, name, width, height, length, type_code in specimen_types:
    # Check if specimen already exists
    try:
        existing_specimen = cdb.Specimen.objects.using("cdb").get(specimen_id=specimen_id)
        # Update existing specimen
        existing_specimen.name = name
        existing_specimen.width_mm = width
        existing_specimen.height_mm = height
        existing_specimen.length_mm = length
        existing_specimen.type_code = type_code
        existing_specimen.save(using="cdb")
        print(f"Updated Specimen ID {specimen_id}: {name}")
    except cdb.Specimen.DoesNotExist:
        # Create new specimen
        cdb.Specimen.objects.using("cdb").create(
            specimen_id=specimen_id,
            name=name,
            width_mm=width,
            height_mm=height,
            length_mm=length,
            type_code=type_code
        )
        print(f"Created Specimen ID {specimen_id}: {name}")

print("\nLookup tables population complete!")

# 6. Create a documentation file with all the lookup IDs
doc_content = """
# Lookup Tables Reference

This document provides the canonical IDs for lookup tables used in the concrete database import process.

## Standard IDs

| ID | Code | Title |
|---|---|---|
{}

## Unit IDs

| ID | Symbol | Description |
|---|---|---|
{}

## Test Method IDs

| ID | Description | Standard | Default Unit | Category |
|---|---|---|---|---|
{}

## Curing Regime IDs

| ID | Name | Description | Reference |
|---|---|---|---|
{}

## Specimen IDs

| ID | Name | Dimensions (mm) | Type Code |
|---|---|---|---|
{}
"""

# Format standard rows
standard_rows = "\n".join([f"| {std_id} | {code} | {title} |" for std_id, code, title in standards])

# Format unit rows
unit_rows = "\n".join([f"| {unit_id} | {symbol} | {desc} |" for unit_id, symbol, desc in units])

# Format test method rows
test_method_rows = []
for test_id, desc, std_id, unit_id, category in test_methods:
    std_code = next((code for s_id, code, _ in standards if s_id == std_id), "N/A")
    unit_symbol = next((symbol for u_id, symbol, _, _ in units if u_id == unit_id), "N/A")
    test_method_rows.append(f"| {test_id} | {desc} | {std_code} | {unit_symbol} | {category} |")
test_method_rows_str = "\n".join(test_method_rows)

# Format curing regime rows
curing_rows = "\n".join([f"| {regime_id} | {name} | {desc} | {reference or 'None'} |" for regime_id, name, desc, reference in curing_regimes])

# Format specimen rows
specimen_rows = []
for specimen_id, name, width, height, length, type_code in specimen_types:
    dimensions = "Variable" if width is None else f"{width}×{height}×{length}"
    specimen_rows.append(f"| {specimen_id} | {name} | {dimensions} | {type_code} |")
specimen_rows_str = "\n".join(specimen_rows)

# Fill in the document content
doc_content = doc_content.format(
    standard_rows,
    unit_rows,
    test_method_rows_str,
    curing_rows,
    specimen_rows_str
)

# Create docs directory if it doesn't exist
if not os.path.exists('docs'):
    os.makedirs('docs')

# Write the documentation file
with open('docs/lookup_ids.md', 'w') as f:
    f.write(doc_content)

print("Created documentation file at docs/lookup_ids.md")
