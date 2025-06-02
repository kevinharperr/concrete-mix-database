# Archived Scripts

These scripts are **deprecated** and preserved for historical reference only. **Do not use in production.**

## 📋 Scripts in this folder:

### `manage_cdb.py`
**Purpose:** Custom database management utility  
**Status:** 🗂️ Archived - Likely obsolete after single-database consolidation  
**Reason:** Django's standard `manage.py` now handles all database operations  
**Archived:** June 2025 - Spring cleaning reorganization

### `run_server.py`
**Purpose:** Dual-app development server launcher  
**Status:** 🗂️ Archived - Obsolete after single-app architecture  
**Reason:** Supported old dual-app mode (concrete_mix_app + cdb_app)  
**Archived:** June 2025 - Spring cleaning reorganization

## ⚠️ Important Notes

- **DO NOT USE** these scripts in current development
- They are preserved for historical reference and learning
- May contain outdated assumptions about project structure
- Use modern equivalents instead:
  - Instead of `manage_cdb.py` → use `manage.py`
  - Instead of `run_server.py` → use `python manage.py runserver`

## 📚 Historical Context

These scripts were created during earlier phases of the project:
- `manage_cdb.py`: From multi-database era (before v1.0.1 consolidation)
- `run_server.py`: From dual-app architecture (before concrete_mix_app retirement)

## 🔄 Migration Path

If you need functionality from these scripts:
1. Review the archived script for logic
2. Implement equivalent functionality in current tools
3. Test thoroughly in staging environment
4. Document the new approach 