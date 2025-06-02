# Scripts Directory

This directory contains all utility scripts for the Concrete Mix Database project, organized by function and usage status.

## 📁 Directory Structure

### 🔧 `active/` - Currently Used Scripts
Scripts that are actively used in the current workflow and should be maintained.

### 🔄 `etl/` - Extract, Transform, Load Scripts  
Scripts for data import, transformation, and ETL processes.

### ✅ `validation/` - Data Validation Scripts
Scripts for checking data integrity, validation, and quality assurance.

### 🗄️ `database_management/` - Database Operations
Scripts for database setup, reset, backup, restoration, and maintenance.

### 📊 `analysis/` - Data Analysis Scripts
Scripts for research analysis, performance testing, and data exploration.

### 🧪 `experimental/` - Experimental Scripts
Scripts for testing, prototyping, and experimental features.

### 📦 `archived/` - Deprecated Scripts
Scripts that are no longer used but preserved for historical reference.

## 🎯 Usage Guidelines

1. **Active scripts** should be tested and maintained
2. **ETL scripts** handle data import/export operations
3. **Validation scripts** ensure data quality
4. **Database management** scripts require careful review before execution
5. **Analysis scripts** are for research and reporting
6. **Experimental scripts** are not guaranteed to work
7. **Archived scripts** should not be used in production

## 🚀 Running Scripts

Most scripts should be run from the project root directory:

```bash
# Example: Run an active script
python scripts/active/export_database.py

# Example: Run a validation script  
python scripts/validation/validation_run.py
```

## ⚠️ Important Notes

- Always review database management scripts before execution
- Test scripts in staging environment when possible
- Archived scripts are preserved for reference only
- Some scripts may require Django environment setup 