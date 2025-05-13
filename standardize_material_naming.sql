-- ==========================================================================
-- Material Naming Standardization Script
-- Date: May 8, 2025
-- 
-- Purpose: Standardize material naming conventions to ensure consistency:
--   1. Standardize case and format for cement types (CEM I, CEM II/B-S, etc.)
--   2. Standardize aggregates to use NCA, NFA, RCA, RFA format
--   3. Standardize other material naming to follow consistent conventions
--   4. Create proper, consistent specific_name for each material
-- ==========================================================================

BEGIN;

-- ==========================================================================
-- STEP 0: Preflight setup
-- ==========================================================================

-- 0a. Set client_min_messages to reduce noise
SET client_min_messages TO WARNING;

-- 0b. Lock material table to prevent concurrent inserts 
LOCK TABLE material IN SHARE ROW EXCLUSIVE MODE;

-- 0c. Create audit table of current state
CREATE TEMP TABLE material_naming_audit AS
SELECT 
    material_id,
    class_code,
    subtype_code AS old_subtype_code,
    specific_name AS old_specific_name
FROM material;

-- ==========================================================================
-- STEP 1: Cement name standardization
-- ==========================================================================

-- 1a. Standardize CEM I
UPDATE material
SET subtype_code = 'CEM I',
    specific_name = 'CEM I'
WHERE class_code = 'CEMENT'
  AND LOWER(subtype_code) IN ('cem i', 'cem_i');

-- 1b. Standardize CEM II variants
UPDATE material
SET subtype_code = REPLACE(UPPER(subtype_code), '_', '/'),
    specific_name = REPLACE(UPPER(subtype_code), '_', '/')
WHERE class_code = 'CEMENT'
  AND LOWER(subtype_code) LIKE 'cem_ii%';

-- 1c. Fix CEM II with dashes format 
UPDATE material
SET subtype_code = REGEXP_REPLACE(subtype_code, 'CEM II/([A-Z])([A-Z])', 'CEM II/\1-\2'),
    specific_name = REGEXP_REPLACE(specific_name, 'CEM II/([A-Z])([A-Z])', 'CEM II/\1-\2')
WHERE class_code = 'CEMENT'
  AND subtype_code LIKE 'CEM II/%'
  AND subtype_code NOT LIKE '%-%';

-- 1d. Standardize CEM III variants
UPDATE material
SET subtype_code = REPLACE(UPPER(subtype_code), '_', '/'),
    specific_name = REPLACE(UPPER(subtype_code), '_', '/')
WHERE class_code = 'CEMENT'
  AND LOWER(subtype_code) LIKE 'cem_iii%';

-- 1e. Fix CEM III with dashes format
UPDATE material
SET subtype_code = REGEXP_REPLACE(subtype_code, 'CEM III/([A-Z])([A-Z])', 'CEM III/\1-\2'),
    specific_name = REGEXP_REPLACE(specific_name, 'CEM III/([A-Z])([A-Z])', 'CEM III/\1-\2')
WHERE class_code = 'CEMENT'
  AND subtype_code LIKE 'CEM III/%'
  AND subtype_code NOT LIKE '%-%';

-- 1f. Handle special cases with double underscores replaced with dashes
UPDATE material
SET subtype_code = REGEXP_REPLACE(UPPER(subtype_code), '__', '-'),
    specific_name = REGEXP_REPLACE(UPPER(specific_name), '__', '-')
WHERE class_code = 'CEMENT'
  AND subtype_code LIKE '%__%';

-- 1g. Portland cement standardization
UPDATE material
SET subtype_code = 'CEM I',
    specific_name = 'Portland Cement (CEM I)'
WHERE class_code = 'CEMENT'
  AND LOWER(subtype_code) = 'portland_cement';

-- ==========================================================================
-- STEP 2: Aggregate name standardization
-- ==========================================================================

-- 2a. Standardize Natural Coarse Aggregate to NCA
UPDATE material
SET subtype_code = 'NCA',
    specific_name = 'Natural Coarse Aggregate'
WHERE class_code = 'AGGR_C'
  AND (LOWER(subtype_code) = 'natural_coarse_aggregate'
       OR LOWER(subtype_code) = 'nca');

-- 2b. Standardize Natural Fine Aggregate to NFA
UPDATE material
SET subtype_code = 'NFA',
    specific_name = 'Natural Fine Aggregate'
WHERE class_code = 'AGGR_F'
  AND (LOWER(subtype_code) = 'natural_fine_aggregate'
       OR LOWER(subtype_code) = 'nfa');

-- 2c. Standardize Recycled Coarse Aggregate to RCA
UPDATE material
SET subtype_code = 'RCA',
    specific_name = 'Recycled Coarse Aggregate'
WHERE class_code = 'AGGR_C'
  AND (LOWER(subtype_code) = 'recycled_coarse_aggregate'
       OR LOWER(subtype_code) = 'rca');

-- 2d. Standardize empty aggregate subtypes
UPDATE material
SET subtype_code = 'NCA',
    specific_name = 'Natural Coarse Aggregate'
WHERE class_code = 'AGGR_C'
  AND (subtype_code IS NULL OR subtype_code = '');

UPDATE material
SET subtype_code = 'NFA',
    specific_name = 'Natural Fine Aggregate'
WHERE class_code = 'AGGR_F'
  AND (subtype_code IS NULL OR subtype_code = '');

-- ==========================================================================
-- STEP 3: SCM name standardization
-- ==========================================================================

-- 3a. Standardize Fly Ash
UPDATE material
SET subtype_code = 'FA',
    specific_name = 'Fly Ash (General)'
