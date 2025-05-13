-- ==========================================================================
-- Comprehensive Material Cleanup Script
-- Date: May 8, 2025
-- 
-- Purpose: Clean up the material table by:
--   1. Standardizing names and subtype_codes
--   2. Merging duplicate materials
--   3. Reclassifying materials
--   4. Maintaining referential integrity across all tables
-- ==========================================================================

BEGIN;

-- ==========================================================================
-- STEP 0: Preflight checks
-- ==========================================================================

-- 0a. Set client_min_messages to reduce noise
SET client_min_messages TO WARNING;

-- 0b. Lock material table to prevent concurrent inserts 
LOCK TABLE material IN SHARE ROW EXCLUSIVE MODE;

-- 0c. Defer constraints for the transaction
SET CONSTRAINTS ALL DEFERRED;

-- 0d. Check for composite foreign keys on material_id
-- If any exist, script should be aborted and rewritten to handle them.
DO $$ 
DECLARE
    composite_fk_count INT;
BEGIN
    SELECT COUNT(*) INTO composite_fk_count
    FROM (
        SELECT ccu.table_name, COUNT(*) AS key_column_count
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu 
            ON tc.constraint_name = ccu.constraint_name
        JOIN information_schema.referential_constraints rc
            ON tc.constraint_name = rc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND (
            EXISTS (
                SELECT 1 FROM information_schema.constraint_column_usage
                WHERE constraint_name = tc.constraint_name
                AND column_name = 'material_id'
            )
        )
        GROUP BY ccu.table_name, tc.constraint_name
        HAVING COUNT(*) > 1
    ) composite_fks;

    IF composite_fk_count > 0 THEN
        RAISE EXCEPTION 'Composite foreign keys on material_id detected. Script must be revised.';
    END IF;
END $$;

-- ==========================================================================
-- STEP 1: Create standardization mapping and audit tables
-- ==========================================================================

-- 1a. Create an audit table to track the original state
CREATE TEMP TABLE _material_audit_before AS
SELECT 
    material_id,
    class_code,
    COALESCE(LOWER(subtype_code), '(null)') AS subtype_code_lower,
    COALESCE(specific_name, '(null)') AS specific_name
FROM material;

-- 1b. Create mapping table for standardization
CREATE TEMP TABLE material_std_mapping (
    material_id INT,
    old_class_code VARCHAR(50),
    old_subtype_code VARCHAR(50),
    old_specific_name VARCHAR(255),
    new_class_code VARCHAR(50),
    new_subtype_code VARCHAR(50),
    new_specific_name VARCHAR(255),
    canonical_id INT,           -- null if this is canonical, otherwise points to the ID to merge into
    PRIMARY KEY (material_id)
);

-- 1c. Initial population of mapping table
INSERT INTO material_std_mapping
SELECT 
    m.material_id,
    m.class_code AS old_class_code,
    m.subtype_code AS old_subtype_code,
    m.specific_name AS old_specific_name,
    m.class_code AS new_class_code,   -- will modify later as needed
    m.subtype_code AS new_subtype_code, -- will modify later
    m.specific_name AS new_specific_name, -- will modify later
    NULL AS canonical_id -- will map later
FROM material m;

-- ==========================================================================
-- STEP 2: Define canonical mappings for each material type
-- ==========================================================================

-- 2a. Update class code, subtype_code, and specific_name for SCMs
-- GGBS variants
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'ggbs',
    new_specific_name = 'Ground-granulated Blast-furnace Slag'
WHERE old_class_code = 'SCM' 
  AND (LOWER(old_subtype_code) IN ('ggbs', 'bfs', 'ggbfs') 
       OR LOWER(old_specific_name) LIKE '%ggbs%' 
       OR LOWER(old_specific_name) LIKE '%blast%furnace%');

-- Fly Ash variants
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'fly_ash',
    new_specific_name = 'Fly Ash (General)'
WHERE old_class_code = 'SCM' 
  AND (LOWER(old_subtype_code) IN ('fa', 'fly ash') 
       OR LOWER(old_specific_name) LIKE '%fly ash%')
  AND LOWER(old_subtype_code) NOT LIKE '%bitum%' 
  AND LOWER(old_subtype_code) NOT LIKE '%lignite%'
  AND LOWER(old_specific_name) NOT LIKE '%bitum%'
  AND LOWER(old_specific_name) NOT LIKE '%lignite%';

-- Fly Ash - Bituminous
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'fly_ash_bituminous',
    new_specific_name = 'Fly Ash - Bituminous Coal (Class F)'
