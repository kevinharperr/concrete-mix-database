-- Fix DS6 water-binder ratios: move values from w_c_ratio to w_b_ratio column
-- DS6 only has water-to-binder ratios, no water-to-cement ratios

BEGIN;

-- First check current state
SELECT 
    COUNT(*) as total_ds6_mixes,
    COUNT(CASE WHEN w_c_ratio IS NOT NULL THEN 1 END) as mixes_with_wc,
    COUNT(CASE WHEN w_b_ratio IS NOT NULL THEN 1 END) as mixes_with_wb,
    MIN(w_c_ratio) as min_wc,
    MAX(w_c_ratio) as max_wc
FROM concrete_mix
WHERE dataset_id = 19; -- DS6

-- Create audit table to track changes
CREATE TEMP TABLE ds6_ratio_changes AS
SELECT 
    mix_id, mix_code, w_c_ratio as original_wc, w_b_ratio as original_wb
FROM concrete_mix
WHERE dataset_id = 19;

-- Update concrete_mix to move values from w_c_ratio to w_b_ratio
UPDATE concrete_mix
SET 
    w_b_ratio = w_c_ratio,
    w_c_ratio = NULL
WHERE dataset_id = 19;

-- Output sample of changed rows to verify
SELECT 
    cm.mix_id, 
    cm.mix_code,
    drc.original_wc,
    drc.original_wb,
    cm.w_c_ratio as new_wc,
    cm.w_b_ratio as new_wb
FROM concrete_mix cm
JOIN ds6_ratio_changes drc ON cm.mix_id = drc.mix_id
ORDER BY cm.mix_id
LIMIT 10;

-- Check final state
SELECT 
    COUNT(*) as total_ds6_mixes,
    COUNT(CASE WHEN w_c_ratio IS NOT NULL THEN 1 END) as mixes_with_wc,
    COUNT(CASE WHEN w_b_ratio IS NOT NULL THEN 1 END) as mixes_with_wb,
    MIN(w_b_ratio) as min_wb,
    MAX(w_b_ratio) as max_wb
FROM concrete_mix
WHERE dataset_id = 19; -- DS6

COMMIT;
