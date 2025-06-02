# Active Scripts

These scripts are **currently used** in the project workflow and should be maintained and tested.

## 📋 Scripts in this folder:

### `export_database.py`
**Purpose:** Database backup and export utility  
**Usage:** Creates database backups for safety and migration  
**Status:** ✅ Active - Used for database backup operations

### `import_ds1.py` 
**Purpose:** Proven DS1 dataset importer  
**Usage:** Imports Dataset 1 with validated methodology  
**Status:** ✅ Active - Reference implementation for dataset imports

### `run_database_refresh.py`
**Purpose:** Main database refresh orchestrator  
**Usage:** Coordinates the complete database refresh process  
**Status:** ✅ Active - Core workflow script

### `run_specific_import.py`
**Purpose:** Current DS2 ETL runner  
**Usage:** Handles DS2 dataset import with proven configuration  
**Status:** ✅ Active - Primary ETL tool for DS2

## 🎯 Maintenance Notes

- These scripts should be tested before major changes
- Document any modifications in the changelog
- Ensure compatibility with current Django environment
- Test in staging before production use

## 🚀 Usage Examples

```bash
# Export database backup
python scripts/active/export_database.py

# Import DS1 dataset
python scripts/active/import_ds1.py

# Run database refresh process
python scripts/active/run_database_refresh.py

# Import DS2 dataset
python scripts/active/run_specific_import.py
``` 