WHERE old_class_code = 'SCM' 
  AND (LOWER(old_subtype_code) LIKE '%bitum%' 
       OR LOWER(old_specific_name) LIKE '%bitum%');

-- Fly Ash - Lignite/Brown Coal
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'fly_ash_lignite',
    new_specific_name = 'Fly Ash - Lignite/Brown Coal (Class F)'
WHERE old_class_code = 'SCM' 
  AND (LOWER(old_subtype_code) LIKE '%lignite%' 
       OR LOWER(old_subtype_code) LIKE '%brown%coal%'
       OR LOWER(old_specific_name) LIKE '%lignite%'
       OR LOWER(old_specific_name) LIKE '%brown%coal%');

-- Calcined Fly Ash
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'calcined_fly_ash',
    new_specific_name = 'Calcined Fly Ash'
WHERE old_class_code = 'SCM' 
  AND (LOWER(old_subtype_code) = 'cfa' 
       OR LOWER(old_specific_name) LIKE '%calcined%fly%');

-- Silica Fume variants
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'silica_fume',
    new_specific_name = 'Silica Fume'
WHERE old_class_code = 'SCM' 
  AND (LOWER(old_subtype_code) IN ('sf', 'silica_fume', 'silica fume') 
       OR LOWER(old_specific_name) LIKE '%silica%fume%');

-- Limestone Powder
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'limestone_powder',
    new_specific_name = 'Limestone Powder (Filler)'
WHERE old_class_code = 'SCM' 
  AND (LOWER(old_subtype_code) LIKE '%limestone%' 
       OR LOWER(old_specific_name) LIKE '%limestone%');

-- Natural Pozzolan
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'natural_pozzolan',
    new_specific_name = 'Natural Pozzolan'
WHERE old_class_code = 'SCM' 
  AND (LOWER(old_subtype_code) LIKE '%natural%pozzolan%' 
       OR LOWER(old_specific_name) LIKE '%natural%pozzolan%');

-- Calcined Clay / Metakaolin
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'calcined_clay',
    new_specific_name = 'Calcined Clay (Metakaolin)'
WHERE old_class_code = 'SCM' 
  AND (LOWER(old_subtype_code) IN ('cc', 'calcined_clay', 'mk') 
       OR LOWER(old_specific_name) LIKE '%calcined%clay%'
       OR LOWER(old_specific_name) LIKE '%metakaolin%');

-- Rice Husk Ash
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'rha',
    new_specific_name = 'Rice Husk Ash'
WHERE old_class_code = 'SCM' 
  AND (LOWER(old_subtype_code) = 'rha' 
       OR LOWER(old_specific_name) LIKE '%rice%husk%');

-- Palm Oil Fly Ash or Palm Oil Clinker
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'pofa',
    new_specific_name = 'Palm Oil Fly Ash'
WHERE old_class_code = 'SCM' 
  AND (LOWER(old_subtype_code) = 'pofa' 
       OR LOWER(old_subtype_code) = 'pocp'
       OR LOWER(old_specific_name) LIKE '%palm%oil%');

-- 2b. Update class code and types for misclassified items
-- ii/c was mis-classified as SCM
UPDATE material_std_mapping 
SET 
    new_class_code = 'CEMENT',
    new_subtype_code = 'cem_iii/c',
    new_specific_name = 'CEM III/C (Blastfurnace Cement)'
WHERE old_subtype_code = 'iii/c';

-- 2c. Update admixtures
-- Superplasticizers
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'superplasticizer',
    new_specific_name = 'Superplasticizer (HRWR)'
WHERE old_class_code = 'ADM' 
  AND (LOWER(old_subtype_code) IN ('sp', 'superplasticizer', 'pce') 
       OR LOWER(old_specific_name) LIKE '%superplast%'
       OR LOWER(old_specific_name) LIKE '%hrwr%');

-- 2d. Fix empty subtype codes
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'water',
    new_specific_name = 'Water'
WHERE old_class_code = 'WATER' AND (old_subtype_code IS NULL OR old_subtype_code = '');

UPDATE material_std_mapping 
SET 
    new_subtype_code = 'portland_cement',
    new_specific_name = 'Portland Cement'
WHERE old_class_code = 'CEMENT' AND (old_subtype_code IS NULL OR old_subtype_code = '');

UPDATE material_std_mapping 
SET 
    new_subtype_code = 'natural_coarse_aggregate',
    new_specific_name = 'Natural Coarse Aggregate'
WHERE old_class_code = 'AGGR_C' AND (old_subtype_code IS NULL OR old_subtype_code = '');

