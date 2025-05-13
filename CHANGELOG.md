# Changelog

## [1.0.1] - 2025-05-13

### Fixed
- Fixed field name inconsistencies after transition to single-app structure (test_value → value_num, test_age_days → age_days)
- Fixed relationship name references (mixcomponent_set → components, mixcomponent__mix__dataset → mix_usages__mix__dataset)
- Fixed Dataset template to remove references to non-existent fields
- Fixed JavaScript chart rendering in mix_detail.html
- Removed obsolete base.html template file with references to retired concrete_mix_app
- Consolidated database configuration to use single 'cdb' database

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
