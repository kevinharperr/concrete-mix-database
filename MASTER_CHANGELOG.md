# Concrete Mix Database - Master Changelog

## Last Updated: May 7, 2025, 15:52

## Overview
This master changelog documents all significant database operations, fixes, and data changes made to the concrete mix database.

---

## Database Integrity Fix (May 6, 2025, 20:35)

### Issues Identified
- **Non-standard Mix Codes**: 1,500 mixes (27% of database) had non-standard naming without the DS#-## format
- **ID Sequencing**: Mix IDs ranged from 6 to 13840 with large gaps, indicating deleted records
- **Inconsistent Naming**: Particularly in DS4 dataset where mix codes were simple numbers ("1", "2", "3") instead of "DS4-1", etc.
- **Potential Duplicates**: Some mix codes appeared in multiple datasets without proper distinguishing prefixes

### Actions Taken
1. **Full Database Backup**: Created CSV backup at `db_backup/mix_backup_20250506_203544.csv`
2. **Mix Code Standardization**: 
   - Converted all 1,500 non-standard mix codes to DS#-## format
   - Examples: "1" → "DS4-1", "27" → "DS5-27", "1350" → "DS5-1350"
3. **Verification**: Confirmed all mix codes now follow the standard pattern
4. **ID Preservation**: Maintained existing ID sequences to preserve relationships

### Results
- Successfully standardized 1,500 mix codes
- Non-standard codes remaining: 0
- Duplicate codes remaining: 0
- All database relationships preserved

---

## Material Reference System Implementation (May 7, 2025, 08:10)

### Issues Identified
- Material properties and aggregate details could not be properly linked to materials during import
- Warnings about missing material_id for properties and aggregate details occurred during import
- Performance results were not being captured due to incorrect column mappings

### Actions Taken
1. **Material Reference System**: Implemented in `import_ds.py` to track materials by reference keys
2. **Column Mapping Improvements**:
   - Created tools to ensure proper JSON formatting in mapping files
   - Developed new mapping files that leverage the reference key system
3. **Performance Results**:
   - Corrected column mappings for compressive strength tests (both cube and cylinder)
   - Successfully imported all performance results with proper age and specimen data
4. **Health Monitoring**:
   - Created health check script (`ds6_health_check.py`) to evaluate dataset integrity
   - Developed health flags generator (`generate_ds6_health_flags.py`) to assess data quality
5. **Documentation**: Created comprehensive documentation of the reference system

### Results
- Successfully imported 654 DS6 mixes with proper material references
- Imported 2,114 performance results with 95.1% of mixes having 28-day strength data
- Eliminated warnings about missing material IDs during import process
- Created a framework for future dataset imports using the reference key system

### Future Plans
- Create comprehensive mapping files for all columns in the DS6 dataset
- Apply the reference key system to all future dataset imports
- Develop templates and validation tools for mapping file creation

---

## DS6 Dataset Operations (May 6, 2025, 20:30)

### Issues Identified
- Initial import resulted in 0 unique materials and properties linked to DS6 mixes
- Material properties import created new 'DS6_PROPS-XX' mixes instead of linking to existing 'DS6-XX' mixes
- Mix codes were not properly renamed from 'DS6_PROPS-' to 'DS6-' during import

### Actions Taken
1. **Database Purge**: Created and executed `thorough_ds6_purge.py` to remove all DS6-related data
2. **Data Removed**:
   - 5,232 DS6 mixes
   - 27,048 mix components related to these mixes
   - 2 DS6 datasets (DS6 and DS6_PROPS)
   - Special modulus properties associated with DS6 materials
3. **Cleanup**: Removed temporary diagnostic and fix scripts

### Results
- Database returned to clean state without any DS6-related data
- Complete removal confirmed through verification queries
- Created DS6_CHANGELOG.md to document the process and lessons learned

---

## Material Table Cleanup (May 7, 2025, 15:52)

### Issues Identified
- Duplicate SCM entries with variant subtype codes (e.g., GGBS, ggbfs, BFS)
- Missing or inconsistent `subtype_code` and `specific_name` fields
- Mis-classified materials (e.g., CEM III/C under `SCM`)

### Actions Taken
1. Implemented `cleanup_materials.sql` to:
   - Merge duplicate SCM records into canonical entries
   - Update foreign keys dynamically across all referencing tables
   - Re-classify mis-classified CEM entries under `CEMENT`
   - Enforce composite-FK safety with fail-fast pre-flight check
   - Wrap operations in a single transaction with deferred constraints
2. Exported before/after audit snapshots (`materials_audit_before.csv`, `materials_audit_after.csv`)

### Results
- 2 duplicate SCM records merged
- Audit CSVs generated for verification
- Referential integrity preserved (no orphaned child rows)

---

## DS6 Mix Code Correction (May 7, 2025, 16:54)

### Issues Identified
- DS6 mix codes were incorrectly stored: the study number was in `mix_code` field (all "1")
- Actual mix numbers were embedded in the notes as "Dataset: DS6; Mix number: X"

### Actions Taken
1. Created `fix_ds6_mixcodes.sql` to:
   - Move the mix number from the notes to the `mix_code` field in proper "DS6-X" format
   - Move the study number from `mix_code` to the notes as "Study reference: X"

