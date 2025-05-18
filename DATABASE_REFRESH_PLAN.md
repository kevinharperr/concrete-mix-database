# Concrete Mix Database Refresh Implementation Plan

## Overview

This document outlines the strategy and implementation plan for completely refreshing the Concrete Mix Database (CDB) to address systemic data import issues. The plan aims to create a clean, consistent database while minimizing disruption and mitigating potential risks.

**Target Completion Date:** TBD  
**Project Lead:** TBD

## Background and Justification

Data validation has revealed significant inconsistencies in the database, particularly with the DS2 dataset (dataset_id=9), including:

- Mix code misalignment (database mix codes don't match source data)
- Missing components (especially aggregates)
- Incorrect water-binder ratios
- Incomplete material properties

These issues affect data integrity and the reliability of analysis based on the current database. Starting fresh with improved import validation is the most efficient solution.

## Implementation Phases

### Phase 1: Preparation and Backup (COMPLETED)

#### Data Backup and Export

1. **Complete Database Dump**
   - Create a full SQL dump of the existing database
   - Store multiple copies in secure locations
   
2. **Table-Level CSV Exports**
   - Export all tables to CSV format for easy reference
   - Include lookup tables, mix components, and user-created content
   
3. **User Content Identification**
   - Identify and isolate any user-created or manually adjusted data
   - Create special exports of this data for potential re-import

4. **ID Reference Mapping**
   - Create a mapping of current mix IDs to original dataset identifiers
   - Document this mapping for reference during and after transition

#### Environment Setup

1. **Create a Staging Environment**
   - Set up a replica of the production environment
   - Validate that the staging environment functions correctly
   
2. **Version Control**
   - Ensure all changes to import scripts are tracked in version control
   - Create a new branch specifically for the database refresh

### Phase 2: System Development (IN PROGRESS)

#### Import Infrastructure

1. **ETL Script Redesign** ✅
   - Developed improved ETL scripts with robust validation
   - Implemented checks for required fields and data types
   - Added explicit handling of missing or null values

2. **Component Validation** ✅
   - Added validation for required mix components (cement, water, aggregates)
   - Implemented checks for realistic ratio values (w/c, w/b)
   - Created data quality scoring for imported mixes

3. **Testing Framework** ✅
   - Created automated validation tool for datasets
   - Developed validation scripts to compare import results with source data

#### Interface Adjustments

1. **Temporary Notice System** ✅
   - Implemented a notification banner for the CDB web app
   - Created a status page showing import progress
   - Added detailed activity logging system

2. **Read-Only Mode** ✅
   - Developed a mechanism to place the system in read-only mode during transition
   - Ensured all write operations are properly blocked while preserving read functionality
   - Added command-line interface for programmatic control
   - Implemented visual indicators for better user experience

### Phase 3: Test Migration (Estimated: 2-3 days)

1. **Staging Database Reset** ✅
   - Cleared the staging database
   - Validated that all tables were properly emptied
   - Created minimal test data for ETL validation

2. **Test Import Sequence** ✅
   - Import reference/lookup tables first
   - Test single dataset import and validate results
   - Document any issues encountered
   - Implemented comprehensive validation for data integrity

3. **Validation Run** ✅
   - Execute validation scripts against the test import
   - Verify component relationships and calculated values
   - Fix any issues with the import scripts
   - Generate validation reports with detailed metrics

4. **Performance Testing** ✅
    - Measure time required for each dataset import
    - Identify bottlenecks and optimize if necessary
    - Establish expected timelines for the production refresh

### Phase 4: Production Implementation (Estimated: 1-3 days)

#### Pre-Implementation

1. **User Notification** ✅
   - Send announcements about the planned maintenance using the implemented notification system
   - Provide clear timeline and expectations through the notification management interface
   - Use email notification functionality to reach all active users

2. **Final Backups**
   - Create final backups immediately before implementation
   - Verify backup integrity

3. **System Status Update**
   - Update status page to indicate maintenance in progress
   - Activate read-only mode if implemented

#### Implementation

1. **Database Reset**
   - Execute schema reset scripts (retaining structure but clearing data)
   - Verify that all tables are properly emptied

2. **Sequential Import**
   - Import all datasets in the predetermined order
   - Run validation after each dataset import
   - Document progress and any issues

3. **Post-Import Verification**
   - Run comprehensive validation across all datasets
   - Verify cross-dataset relationships
   - Check calculated fields (w/b ratios) for accuracy

### Phase 5: Post-Implementation (Estimated: 1-2 days)

1. **System Activation**
   - Restore full functionality to the CDB web app
   - Remove maintenance notices

2. **Documentation Update**
   - Update any documentation referencing database content
   - Document the new import process

3. **User Communication**
   - Inform users that the system is back online
   - Highlight improvements and any changes they should be aware of

4. **Monitor and Support**
   - Closely monitor system performance and user feedback
   - Be prepared to address any issues quickly

## Risk Mitigation Strategies

### Data Loss Prevention

- **Multiple Backups**: Maintain at least three copies of all data
- **Staggered Backup Timing**: Create backups at different stages of the process
- **Verification**: Test backup restoration before proceeding with data deletion

### Minimizing Disruption

- **Off-Hours Implementation**: Schedule the most disruptive work outside of business hours
- **Phased Approach**: Implement changes in logical segments with verification at each step
- **Rollback Plan**: Maintain the ability to revert to the original database if critical issues arise

### Maintaining Reference Integrity

- **ID Mapping Document**: Create and maintain a reference document mapping old IDs to new ones
- **Legacy ID Field**: Consider adding a field to store original IDs for cross-reference
- **URL Redirection**: For critical paths, implement redirects from old IDs to new ones

### Quality Assurance

- **Automated Validation**: Create scripts to validate imported data against source files
- **Manual Spot Checks**: Identify key mixes for manual verification
- **Performance Testing**: Ensure the refreshed database maintains or improves system performance

## Rollback Plan

In case of significant issues that cannot be resolved during the implementation timeframe:

1. **Decision Point Identification**
   - Pre-define criteria for rollback decisions
   - Assign authority for making the rollback decision

2. **Rollback Procedure**
   - Restore database from the most recent pre-implementation backup
   - Revert any code changes related to the refresh
   - Restore original application state

3. **Communication**
   - Inform all stakeholders of the rollback
   - Provide estimated timeline for resolving issues and reattempting

## Communication Plan

### Pre-Implementation

- Announce the planned refresh with at least one week's notice
- Provide a detailed timeline and expected impacts
- Give users guidance on any preparations they should make

### During Implementation

- Maintain a status page with regular updates
- Provide clear indicators of progress
- Communicate any delays or issues promptly

### Post-Implementation

- Announce completion and system availability
- Provide documentation on any changes to workflows
- Establish a feedback mechanism for reporting issues

## Resources and Responsibilities

### Required Roles

- **Project Manager**: Overall coordination and communication
- **Database Administrator**: Backup, reset, and data migration
- **Developer(s)**: Import script creation and testing
- **QA Tester**: Validation and verification
- **User Representative**: Feedback and user-perspective testing

### Tools and Resources

- Database management tools
- Version control system
- Automated testing framework
- Communication platforms for updates
- Documentation resources

## Success Criteria

The database refresh will be considered successful when:

1. All datasets are successfully imported with complete component data
2. Validation confirms data integrity and accuracy
3. The CDB web app functions correctly with the new database
4. Water-binder ratios are calculated correctly for all mixes
5. Users can access and work with the system without significant issues

## Post-Implementation Review

After completion, conduct a review to:

1. Evaluate the effectiveness of the implementation process
2. Document lessons learned
3. Identify any remaining issues requiring attention
4. Develop plans for long-term data quality maintenance

## Appendix

### Dataset Import Order

1. Reference data (material classes, units, etc.)
2. Materials
3. Dataset 1
4. Dataset 2
5. [Continue for all datasets]

### Validation Checklists

#### Pre-Import Validation
- Schema correctness
- Reference data completeness
- Import script correctness

#### Per-Dataset Validation
- Record count matching
- Required fields presence
- Foreign key integrity
- Component completeness

#### Post-Import Validation
- Calculated field accuracy
- Cross-dataset relationships
- Application functionality
- Performance benchmarks
