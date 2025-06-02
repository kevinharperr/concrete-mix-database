# LLM Agent Codebase Analysis Prompt

## Repository Information
- **Repository:** https://github.com/kevinharperr/concrete-mix-database/tree/database-refresh
- **Branch:** `database-refresh` (NOT main branch)
- **Project Type:** Django web application for concrete mix database management
- **Current Status:** Production-ready with 1,764 concrete mixes (DS1 + DS2 datasets)

## Objective
Perform comprehensive spring cleaning analysis to identify:
1. **Unused files and scripts** that can be safely removed
2. **Duplicate or redundant code**
3. **Optimization opportunities**
4. **Documentation inconsistencies**
5. **Dependency cleanup**
6. **Code structure improvements**

## ⚠️ CRITICAL - FILES TO NEVER TOUCH OR REMOVE

### Essential Django Structure (REQUIRED FOR FUNCTIONALITY)
- `manage.py` - Django management script
- `concrete_mix_project/` directory and ALL contents:
  - `settings.py` - Main Django configuration
  - `settings_staging.py` - Staging configuration  
  - `urls.py` - URL routing
  - `wsgi.py` - Production WSGI interface
  - `asgi.py` - Production ASGI interface
  - `__init__.py` - Python package marker
  - `db_router.py` - Database routing logic

### Core Application Code (ESSENTIAL)
- `cdb_app/` directory and ALL contents - Main Django application
- `refresh_status/` directory and ALL contents - Notification system
- `templates/` directory and ALL contents - Django templates
- `static/` directory - Static files (newly created)

### Configuration Files (KEEP)
- `.gitignore` - Git ignore rules
- `requirements.txt` or similar dependency files
- `SECURITY_README.md` - Security documentation (just added)
- Environment example files (`env.example`)

## 📁 Key Directories and Files to Analyze

### Main Application Structure
```
concrete-mix-database/
├── cdb_app/                    # Core Django app (ESSENTIAL)
├── concrete_mix_project/       # Django project package (ESSENTIAL)
├── refresh_status/             # Notification system (ESSENTIAL)
├── templates/                  # Django templates (ESSENTIAL)
├── static/                     # Static files (ESSENTIAL)
├── database_export/            # Documentation and export files
├── etl/                        # ETL configurations (may have unused files)
└── [Various .py scripts]      # Root-level Python scripts
```

### Documentation Files to Review
- `README.md` - Main documentation
- `CHANGELOG.md` - Version history
- `MASTER_CHANGELOG.md` - Comprehensive changelog
- `DATABASE_REFRESH_PLAN.md` - Project roadmap
- `database_export/LESSONS_LEARNED.md` - Technical lessons
- Various other `.md` files

### Root-Level Python Scripts (FOCUS AREA FOR CLEANUP)
These are the files most likely to contain unused/redundant code:
- Data import scripts (various `import_*.py` files)
- Validation scripts (various `validate_*.py`, `verify_*.py` files)
- Database management scripts (`reset_*.py`, `setup_*.py` files)
- Testing scripts (`test_*.py`, `check_*.py` files)
- Utility scripts (`cleanup_*.py`, `fix_*.py` files)

## 🎯 Specific Analysis Focus Areas

### 1. Unused Import/ETL Scripts
Look for:
- Multiple versions of similar import scripts
- Failed experiment scripts (like universal import system files)
- Temporary debugging scripts
- Scripts with "test", "temp", "backup" in names
- Scripts that import modules not used elsewhere

### 2. Duplicate Functionality
Identify:
- Multiple scripts doing similar database operations
- Redundant validation logic
- Duplicate utility functions
- Similar configuration files

### 3. Outdated Dependencies
Check for:
- Unused imports in Python files
- Dependencies listed but not used
- Commented-out code blocks
- Legacy configuration options

### 4. Documentation Consistency
Review:
- Outdated references in documentation
- Inconsistent naming conventions
- Missing documentation for current scripts
- Redundant documentation files

## 📊 Project Context for Better Analysis

### Current Technology Stack
- **Backend:** Django 5.x with PostgreSQL
- **Frontend:** Django Templates + Bootstrap 5
- **Database:** PostgreSQL with 1,764 concrete mixes
- **Key Features:** Data filtering, visualization, ETL pipelines

### Recent Major Changes (Important Context)
1. **Application consolidation** - Retired `concrete_mix_app`, now using single `cdb_app`
2. **Security hardening** - Removed hardcoded credentials (just completed)
3. **DS1 & DS2 data imports** - Successfully imported with sequential IDs
4. **Universal import system removal** - Failed system was completely removed