WHERE class_code = 'SCM'
  AND LOWER(subtype_code) IN ('fa', 'fly_ash');

-- 3b. Standardize Fly Ash variants
UPDATE material
SET subtype_code = 'FA-B',
    specific_name = 'Fly Ash - Bituminous (Class F)'
WHERE class_code = 'SCM'
  AND LOWER(subtype_code) LIKE '%bitum%';

UPDATE material
SET subtype_code = 'FA-L',
    specific_name = 'Fly Ash - Lignite (Class F)'
WHERE class_code = 'SCM'
  AND LOWER(subtype_code) LIKE '%lignite%';

-- 3c. Standardize GGBS
UPDATE material
SET subtype_code = 'GGBS',
    specific_name = 'Ground-granulated Blast-furnace Slag'
WHERE class_code = 'SCM'
  AND LOWER(subtype_code) IN ('ggbs', 'ggbfs');

-- 3d. Standardize Silica Fume
UPDATE material
SET subtype_code = 'SF',
    specific_name = 'Silica Fume'
WHERE class_code = 'SCM'
  AND LOWER(subtype_code) IN ('sf', 'silica_fume');

-- 3e. Standardize Limestone Powder
UPDATE material
SET subtype_code = 'LP',
    specific_name = 'Limestone Powder (Filler)'
WHERE class_code = 'SCM'
  AND LOWER(subtype_code) LIKE '%limestone%';

-- 3f. Standardize Natural Pozzolan
UPDATE material
SET subtype_code = 'NP',
    specific_name = 'Natural Pozzolan'
WHERE class_code = 'SCM'
  AND LOWER(subtype_code) LIKE '%natural_pozzolan%';

-- 3g. Standardize Natural Zeolite
UPDATE material
SET subtype_code = 'NZ',
    specific_name = 'Natural Zeolite'
WHERE class_code = 'SCM'
  AND LOWER(subtype_code) = 'natural_zeolite';

-- 3h. Standardize Calcined Clay / Metakaolin
UPDATE material
SET subtype_code = 'MK',
    specific_name = 'Calcined Clay (Metakaolin)'
WHERE class_code = 'SCM'
  AND (LOWER(subtype_code) = 'calcined_clay' 
       OR LOWER(subtype_code) = 'mk');

-- 3i. Standardize Rice Husk Ash
UPDATE material
SET subtype_code = 'RHA',
    specific_name = 'Rice Husk Ash'
WHERE class_code = 'SCM'
  AND LOWER(subtype_code) = 'rha';

-- 3j. Standardize Palm Oil Fly Ash
UPDATE material
SET subtype_code = 'POFA',
    specific_name = 'Palm Oil Fly Ash'
WHERE class_code = 'SCM'
  AND LOWER(subtype_code) = 'pofa';

-- 3k. Standardize Fluiddized Fly Ash
UPDATE material
SET subtype_code = 'FFA',
    specific_name = 'Fluidized Fly Ash'
WHERE class_code = 'SCM'
  AND LOWER(subtype_code) LIKE '%fluid%ash%';

-- ==========================================================================
-- STEP 4: Admixture name standardization
-- ==========================================================================

-- 4a. Standardize Superplasticizer
UPDATE material
SET subtype_code = 'SP',
    specific_name = 'Superplasticizer (HRWR)'
WHERE class_code = 'ADM'
  AND LOWER(subtype_code) IN ('sp', 'superplasticizer');

-- 4b. Standardize Air Entrainer
UPDATE material
SET subtype_code = 'AE',
    specific_name = 'Air Entrainer'
WHERE class_code = 'ADM'
  AND LOWER(subtype_code) LIKE '%air%';

-- 4c. Standardize Accelerator
UPDATE material
SET subtype_code = 'ACC',
    specific_name = 'Accelerator'
WHERE class_code = 'ADM'
  AND LOWER(subtype_code) LIKE '%accel%';

-- 4d. Standardize Retarder
UPDATE material
SET subtype_code = 'RET',
    specific_name = 'Retarder'
WHERE class_code = 'ADM'
  AND LOWER(subtype_code) LIKE '%retard%';

-- ==========================================================================
-- STEP 5: Water name standardization
-- ==========================================================================

-- 5a. Standardize Water
UPDATE material
SET subtype_code = 'WATER',
    specific_name = 'Water'
WHERE class_code = 'WATER';

-- ==========================================================================
-- STEP 6: Output results and verification
-- ==========================================================================

-- 6a. Join to show the changes
SELECT 
    ma.material_id,
    ma.class_code,
    ma.old_subtype_code,
    ma.old_specific_name,
    m.subtype_code AS new_subtype_code,
    m.specific_name AS new_specific_name,
    CASE WHEN ma.old_subtype_code = m.subtype_code THEN 'No Change' ELSE 'Changed' END AS status
FROM material_naming_audit ma
JOIN material m ON ma.material_id = m.material_id
ORDER BY ma.class_code, m.subtype_code, ma.material_id;

-- 6b. Show summary counts by class and subtype
SELECT 
    class_code,
    subtype_code,
    COUNT(*) AS material_count
FROM material
GROUP BY class_code, subtype_code
ORDER BY class_code, subtype_code;

COMMIT;

\copy (SELECT ma.material_id, ma.class_code, ma.old_subtype_code, ma.old_specific_name, m.subtype_code AS new_subtype_code, m.specific_name AS new_specific_name FROM material_naming_audit ma JOIN material m ON ma.material_id = m.material_id ORDER BY ma.class_code, m.subtype_code, ma.material_id) TO 'material_naming_changes.csv' CSV HEADER

\echo 'Material naming standardization complete.'
