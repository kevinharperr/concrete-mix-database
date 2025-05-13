-- ==========================================================================
-- Final Material Cleanup Script
-- Date: May 8, 2025
-- 
-- Purpose: Finalize material table cleanup by:
--   1. Setting proper subtype_codes for NULL entries used in mixes
--   2. Consolidating water entries
--   3. Standardizing or removing unused inconsistent SCM entries
-- ==========================================================================

BEGIN;

-- ==========================================================================
-- STEP 0: Preflight setup
-- ==========================================================================

-- 0a. Set client_min_messages to reduce noise
SET client_min_messages TO WARNING;

-- 0b. Lock material table to prevent concurrent inserts 
LOCK TABLE material IN SHARE ROW EXCLUSIVE MODE;

-- ==========================================================================
-- STEP 1: Fix NULL subtype_codes for heavily used materials
-- ==========================================================================

-- 1a. Fix SCM with NULL subtype_code (material_id 24, used in DS5)
UPDATE material
SET subtype_code = 'SCM-Generic',
    specific_name = 'Generic SCM (DS5)'
WHERE material_id = 24;

-- 1b. Fix ADM with NULL subtype_code (material_id 26, used in DS5)
UPDATE material
SET subtype_code = 'ADM-Generic',
    specific_name = 'Generic Admixture (DS5)'
WHERE material_id = 26;

-- ==========================================================================
-- STEP 2: Handle unused or inconsistent materials
-- ==========================================================================

-- 2a. Set proper code for SCM with 'specific_name' (material_id 54, not used in mixes)
UPDATE material
SET subtype_code = 'OPC',
    specific_name = 'Ordinary Portland Cement'
WHERE material_id = 54;

-- 2b. Fix SCM with 'ba' (material_id 72, not used in mixes)
UPDATE material
SET subtype_code = 'BA',
    specific_name = 'Bottom Ash'
WHERE material_id = 72;

-- 2c. Fix SCM with 'calcined_fly_ash' (material_id 47, used in DS5)
UPDATE material
SET subtype_code = 'CFA',
    specific_name = 'Calcined Fly Ash'
WHERE material_id = 47;

-- ==========================================================================
-- STEP 3: Consolidate WATER entries (keeping most used entry)
-- ==========================================================================

-- 3a. Check if water entry with material_id 68 can be safely removed
SELECT COUNT(*) AS count_68_usage FROM mix_component WHERE material_id = 68;

-- 3b. Delete unused water entry if no references exist
DELETE FROM material WHERE material_id = 68 AND NOT EXISTS (
  SELECT 1 FROM mix_component WHERE material_id = 68
);

-- 3c. Analyze which water entry is most used
SELECT 
    material_id, 
    COUNT(*) as usage_count,
    RANK() OVER(ORDER BY COUNT(*) DESC) as usage_rank
FROM mix_component 
WHERE material_id IN (6, 13)
GROUP BY material_id;

-- We won't automatically consolidate the water entries that are in use
-- as this would require updating thousands of mix components
-- and the risk of data inconsistency is high.

-- ==========================================================================
-- STEP 4: Verification
-- ==========================================================================

-- 4a. Verify all materials now have proper subtype_codes
SELECT material_id, class_code, subtype_code, specific_name
FROM material
WHERE subtype_code IS NULL OR subtype_code = ''
ORDER BY material_id;

-- 4b. View final material list organized by class
SELECT 
    class_code,
    COUNT(*) AS material_count,
    array_agg(DISTINCT subtype_code ORDER BY subtype_code) AS subtypes
FROM material
GROUP BY class_code
ORDER BY class_code;

COMMIT;

\echo 'Final material cleanup complete.'
