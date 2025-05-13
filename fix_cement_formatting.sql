-- Fix cement type formatting issues from the standardization script

BEGIN;

-- 1. Fix the CEM/II format to CEM II format (remove first slash)
UPDATE material
SET subtype_code = REGEXP_REPLACE(subtype_code, 'CEM/(II|III)', 'CEM \1'),
    specific_name = REGEXP_REPLACE(specific_name, 'CEM/(II|III)', 'CEM \1')
WHERE class_code = 'CEMENT'
  AND subtype_code LIKE 'CEM/%';

-- 2. Fix special cases with double slashes
UPDATE material
SET subtype_code = REGEXP_REPLACE(subtype_code, '//([A-Z]+)/', '-\1 '),
    specific_name = REGEXP_REPLACE(specific_name, '//([A-Z]+)/', '-\1 ')
WHERE class_code = 'CEMENT'
  AND subtype_code LIKE '%//%';

-- 3. Remove trailing slashes
UPDATE material
SET subtype_code = RTRIM(subtype_code, '/'),
    specific_name = RTRIM(specific_name, '/')
WHERE class_code = 'CEMENT'
  AND subtype_code LIKE '%/';

-- 4. Show results
SELECT 
    material_id,
    class_code,
    subtype_code,
    specific_name
FROM material
WHERE class_code = 'CEMENT'
ORDER BY subtype_code;

COMMIT;

\echo 'Cement formatting fixed.'
