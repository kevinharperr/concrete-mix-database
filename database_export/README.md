# Concrete Mix Database Export

## Overview

This directory contains a database export of the Concrete Mix Database (CDB) application.

**Export Date:** 2025-05-20 10:27:03
**Database Name:** cdb

## Files Included

- `cdb_database_dump_20250520_102702.backup`: Binary format database dump (for direct restoration)
- `cdb_database_dump_20250520_102702.sql`: SQL format database dump (for inspection or manual import)

## Import Instructions

### Prerequisites

- PostgreSQL should be installed on your system
- The CDB application code should be set up

### Option 1: Binary Restoration (Recommended)

```bash
# Create the database if it doesn't exist
psql -c 'CREATE DATABASE cdb;' -U postgres

# Restore the database from the binary dump
pg_restore -d cdb -U postgres cdb_database_dump_20250520_102702.backup
```

### Option 2: SQL Import

```bash
# Create the database if it doesn't exist
psql -c 'CREATE DATABASE cdb;' -U postgres

# Import the SQL dump
psql -d cdb -U postgres -f cdb_database_dump_20250520_102702.sql
```

## Application Setup

After restoring the database, make sure your Django settings are configured to connect to this database:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cdb',
        'USER': 'postgres',
        'PASSWORD': 'your_password',  # Set your own password
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Important Notes

* This database export contains all concrete mix data, including material properties, mix components, and test results
* Some high water-binder ratios have been identified in certain mixes (particularly in DS2 dataset), as documented in the LESSONS_LEARNED.md file
* The database structure is designed to work with the CDB web application

## Contact

For questions or issues with this database export, please contact the database administrator.
