
# DS6 Import Fix - Material Reference System Approach

**NOTE: This document contains the previous fix instructions which have been superseded by the Material Reference System implementation (May 7, 2025).**

## Issues Successfully Resolved

The following issues with the DS6 dataset import have been successfully fixed using the material reference system approach:

1. Material properties and aggregate details not linking properly to materials during import
2. Missing material_id warnings during import process
3. Performance results not being imported due to incorrect column mappings

## ✅ Successful Solution: Material Reference System

Instead of using the approaches outlined below, we implemented a more elegant material reference system that:

1. Tracks materials by reference keys during import
2. Links properties and aggregate details to materials using these reference keys
3. Correctly maps performance result columns for accurate import

### Implementation Details

1. Updated `import_ds.py` to track materials with a reference key system:
   ```python
   # Track materials with reference keys during import
   material_refs = {}
   
   # In mix_component section
   if reference_key:
       material_refs[reference_key] = material_object
   
   # In material_property section
   if material_ref_key and material_ref_key in material_refs:
       material = material_refs[material_ref_key]
   ```

2. Created proper mapping files with reference keys for all materials:
   ```
   python create_corrected_mapping.py
   ```

3. Successfully imported all data with the corrected mapping:
   ```
   python manage.py import_ds DS6 ./etl/ds6.csv --map ./etl/ds6_corrected_mapping.csv
   ```

### Results

- Successfully imported all 654 mixes with properly linked material properties
- Imported 2,114 performance results with 95.1% of mixes having 28-day strength data
- No manual SQL fixes or property linking required

## Future Process for DS6 and Other Datasets

1. Create comprehensive mapping files with reference keys for all materials
2. Apply the same reference key approach to all future dataset imports
3. Use the health check and health flags scripts to validate imports

---

## ⚠️ [OLD] Previous Fix Instructions (No Longer Needed)

The following were the previously proposed fix steps that are no longer needed:

1. Run SQL queries to update mix codes
2. Re-run import with --link-only parameter
3. Update import_ds.py with a --link-only option
4. Use manual SQL fixes for property linking

These steps have been replaced by the material reference system approach.
