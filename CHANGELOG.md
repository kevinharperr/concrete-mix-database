# Changelog

## [1.0.5] - 2025-05-16

### Added
- Created robust ETL framework for database refresh:
  - `BaseImporter` class with comprehensive validation logic for concrete mixes
  - `StandardDatasetImporter` for standardized dataset formats
  - `DatasetValidator` tool for pre-import validation of datasets
- Implemented material component validation rules:
  - Water-binder ratio checks (0.25-0.70)
  - Minimum component requirements (cement, water, aggregate)
  - Cement content validation (100-600 kg/m³)
  - Water content validation (100-300 kg/m³)
- Added detailed logging and statistics collection for import processes
- Created tooling for staging environment preparation and testing

### Improved
- Enhanced data validation with customizable thresholds
- Added detailed validation reporting for data quality assessment
- Structured the ETL process for better maintainability and extensibility

## [1.0.4] - 2025-05-14

### Added
- Added Fresh Properties tab to the Performance Results section with dedicated chart and table
- Enhanced dark mode styling with improved text contrast and visibility
- Added diagnostic script (check_wb_ratios.py) to analyze water-binder ratio calculations and component breakdowns

### Improved
- Added additional CSS variables for better dark mode theme consistency
- Improved table header styling in dark mode for better readability
- Enhanced alert styling in dark mode with appropriate background and text colors
- Added specific styling for code blocks, pre elements, and buttons in dark mode
- Added special styling for Fresh Properties tab elements in dark mode
- Fixed spacing issues between tab headers and content in Performance Results section
- Improved water-binder ratio calculation with simplified formula (Water/(Cement+SCMs)) for better consistency
- Enhanced identification of cementitious materials using material class and subtype information

### Fixed
- Fixed JavaScript errors in the Fresh Properties chart implementation
- Improved chart label visibility in dark mode with dedicated color variables
- Fixed large gaps in Performance tabs by conditionally displaying charts only when data is available
- Fixed incorrect water-binder ratio calculations by ensuring proper recognition of all SCM types (CFA, FA-B, etc.)
- Resolved Decimal vs float comparison issues in the water-binder ratio update script

## [1.0.3] - 2025-05-14

### Added
- Implemented Strength Classification System to categorize mixes according to EN and ASTM standards
- Added automatic calculation of strength classes based on 28-day compression test results
- Added display of both reported and calculated strength classifications in mix detail page

### Fixed
- Fixed strength classification to recognize 'hardened' category as compressive strength tests
- Fixed multiple NameError issues in strength classification filtering by replacing Q objects with union() method
- Fixed sorting issues in mix list view

## [1.0.2] - 2025-05-13

### Added
- Added dedicated Visualizations tab in the mix detail page
- Implemented enhanced material composition charts (bar chart and pie chart)
- Added strength development visualization
- Added performance metrics radar chart
- Created sustainability metrics dashboard
- Added mix summary section with key metrics (total material, cement content, water content)

### Improved
- Improved layout for visualizations with proper sizing and responsive containers
- Enhanced user experience with tabbed interface separating mix details from visualizations
- Fixed chart sizing issues to prevent layout overflow

## [1.0.1] - 2025-05-13

### Fixed
- Fixed field name inconsistencies after transition to single-app structure (test_value → value_num, test_age_days → age_days)
- Fixed relationship name references (mixcomponent_set → components, mixcomponent__mix__dataset → mix_usages__mix__dataset)
- Fixed Dataset template to remove references to non-existent fields
- Fixed JavaScript chart rendering in mix_detail.html
- Removed obsolete base.html template file with references to retired concrete_mix_app
- Consolidated database configuration to use single 'cdb' database
- Fixed schema path issues with PostgreSQL tables in the 'cdb' database
- Removed explicit database references (.using('cdb')) from views and API for cleaner code
- Migrated Django system tables to 'cdb' database to ensure proper authentication and session management
- Cleaned up remaining content types from retired concrete_mix_app to prevent potential conflicts

## [1.0.0] - 2025-05-13

### Major Changes
- **Application Architecture**: Retired concrete_mix_app and transitioned to a single application architecture using cdb_app
- **Git**: Set up Git version control and GitHub repository

### Added
- Created missing template: `material_confirm_delete.html`
- Added `cdb_base.html` as the primary base template

### Changed
- Made cdb_app the primary application at the root URL (previously at /cdb prefix)
- Updated all templates to extend `cdb_base.html` instead of `base.html`
- Updated branding throughout to "Concrete Mix Database" instead of "CDB - Concrete Database"
- Updated navbar and footer to reflect the new branding

### Removed
- Completely removed concrete_mix_app (models, views, templates, etc.)
- Removed all references to concrete_mix_app from settings.py and URLs
- Removed "Original DB" link from the navbar

### Fixed
- Fixed template inheritance issues in delete confirmation templates
- Resolved broken navigation and URL patterns

### Technical Details
- Used separate Git branch (`retire-concrete-mix-app`) for the major restructuring
- Followed a systematic approach to identify and update all affected files
- Ensured proper testing of delete functionality