UPDATE material_std_mapping 
SET 
    new_subtype_code = 'natural_fine_aggregate',
    new_specific_name = 'Natural Fine Aggregate'
WHERE old_class_code = 'AGGR_F' AND (old_subtype_code IS NULL OR old_subtype_code = '');

-- 2e. Other standardizations
UPDATE material_std_mapping 
SET 
    new_subtype_code = 'nca',
    new_specific_name = 'Natural Coarse Aggregate'
WHERE old_class_code = 'AGGR_C' AND LOWER(old_subtype_code) = 'nca';

UPDATE material_std_mapping 
SET 
    new_subtype_code = 'nfa',
    new_specific_name = 'Natural Fine Aggregate'
WHERE old_class_code = 'AGGR_F' AND LOWER(old_subtype_code) = 'nfa';

-- ==========================================================================
-- STEP 3: Identify canonical entries for each group
-- ==========================================================================

-- 3a. Update the canonical_id based on our standardized mappings
DO $$ 
DECLARE
    material_type RECORD;
    canonical_material_id INT;
BEGIN
    -- For each unique combination of new class_code and new_subtype_code
    FOR material_type IN (
        SELECT DISTINCT new_class_code, new_subtype_code
        FROM material_std_mapping
        WHERE new_subtype_code IS NOT NULL
        ORDER BY new_class_code, new_subtype_code
    ) LOOP
        -- Find the first/lowest material_id for each type to use as canonical
        SELECT MIN(material_id) INTO canonical_material_id
        FROM material_std_mapping
        WHERE new_class_code = material_type.new_class_code
          AND new_subtype_code = material_type.new_subtype_code;
        
        -- Set the canonical_id for all other entries of this type
        UPDATE material_std_mapping
        SET canonical_id = canonical_material_id
        WHERE new_class_code = material_type.new_class_code
          AND new_subtype_code = material_type.new_subtype_code
          AND material_id != canonical_material_id;
    END LOOP;
END $$;

-- ==========================================================================
-- STEP 4: Create a tracking table for the merges
-- ==========================================================================

-- 4a. Create the material_merge_log table if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'material_merge_log') THEN
        CREATE TABLE material_merge_log (
            material_id_old INT,
            material_id_new INT,
            run_ts TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (material_id_old)
        );
    END IF;
END $$;

-- 4b. Create the merge log entries for this run
INSERT INTO material_merge_log (material_id_old, material_id_new)
SELECT material_id, canonical_id
FROM material_std_mapping
WHERE canonical_id IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM material_merge_log
    WHERE material_merge_log.material_id_old = material_std_mapping.material_id
);

-- ==========================================================================
-- STEP 5: Update the current materials table with standardized values
-- ==========================================================================

-- 5a. Update the material table for canonical entries
UPDATE material
SET 
    class_code = m.new_class_code,
    subtype_code = m.new_subtype_code,
    specific_name = m.new_specific_name
FROM material_std_mapping m
WHERE material.material_id = m.material_id
  AND m.canonical_id IS NULL -- Only update the ones we're keeping
  AND (material.class_code != m.new_class_code
       OR COALESCE(material.subtype_code, '') != COALESCE(m.new_subtype_code, '')
       OR COALESCE(material.specific_name, '') != COALESCE(m.new_specific_name, ''));

-- ==========================================================================
-- STEP 6: Redirect foreign keys on child tables to canonical entries
-- ==========================================================================

-- 6a. Update mix_component table
UPDATE mix_component
SET material_id = msm.canonical_id
FROM material_std_mapping msm
WHERE mix_component.material_id = msm.material_id
AND msm.canonical_id IS NOT NULL;

-- 6b. Update chemical_composition table if exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'chemical_composition') THEN
        EXECUTE 'UPDATE chemical_composition
                 SET material_id = msm.canonical_id
                 FROM material_std_mapping msm
                 WHERE chemical_composition.material_id = msm.material_id
                 AND msm.canonical_id IS NOT NULL;';
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'chemicalcomposition') THEN
        EXECUTE 'UPDATE chemicalcomposition
                 SET material_id = msm.canonical_id
                 FROM material_std_mapping msm
                 WHERE chemicalcomposition.material_id = msm.material_id
                 AND msm.canonical_id IS NOT NULL;';
    END IF;
END $$;

-- 6c. Update material_property table
UPDATE material_property
SET material_id = msm.canonical_id
FROM material_std_mapping msm
WHERE material_property.material_id = msm.material_id
AND msm.canonical_id IS NOT NULL;

