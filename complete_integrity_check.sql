-- Check for orphaned rows in all tables that could be affected by material ID changes

-- 1. Check for orphaned rows in direct material FK tables
WITH integrity_results AS (
    -- Mix components check
    SELECT 'mix_component' AS table_name, 
           COUNT(*) AS orphaned_count
    FROM mix_component
    WHERE NOT EXISTS (SELECT 1 FROM material WHERE material_id = mix_component.material_id)
    
    UNION ALL
    
    -- Material properties check
    SELECT 'material_property' AS table_name, 
           COUNT(*) AS orphaned_count
    FROM material_property
    WHERE NOT EXISTS (SELECT 1 FROM material WHERE material_id = material_property.material_id)
)
SELECT * FROM integrity_results;

-- 2. Check for related constraints in mix_component
WITH mix_constraint_results AS (
    -- Check all mix components point to valid mixes
    SELECT 'mix_component->mix' AS relationship, 
           COUNT(*) AS orphaned_count
    FROM mix_component
    WHERE NOT EXISTS (SELECT 1 FROM concrete_mix WHERE mix_id = mix_component.mix_id)
)
SELECT * FROM mix_constraint_results;

-- 3. Verify material count statistics before and after merge
SELECT
    'Previous SCM subtypes vs. current count' AS check_description,
    30 AS previous_scm_count, -- from the original query
    (SELECT COUNT(*) FROM material WHERE class_code = 'SCM') AS current_scm_count,
    16 AS merged_materials -- identified in material_merge_log
;

-- 4. Check mix count by dataset to ensure consistent mix compositions
SELECT
    d.dataset_name,
    COUNT(DISTINCT cm.mix_id) AS mix_count,
    COUNT(mc.component_id) AS component_count,
    COUNT(mc.component_id) / COUNT(DISTINCT cm.mix_id)::numeric AS avg_components_per_mix
FROM dataset d
JOIN concrete_mix cm ON d.dataset_id = cm.dataset_id 
JOIN mix_component mc ON cm.mix_id = mc.mix_id
GROUP BY d.dataset_name
ORDER BY d.dataset_name;
