-- Fix DS6 mix codes: move mix number from notes to mix_code field
-- and study_no from mix_code to notes

BEGIN;

-- Create temp table to extract mix numbers and store original values
CREATE TEMP TABLE ds6_mix_fixes AS
SELECT 
    mix_id,
    mix_code AS original_study_no,
    notes AS original_notes,
    REGEXP_REPLACE(notes, '.*Mix number: (\d+).*', 'DS6-\1') AS new_mix_code,
    CASE 
        WHEN mix_code = '' OR mix_code IS NULL THEN 'Unknown study reference' 
        ELSE 'Study reference: ' || mix_code 
    END AS new_notes
FROM concrete_mix
WHERE dataset_id = 19; -- DS6

-- Preview the changes
SELECT 
    mix_id, 
    original_study_no, 
    original_notes, 
    new_mix_code, 
    new_notes 
FROM ds6_mix_fixes
LIMIT 10;

-- Update concrete_mix with the new values
UPDATE concrete_mix
SET 
    mix_code = ds6_mix_fixes.new_mix_code,
    notes = ds6_mix_fixes.new_notes
FROM ds6_mix_fixes
WHERE concrete_mix.mix_id = ds6_mix_fixes.mix_id;

-- Ensure uniqueness of mix_code
SELECT 
    new_mix_code, 
    COUNT(*) 
FROM ds6_mix_fixes 
GROUP BY new_mix_code 
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC;

-- Verify results
SELECT 
    mix_id, 
    mix_code, 
    notes 
FROM concrete_mix
WHERE dataset_id = 19
ORDER BY mix_id
LIMIT 20;

COMMIT;