-- 6d. Update aggregate_detail table if exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'aggregate_detail') THEN
        EXECUTE 'UPDATE aggregate_detail
                 SET material_id = msm.canonical_id
                 FROM material_std_mapping msm
                 WHERE aggregate_detail.material_id = msm.material_id
                 AND msm.canonical_id IS NOT NULL;';
    END IF;
END $$;

-- 6e. Update cement_detail table if exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'cement_detail') THEN
        EXECUTE 'UPDATE cement_detail
                 SET material_id = msm.canonical_id
                 FROM material_std_mapping msm
                 WHERE cement_detail.material_id = msm.material_id
                 AND msm.canonical_id IS NOT NULL;';
    END IF;
END $$;

-- 6f. Update scm_detail table if exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'scm_detail') THEN
        EXECUTE 'UPDATE scm_detail
                 SET material_id = msm.canonical_id
                 FROM material_std_mapping msm
                 WHERE scm_detail.material_id = msm.material_id
                 AND msm.canonical_id IS NOT NULL;';
    END IF;
END $$;

-- 6g. Update admixture_detail table if exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'admixture_detail') THEN
        EXECUTE 'UPDATE admixture_detail
                 SET material_id = msm.canonical_id
                 FROM material_std_mapping msm
                 WHERE admixture_detail.material_id = msm.material_id
                 AND msm.canonical_id IS NOT NULL;';
    END IF;
END $$;

-- 6h. Update aggregate_constituent table if exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'aggregate_constituent') THEN
        EXECUTE 'UPDATE aggregate_constituent
                 SET material_id = msm.canonical_id
                 FROM material_std_mapping msm
                 WHERE aggregate_constituent.material_id = msm.material_id
                 AND msm.canonical_id IS NOT NULL;';
    END IF;
END $$;

-- 6i. Update fibre_detail table if exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'fibre_detail') THEN
        EXECUTE 'UPDATE fibre_detail
                 SET material_id = msm.canonical_id
                 FROM material_std_mapping msm
                 WHERE fibre_detail.material_id = msm.material_id
                 AND msm.canonical_id IS NOT NULL;';
    END IF;
END $$;

-- ==========================================================================
-- STEP 7: Delete the duplicate materials that have been merged
-- ==========================================================================

DELETE FROM material
USING material_std_mapping
WHERE material.material_id = material_std_mapping.material_id
AND material_std_mapping.canonical_id IS NOT NULL;

-- ==========================================================================
-- STEP 8: Create audit output of the changes
-- ==========================================================================

-- 8a. Create an after state audit table
CREATE TEMP TABLE _material_audit_after AS
SELECT 
    material_id,
    class_code,
    COALESCE(LOWER(subtype_code), '(null)') AS subtype_code_lower,
    COALESCE(specific_name, '(null)') AS specific_name
FROM material;

-- 8b. Show merge summary
SELECT 
    COUNT(*) AS total_merges,
    COUNT(DISTINCT material_id_new) AS unique_canonical_materials
FROM material_merge_log
WHERE run_ts::date = CURRENT_DATE;

-- 8c. Show changes to class_code distribution
SELECT 
    'before' AS state,
    class_code,
    COUNT(*) AS count
FROM _material_audit_before
GROUP BY class_code
UNION ALL
SELECT 
    'after' AS state,
    class_code,
    COUNT(*) AS count
FROM _material_audit_after
GROUP BY class_code
ORDER BY class_code, state;

-- Export audits
COMMIT;

\copy (SELECT 'before' AS phase, * FROM _material_audit_before) TO 'comprehensive_materials_audit_before.csv' CSV HEADER
\copy (SELECT 'after' AS phase, m.material_id, m.class_code, COALESCE(LOWER(m.subtype_code), '(null)'), COALESCE(LOWER(m.specific_name), '(null)') FROM material m) TO 'comprehensive_materials_audit_after.csv' CSV HEADER
\copy (SELECT mml.material_id_old, mml.material_id_new, mml.run_ts, ms.old_subtype_code AS old_subtype, ms.old_specific_name AS old_name, m.subtype_code AS new_subtype, m.specific_name AS new_name FROM material_merge_log mml JOIN material_std_mapping ms ON ms.material_id = mml.material_id_old JOIN material m ON m.material_id = mml.material_id_new WHERE mml.run_ts::date = CURRENT_DATE ORDER BY mml.material_id_old) TO 'material_merge_details.csv' CSV HEADER

\echo 'Comprehensive material cleanup complete.'
