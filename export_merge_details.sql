-- Export detailed information about merged materials
-- This script will work even after the original materials have been deleted

-- Create a temporary view with human-readable translations
CREATE TEMP VIEW material_merge_view AS
SELECT 
    mml.material_id_old,
    mml.material_id_new,
    mml.run_ts,
    mm.source AS merge_source,
    m.class_code,
    m.subtype_code,
    m.specific_name
FROM material_merge_log mml
JOIN (
    -- Add a source identifier
    SELECT material_id_old, 'comprehensive_cleanup' AS source 
    FROM material_merge_log 
    WHERE run_ts::date = '2025-05-08'
    UNION ALL
    SELECT material_id_old, 'previous_scm_cleanup' AS source 
    FROM material_merge_log 
    WHERE run_ts::date = '2025-05-07'
) mm ON mml.material_id_old = mm.material_id_old
JOIN material m ON mml.material_id_new = m.material_id
ORDER BY mml.run_ts DESC, mml.material_id_old;

-- Export the data
\copy (SELECT * FROM material_merge_view) TO 'material_merge_details_full.csv' CSV HEADER

-- Get canonical materials counts by type
SELECT 
    class_code,
    subtype_code,
    COUNT(*) AS original_material_count,
    STRING_AGG(material_id_old::text, ', ' ORDER BY material_id_old) AS merged_material_ids
FROM material_merge_view
GROUP BY class_code, subtype_code
ORDER BY class_code, subtype_code;

-- Drop the temporary view
DROP VIEW material_merge_view;