### Known Areas with Potential Cleanup
1. **ETL directory** - May contain old configuration files from removed universal system
2. **Root-level scripts** - Many temporary/experimental scripts from development
3. **Database management scripts** - Multiple versions from different phases
4. **Validation/testing scripts** - Accumulated during development iterations

## 🔍 Analysis Methodology

### Step 1: File Categorization
Categorize each file as:
- **ESSENTIAL** (core functionality)
- **ACTIVE** (currently used)
- **LEGACY** (outdated but possibly referenced)
- **UNUSED** (safe to remove)
- **DUPLICATE** (redundant with other files)

### Step 2: Dependency Analysis
- Check which files are imported/referenced by others
- Identify orphaned files with no references
- Look for circular dependencies

### Step 3: Code Quality Review
- Identify large blocks of commented code
- Find TODO/FIXME comments that indicate incomplete work
- Spot debugging print statements that can be removed

### Step 4: Documentation Audit
- Verify documentation matches current code structure
- Identify outdated installation/setup instructions
- Check for references to removed features

## 📋 Expected Deliverables

Please provide:

### 1. Removal Recommendations
- List of files that can be safely deleted
- Justification for each recommendation
- Risk level (low/medium/high) for each removal

### 2. Consolidation Opportunities
- Files that can be merged or consolidated
- Duplicate functionality that can be eliminated
- Configuration that can be simplified

### 3. Code Quality Improvements
- Dead code removal suggestions
- Unused import cleanup
- Commenting and documentation improvements

### 4. Dependency Optimization
- Unused dependencies that can be removed
- Missing dependencies that should be added
- Version updates that might be beneficial

### 5. Structure Improvements
- Better organization suggestions
- Naming convention improvements
- Directory structure optimizations

## 🚨 Safety Guidelines

1. **NEVER suggest removing anything in the "CRITICAL - FILES TO NEVER TOUCH" section**
2. **Verify file usage** before suggesting removal (check for imports, references)
3. **Consider git history** - files might be temporarily unused but part of active development
4. **Prioritize low-risk removals** - start with obviously unused files
5. **Suggest testing** before any major cleanup operations

## 📈 Success Metrics

A successful cleanup should:
- Reduce repository size and complexity
- Improve code maintainability
- Eliminate confusion from outdated files
- Maintain 100% functionality
- Preserve all essential documentation
- Make the project easier to navigate for new developers

---

**Note:** This is an active development project with recent major improvements. Please be conservative with removal suggestions and prioritize obvious cleanup opportunities over aggressive refactoring.

## 📂 Quick File Inventory (Reference)

### Root-Level Python Scripts (Primary Analysis Target)
The repository contains numerous Python scripts that accumulated during development. Focus your analysis on these:

**Known Active Scripts:**
- `manage.py` - Django management (ESSENTIAL)
- `run_specific_import.py` - Current ETL runner (ACTIVE)
- `importer_engine.py` - ETL engine (ACTIVE)

**Likely Cleanup Candidates:**
Scripts with patterns like:
- `import_ds*.py` - Dataset import scripts (check for duplicates)
- `validate_*.py` - Validation scripts (check for redundancy)
- `verify_*.py` - Verification scripts (check for redundancy)
- `check_*.py` - Check/diagnostic scripts (likely temporary)
- `test_*.py` - Test scripts (check if still needed)
- `fix_*.py` - Fix/repair scripts (likely one-time use)
- `cleanup_*.py` - Cleanup scripts (likely temporary)
- `reset_*.py` - Reset scripts (check for duplicates)
- `setup_*.py` - Setup scripts (check for duplicates)

### Directories Overview
```
concrete-mix-database/
├── cdb_app/                    # ESSENTIAL - Main Django app
├── concrete_mix_project/       # ESSENTIAL - Django configuration
├── refresh_status/             # ESSENTIAL - Notification system
├── templates/                  # ESSENTIAL - Django templates
├── static/                     # ESSENTIAL - Static files
├── database_export/            # Documentation (review contents)
├── etl/                        # ETL configs (may have cleanup opportunities)
├── migrations/                 # Django migrations (if exists)
└── [50+ Python scripts]       # PRIMARY CLEANUP TARGET
```

**Analysis Priority:** Focus heavily on the root-level Python scripts as this is where most cleanup opportunities exist.

## 🎯 Specific Questions to Answer

1. **Which scripts have similar/duplicate functionality?**
2. **Which scripts were clearly experimental or temporary?**
3. **Which scripts have no imports/references from other files?**
4. **Are there multiple versions of the same logical operation?**
5. **Which scripts contain only commented-out code or minimal functionality?**

This analysis will help significantly reduce project complexity while maintaining all essential functionality. 