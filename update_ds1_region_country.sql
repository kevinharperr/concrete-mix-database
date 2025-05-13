-- ==========================================================================
-- Update Region Country for DS1 Dataset
-- Date: May 8, 2025
-- 
-- Purpose: Set the region_country field to "Taiwan" for all mixes in DS1 dataset
-- ==========================================================================

BEGIN;

-- Set region_country to Taiwan for all DS1 mixes
UPDATE concrete_mix
SET region_country = 'Taiwan'
WHERE dataset_id = 6; -- DS1 dataset ID

-- Verify the update
SELECT 
    dataset_id,
    COUNT(*) as total_mixes,
    region_country
FROM concrete_mix 
WHERE dataset_id = 6 
GROUP BY dataset_id, region_country;

COMMIT;

\echo 'Region country updated to Taiwan for all DS1 mixes.'
