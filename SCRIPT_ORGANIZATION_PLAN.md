# Script Organization Implementation Plan

## Current Inventory
We have **24 Python scripts** in the root directory that need to be organized according to the agent's recommendations.

## Scripts Categorization and Actions

### 🔧 **ACTIVE SCRIPTS** (Currently Used - Move to `scripts/active/`)

| Script | Purpose | Agent Match | Action |
|--------|---------|-------------|--------|
| `run_specific_import.py` | Current DS2 ETL runner (ACTIVE) | ✅ Identified as critical | Move to `active/` |
| `import_ds1.py` | Proven working DS1 importer | ✅ Identified as valuable | Move to `active/` |
| `export_database.py` | Database backup/export tool | ✅ Identified as valuable | Move to `active/` |
| `manage.py` | Django management (ESSENTIAL) | ✅ Keep at root | **NO CHANGE** |

### 🔄 **ETL SCRIPTS** (Move to `scripts/etl/`)

| Script | Purpose | Agent Match | Action |
|--------|---------|-------------|--------|
| `sequential_import.py` | Sequential dataset import logic | Similar to agent's import scripts | Move to `etl/` |
| `debug_import.py` | Import debugging tool | ETL-related debugging | Move to `etl/` |

### ✅ **VALIDATION SCRIPTS** (Move to `scripts/validation/`)

| Script | Purpose | Agent Match | Action |
|--------|---------|-------------|--------|
| `validation_run.py` | Database validation framework | ✅ Identified as validation | Move to `validation/` |
| `validate_dataset_import.py` | Import validation | ✅ ETL validation | Move to `validation/` |
| `verify_db_schema.py` | Schema verification | ✅ Validation tool | Move to `validation/` |
| `direct_db_check.py` | Database integrity check | Similar to agent's check scripts | Move to `validation/` |

### 🗄️ **DATABASE MANAGEMENT** (Move to `scripts/database_management/`)

| Script | Purpose | Agent Match | Action |
|--------|---------|-------------|--------|
| `reset_database.py` | Database reset utility | ✅ DB management | Move to `database_management/` |
| `reset_sequences.py` | PostgreSQL sequence reset | ✅ DB management | Move to `database_management/` |
| `setup_database.py` | Database setup utility | ✅ DB management | Move to `database_management/` |
| `restore_database.py` | Database restoration | ✅ DB management | Move to `database_management/` |
| `preserve_user_data.py` | User data preservation | ✅ DB management | Move to `database_management/` |

### 📊 **ANALYSIS SCRIPTS** (Move to `scripts/analysis/`)

| Script | Purpose | Agent Match | Action |
|--------|---------|-------------|--------|
| `performance_testing.py` | Research performance analysis | ✅ Identified as analysis | Move to `analysis/` |

### 🧪 **EXPERIMENTAL SCRIPTS** (Move to `scripts/experimental/`)

| Script | Purpose | Agent Match | Action |
|--------|---------|-------------|--------|
| `prepare_test_migration.py` | Test migration preparation | Test/experimental | Move to `experimental/` |
| `setup_test_migration.py` | Test migration setup | Test/experimental | Move to `experimental/` |
| `temp_fix_line.py` | Temporary fix script | ✅ Temporary fix | Move to `experimental/` |

### 🗂️ **STAGING/DEVELOPMENT** (Move to `scripts/experimental/` or `scripts/database_management/`)

| Script | Purpose | Agent Match | Action |
|--------|---------|-------------|--------|
| `reset_staging_db.py` | Staging database reset | ✅ Staging/testing | Move to `database_management/` |
| `setup_staging.py` | Staging environment setup | ✅ Staging/testing | Move to `database_management/` |

### 📦 **ARCHIVED SCRIPTS** (Move to `scripts/archived/`)

| Script | Purpose | Agent Match | Action |
|--------|---------|-------------|--------|
| `run_server.py` | Dual-app dev server (obsolete) | ✅ Identified for archive | Move to `archived/` |
| `manage_cdb.py` | Custom DB management (likely obsolete) | ✅ Identified for archive/review | Move to `archived/` |

### 🔄 **DATABASE REFRESH WORKFLOW** (Move to `scripts/active/` - These are part of our refresh process)

| Script | Purpose | Agent Match | Action |
|--------|---------|-------------|--------|
| `run_database_refresh.py` | Main refresh orchestrator | Active workflow | Move to `active/` |

## Implementation Steps

1. ✅ **Create folder structure** (COMPLETED)
2. **Categorize scripts** by function (COMPLETED ABOVE)
3. **Move scripts** to appropriate folders
4. **Add README files** to each scripts folder
5. **Update documentation** to reflect new structure
6. **Test critical scripts** after moving
7. **Commit changes** with detailed documentation

## Notes on Agent's Analysis Accuracy

### ✅ **Agent Got Right:**
- `run_server.py` → Archive (obsolete dual-app)
- `manage_cdb.py` → Likely obsolete
- Need for organized folder structure
- Archive rather than delete principle

### 📝 **Reality Check:**
- **More active scripts** than agent anticipated
- **Several database management** scripts not mentioned by agent
- **Staging/testing infrastructure** more developed than agent saw
- **Database refresh workflow** is more comprehensive

### 🎯 **Our Approach:**
- Follow agent's folder structure ✅
- Be more conservative with "active" classification
- Preserve all staging/testing infrastructure
- Maintain database refresh workflow integrity

## Risk Assessment
- **LOW RISK**: All moves preserve files and functionality
- **CONSERVATIVE**: When in doubt, mark as active rather than archived
- **REVERSIBLE**: All actions can be undone if needed
- **TESTED**: Will verify critical scripts after moving 