### Results
- Successfully updated 654 mixes in the DS6 dataset
- All DS6 mix codes now follow the standardized "DS6-X" format
- Original study reference information preserved in notes
- No duplicated mix codes detected

---

## DS6 Water-Binder Ratio Fix (May 7, 2025, 17:13)

### Issues Identified
- DS6 dataset's water-to-binder ratios were incorrectly stored in the `w_c_ratio` column
- The `w_b_ratio` column was empty for all DS6 mixes
- Original ds6.csv only had `wbr_total` (water-to-binder ratio) values, no water-to-cement ratios

### Actions Taken
1. Created and applied `fix_ds6_ratios.sql` to:
   - Move all values from `w_c_ratio` to the correct `w_b_ratio` column
   - Set `w_c_ratio` to NULL for all DS6 mixes
   - Create audit records to track changes

### Results
- Successfully moved water-binder ratios for all 654 DS6 mixes
- Before: 654 mixes with w_c_ratio values, 0 with w_b_ratio values
- After: 0 mixes with w_c_ratio values, 654 with w_b_ratio values
- Range of w/b ratios preserved (0.20 to 0.72)

---

## Comprehensive Material Cleanup (May 8, 2025, 09:42)

### Issues Identified
- Duplicate materials with different naming variations (e.g., GGBS, ggbfs, BFS all representing the same material)
- Inconsistent naming patterns (case sensitivity, spaces vs. underscores)
- Materials misclassified under incorrect categories (e.g., CEM III/C listed as SCM instead of CEMENT)
- Redundant entries for common materials like fly ash, silica fume, and superplasticizers

### Actions Taken
1. Created and applied `comprehensive_material_cleanup.sql` to:
   - Standardize material names and subtype_codes
   - Merge duplicate materials into canonical entries
   - Properly reclassify misclassified materials
   - Update all foreign key references across the database
   - Create audit records for all changes

### Results
- Successfully merged 16 duplicate materials into 10 canonical materials:
  - 3 superplasticizers → 1 canonical ADM
  - 2 calcined clay entries → 1 canonical SCM
  - 2 fly ash variants → 1 canonical general fly ash
  - 2 GGBS variants → 1 canonical entry
  - 2 silica fume entries → 1 canonical entry
  - Class-specific fly ash variants properly categorized
  - Palm oil fly ash standardized
  - Limestone powder standardized
  - Water entries standardized
- Updated 11,904 foreign key references to maintain referential integrity
- Generated comprehensive audit files to document all changes

---

## Material Naming Standardization (May 8, 2025, 12:45)

### Issues Identified
- Inconsistent naming conventions in `subtype_code` and `specific_name` fields
- Mixed case usage (upper/lower/mixed case) for the same material types
- Inconsistent formatting (spaces, underscores, abbreviations)
- Non-standard cement type formatting (cem_i vs. CEM I, cem_ii/bs vs. CEM II/B-S)
- Verbose aggregate codes (natural_coarse_aggregate instead of NCA)

### Actions Taken
1. Created and implemented `standardize_material_naming.sql` to:
   - Standardize all material `subtype_code` values to follow industry conventions
   - Make specific_name fields consistent and descriptive
   - Apply proper case conventions for each material type

2. Created a separate `fix_cement_formatting.sql` script to:
   - Properly format cement type designations (CEM I, CEM II/B-S, etc.)
   - Fix special cases with incorrect slashes and dashes

### Results
- 34 materials had their naming standardized:
  - **Cements**: All cement types now follow proper EN 197-1 format (CEM I, CEM II/B-S, etc.)
  - **Aggregates**: All aggregates now use standard codes (NCA, NFA, RCA)
  - **SCMs**: All SCMs use industry standard abbreviations (FA, GGBS, SF, LP, etc.)
  - **Admixtures**: All admixtures standardized (SP, AE, ACC, RET)
  - **Water**: All water entries standardized
- Maintained all material relationships and database integrity

---

## Current Database State

### Datasets
- DS1: 1,030 mixes
- DS2: 734 mixes
- DS3: 2,312 mixes
- DS4: 90 mixes with standardized codes
- DS5: 1,410 mixes with standardized codes

### Total Records
- 5,576 mixes with standardized naming
- 37,467 mix components
- All data integrity issues resolved

### Next Steps
- Proceed with proper DS6 dataset import (654 mixes)
- Create correct column mapping files for main dataset and properties
- Implement proper linking of materials and properties
- Verify data integrity after import with health checks

## 2025-05-06 22:58:35 - DS6 Mix Code Standardization

* Fixed 98 mix codes to use standardized 'DS6-XXX' format
* Ensured all DS6 mixes are consistently named for proper identification

### Sample of changes:

* Changed mix code: 1 -> DS6-1
* Changed mix code: 1 -> DS6-1-R
* Changed mix code: 35 -> DS6-35
* Changed mix code: 35 -> DS6-35-R
* Changed mix code: 36 -> DS6-36
* Changed mix code: 36 -> DS6-36-R
* Changed mix code: 2 -> DS6-2
* Changed mix code: 2 -> DS6-2-R
* Changed mix code: 3 -> DS6-3
* Changed mix code: 3 -> DS6-3-R
* ... and 88 more changes
