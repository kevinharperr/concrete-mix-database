# Material Reference System Documentation

## Overview

The Material Reference System is a key enhancement to the concrete mix database import process. It allows for reliable linking of material properties and aggregate details by tracking materials with reference keys rather than relying on direct material IDs.

## How It Works

### Core Concept
During import, materials are tracked in a dictionary called `material_refs` where:
- The key is a string identifier (the "reference key") that uniquely identifies a material within the import context
- The value is the actual Material object that has been created or retrieved from the database

### Implementation Details

1. **Material Creation Phase**:
   ```python
   # In mix_component section
   if reference_key:
       material_refs[reference_key] = material_object
   ```

2. **Material Property Linking**:
   ```python
   # In material_property section
   if material_ref_key and material_ref_key in material_refs:
       material = material_refs[material_ref_key]
   ```

3. **Aggregate Detail Linking**:
   ```python
   # In aggregate_detail section
   if material_ref_key and material_ref_key in material_refs:
       material = material_refs[material_ref_key]
   ```

## Creating Mapping Files

### Column Mapping Format

The column mapping CSV has these fields:
- `source_column`: The column name in your source CSV file
- `target_table`: The database table this column maps to
- `target_column`: The database column this source column maps to
- `extra_kwargs`: Additional parameters as a JSON object

### Reference Key Usage

1. **Defining Materials**:
   ```csv
   "Cement (kg/m3)",mix_component,dosage_kg_m3,{"class_code":"CEMENT", "subtype_code":"CEM I", "specific_name":"Ordinary Portland Cement", "is_cementitious":true, "reference_key":"CEMENT"}
   ```

2. **Linking Properties**:
   ```csv
   cement_sio2_pct,material_property,value_num,{"property_name": "sio2_pct", "property_group": "chemical", "material_ref_key": "CEMENT"}
   ```

3. **Linking Aggregate Details**:
   ```csv
   nca_sg,aggregate_detail,bulk_density_kg_m3,{"material_ref_key": "NCA"}
   ```

## Best Practices

### Reference Key Naming
- Use uppercase, simple names that clearly identify the material (e.g., "CEMENT", "FA", "NCA")
- Be consistent across different mapping files for the same material types
- Document the reference keys used in your mapping files

### JSON Formatting
- Ensure JSON in the extra_kwargs column is properly formatted
- Use the provided scripts (create_formatted_mapping.py) to generate mapping files with valid JSON
- Test your mapping file with small datasets before running full imports

### Validation
- Verify that all required properties and aggregate details have corresponding material references
- Check that reference keys are defined before they are referenced
- Run health checks after import to verify data quality

## Example Workflow

1. Create materials with reference keys
2. Link material properties to those materials using the same reference keys
3. Link aggregate details to aggregate materials using their reference keys
4. Run the import with the mapping file
5. Generate health flags to verify data quality

## Future Enhancements

- Standardize reference keys across all datasets
- Create a library of common material reference keys
- Develop automated validation for mapping files
- Enhance error reporting for reference key issues
