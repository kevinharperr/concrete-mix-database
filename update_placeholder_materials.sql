-- ==========================================================================
-- Update Placeholder Materials for DS5
-- Date: May 8, 2025
-- 
-- Purpose: Properly label placeholder materials from DS5 dataset structure
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
-- STEP 1: Update placeholder materials to reflect DS5 dataset structure
-- ==========================================================================

-- 1a. Update placeholder SCM for scm2 column (material_id 24)
UPDATE material
SET subtype_code = 'SCM2-Placeholder',
    specific_name = 'DS5 Secondary SCM Placeholder (scm2 column)'
WHERE material_id = 24;

-- 1b. Update placeholder ADM for admixture2 column (material_id 26)
UPDATE material
SET subtype_code = 'ADM2-Placeholder',
    specific_name = 'DS5 Secondary Admixture Placeholder (admixture2 column)'
WHERE material_id = 26;

-- ==========================================================================
-- STEP 2: Look for mixes that actually use these materials (non-zero dosage)
-- ==========================================================================

-- 2a. Find any mixes where the SCM2 placeholder has a non-zero dosage
SELECT cm.mix_id, cm.mix_code, mc.dosage_kg_m3 
FROM mix_component mc 
JOIN concrete_mix cm ON mc.mix_id = cm.mix_id
WHERE mc.material_id = 24 AND mc.dosage_kg_m3 > 0
ORDER BY cm.mix_code
LIMIT 10;

-- 2b. Find any mixes where the ADM2 placeholder has a non-zero dosage
SELECT cm.mix_id, cm.mix_code, mc.dosage_kg_m3 
FROM mix_component mc 
JOIN concrete_mix cm ON mc.mix_id = cm.mix_id
WHERE mc.material_id = 26 AND mc.dosage_kg_m3 > 0
ORDER BY cm.mix_code
LIMIT 10;

-- ==========================================================================
-- STEP 3: Find examples of mixes with both SCM1 and SCM2
-- ==========================================================================

-- 3a. Find some example mixes with non-zero dosages of two SCMs
SELECT 
    cm.mix_id, 
    cm.mix_code,
    m1.subtype_code AS scm1_type,
    mc1.dosage_kg_m3 AS scm1_dosage,
    m2.subtype_code AS scm2_type,
    mc2.dosage_kg_m3 AS scm2_dosage
FROM concrete_mix cm
JOIN mix_component mc1 ON cm.mix_id = mc1.mix_id
JOIN material m1 ON mc1.material_id = m1.material_id
JOIN mix_component mc2 ON cm.mix_id = mc2.mix_id
JOIN material m2 ON mc2.material_id = m2.material_id
WHERE 
    cm.dataset_id = 16 -- DS5
    AND m1.class_code = 'SCM' AND m1.material_id != 24 -- Real SCM1, not placeholder
    AND m2.class_code = 'SCM' AND m2.material_id != 24 -- Real SCM2, not placeholder
    AND mc1.dosage_kg_m3 > 0 -- Non-zero SCM1 dosage
    AND mc2.dosage_kg_m3 > 0 -- Non-zero SCM2 dosage
    AND m1.material_id != m2.material_id -- Different SCM types
LIMIT 10;

COMMIT;

\echo 'Placeholder materials updated to reflect DS5 dataset structure.'
