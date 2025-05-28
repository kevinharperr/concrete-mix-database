# Concrete Mix Database Project Guide

## Directory Structure and Purpose

### Overview

This document explains the purpose of the main directories in the Concrete Mix Database project, focusing on the relationship between `cdb_app` (the main application) and `refresh_status` (the database refresh management system).

## cdb_app Directory

`cdb_app` is the **primary Django application** that powers the Concrete Mix Database. It contains:

- **Models**: Database schema definitions for concrete mixes, components, test results, etc.
- **Views**: Request handlers that process user requests and render templates
- **Templates**: HTML templates for rendering web pages
- **Static Files**: CSS, JavaScript, and images for the frontend
- **Forms**: Form definitions for data input and validation
- **Migrations**: Database migration scripts

This is where the core functionality of the application resides, including:

1. **Mix Management**: CRUD operations for concrete mixes
2. **Component Tracking**: Managing materials and their quantities in mixes
3. **Performance Results**: Recording and displaying test results
4. **Visualization**: Charts and graphs for data analysis
5. **Search & Filter**: Tools to find specific mixes based on criteria

## refresh_status Directory

`refresh_status` is a **separate Django application** that was created specifically to manage the database refresh process. It serves as an administrative layer on top of the main application with these purposes:

1. **Read-Only Mode**: Controls to temporarily disable write operations during database maintenance
2. **Status Tracking**: Monitoring and reporting on the progress of database refresh operations
3. **Notifications**: System for alerting users about database maintenance
4. **Admin Interfaces**: Tools for administrators to manage the refresh process

Key components include:

- **context_processors.py**: Provides template context variables for displaying status information
- **templatetags**: Custom template tags for rendering status information
- **views/**: Administrative views for managing the refresh process
- **notifications.py**: User notification system for maintenance events
- **urls.py**: URL routing for the refresh status management interfaces

## Relationship Between Directories

The relationship between these directories represents a **clear separation of concerns**:

- `cdb_app` handles the **core business logic** of the application
- `refresh_status` manages the **operational aspects** of database maintenance

This separation allows the core application to focus on its primary purpose while delegating maintenance operations to a specialized component.

## Database Refresh Process

The database refresh process (documented in `DATABASE_REFRESH_PLAN.md`) uses both components:

1. `refresh_status` handles:
   - Putting the application in read-only mode
   - Displaying maintenance notifications
   - Tracking progress of the refresh
   - Managing user communications

2. `cdb_app` is affected by:
   - Having write operations disabled during refresh
   - Being the target of data migrations and updates
   - Displaying the refreshed data once the process is complete

## Current Issues

1. **Template Syntax Errors**: The mix_detail.html template has syntax errors related to mismatched template tags
2. **Visualization Issues**: Charts aren't rendering properly due to these template issues
3. **JavaScript Integration**: Problems with how JavaScript is embedded in Django templates

## Branch Management

### Current Branch Status

The repository currently has three branches:

1. **master** - The stable production branch with the last known stable version
2. **database-refresh** - The active development branch where all recent work has been done, including the database refresh functionality and template fixes
3. **retire-concrete-mix-app** - A historical branch that was used for the major restructuring to transition from dual-app to single-app architecture

### Branch Differences

- The **database-refresh** branch contains all the latest features and fixes, including:
  - Database refresh implementation
  - Read-only mode functionality
  - User notification system
  - Database validation scripts
  - Recent documentation updates
  - Template fixes (attempted but not completed)

- The **master** branch is behind and does not contain these recent changes

### Recommendations for Branch Management

1. **Continue working on the `database-refresh` branch** in the new platform
2. **Do not merge branches yet** - Keep the branches separate until the template issues are fixed
3. **After fixing template errors** - Once you've fixed the template syntax errors on the new platform, then consider merging `database-refresh` into `master`
4. **Clean migration path** - Keeping the branches separate gives you a cleaner migration path and prevents introducing errors into the stable master branch

## Next Steps

1. Clone the repository from GitHub to the new platform
2. Switch to the `database-refresh` branch with `git checkout database-refresh`
3. Focus on fixing the template syntax issues in `templates/cdb_app/mix_detail.html`
4. Perform a comprehensive review of the template structure
5. Consider refactoring JavaScript to separate files for better maintainability
6. Implement proper template debugging with clear error messages
7. Fix the mismatched template tags in mix_detail.html
8. After fixing issues, consider merging `database-refresh` into `master`

## Recent Work

You were recently working on fixing the template syntax errors in the mix_detail.html file. These errors are causing the visualization tab to break, showing a 500 error when accessed. The specific error message indicates a mismatch between if/endif and block/endblock tags around line 896.

All your changes and the current status of the issue have been documented in:
- CHANGELOG.md (version 1.0.21)
- MASTER_CHANGELOG.md
- database_export/LESSONS_LEARNED.md

This issue will need to be addressed to restore full functionality to the visualization tab.
