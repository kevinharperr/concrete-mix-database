-- Verify database integrity after material consolidation
-- Check for orphaned rows and run counts before/after

-- 1. Check for orphaned rows in tables referencing material_id
SELECT 'mix_component' AS table_name, 
       COUNT(*) AS orphaned_rows
FROM mix_component mc 
WHERE NOT EXISTS (SELECT 1 FROM material WHERE material_id = mc.material_id)

UNION ALL

SELECT 'material_property' AS table_name, 
       COUNT(*) AS orphaned_rows
FROM material_property mp 
WHERE NOT EXISTS (SELECT 1 FROM material WHERE material_id = mp.material_id)

UNION ALL

SELECT 'aggregate_detail' AS table_name, 
       COUNT(*) AS orphaned_rows
FROM aggregate_detail ad 
WHERE NOT EXISTS (SELECT 1 FROM material WHERE material_id = ad.material_id)

UNION ALL

SELECT 'chemicalcomposition' AS table_name, 
       COUNT(*) AS orphaned_rows
FROM chemicalcomposition cc 
WHERE NOT EXISTS (SELECT 1 FROM material WHERE material_id = cc.material_id)

ORDER BY table_name;

-- 2. Check material composition counts to ensure they match
SELECT 'mix_component' AS table_name, COUNT(*) AS row_count FROM mix_component
UNION ALL
SELECT 'material' AS table_name, COUNT(*) AS row_count FROM material
UNION ALL
SELECT 'material_property' AS table_name, COUNT(*) AS row_count FROM material_property
ORDER BY table_name;

-- 3. Sample material data to verify proper standardization
SELECT 
    m.material_id,
    m.class_code,
    m.subtype_code,
    m.specific_name,
    COUNT(mc.mix_id) AS mix_count,
    COUNT(DISTINCT mp.property_id) AS property_count
FROM material m
LEFT JOIN mix_component mc ON m.material_id = mc.material_id
LEFT JOIN material_property mp ON m.material_id = mp.material_id
GROUP BY m.material_id, m.class_code, m.subtype_code, m.specific_name
ORDER BY mix_count DESC, m.class_code, m.subtype_code
LIMIT 10;

-- 4. Sample mix components to verify FK integrity
SELECT 
    mc.mix_id,
    m.mix_code,
    mc.material_id,
    mat.class_code,
    mat.subtype_code,
    mat.specific_name,
    mc.dosage_kg_m3
FROM mix_component mc
JOIN concrete_mix m ON mc.mix_id = m.mix_id
JOIN material mat ON mc.material_id = mat.material_id
WHERE m.dataset_id = 19 -- DS6 dataset
LIMIT 10;
