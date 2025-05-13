# Concrete Mix Database Data Dictionary

*Generated on: 2025-04-23 15:17:49*

This document provides comprehensive information about all tables and columns in the concrete mix database.

## Tables

- [admixture_detail](#admixture_detail)
- [aggregate_constituent](#aggregate_constituent)
- [aggregate_detail](#aggregate_detail)
- [bibliographic_reference](#bibliographic_reference)
- [cement_detail](#cement_detail)
- [column_map](#column_map)
- [concrete_mix](#concrete_mix)
- [concrete_mix_reference](#concrete_mix_reference)
- [curing_regime](#curing_regime)
- [dataset](#dataset)
- [fibre_detail](#fibre_detail)
- [material](#material)
- [material_class](#material_class)
- [material_property](#material_property)
- [mix_component](#mix_component)
- [performance_result](#performance_result)
- [property_dictionary](#property_dictionary)
- [scm_detail](#scm_detail)
- [specimen](#specimen)
- [staging_raw](#staging_raw)
- [standard](#standard)
- [sustainability_metric](#sustainability_metric)
- [test_method](#test_method)
- [unit_lookup](#unit_lookup)

## admixture_detail

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| material_id | integer | NO |  | Foreign key to material.material_id |
| solid_content_pct | numeric | YES |  |  |
| specific_gravity | numeric | YES |  |  |
| chloride_content_pct | numeric | YES |  |  |

## aggregate_constituent

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| material_id | integer | NO |  | Foreign key to material.material_id |
| rc_pct | numeric | YES |  |  |
| ru_pct | numeric | YES |  |  |
| ra_pct | numeric | YES |  |  |
| rb_pct | numeric | YES |  |  |
| fl_pct | numeric | YES |  |  |
| x_pct | numeric | YES |  |  |
| rg_pct | numeric | YES |  |  |

## aggregate_detail

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| material_id | integer | NO |  | Foreign key to material.material_id |
| d_lower_mm | numeric | YES |  |  |
| d_upper_mm | numeric | YES |  |  |
| bulk_density_kg_m3 | numeric | YES |  |  |
| water_absorption_pct | numeric | YES |  |  |
| fineness_modulus | numeric | YES |  |  |

## bibliographic_reference

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| reference_id | integer | NO |  |  |
| author | text | YES |  |  |
| title | text | YES |  |  |
| publication | text | YES |  |  |
| year | integer | YES |  |  |
| doi | character varying(100) | YES |  |  |
| citation_text | text | YES |  |  |

## cement_detail

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| material_id | integer | NO |  | Foreign key to material.material_id |
| strength_class | character varying(10) | YES |  |  |
| clinker_pct | numeric | YES |  |  |

## column_map

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| dataset_id | integer | NO |  | Foreign key to dataset.dataset_id |
| source_column | character varying(128) | NO |  |  |
| target_table | character varying(64) | YES |  |  |
| target_column | character varying(64) | YES |  |  |
| unit_hint | character varying(20) | YES |  |  |
| needs_conversion | boolean | YES |  |  |

## concrete_mix

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| mix_id | integer | NO |  |  |
| dataset_id | integer | NO |  | Foreign key to dataset.dataset_id |
| mix_code | character varying(50) | YES |  |  |
| date_created | date | YES |  |  |
| region_country | character varying(60) | YES |  |  |
| strength_class | character varying(10) | YES |  |  |
| target_slump_mm | numeric | YES |  |  |
| w_c_ratio | numeric | YES |  |  |
| w_b_ratio | numeric | YES |  |  |
| notes | text | YES |  |  |

## concrete_mix_reference

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| mix_id | integer | NO |  | Foreign key to concrete_mix.mix_id |
| reference_id | integer | NO |  | Foreign key to bibliographic_reference.reference_id |

## curing_regime

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| curing_regime_id | integer | NO |  |  |
| description | character varying(100) | YES |  |  |

## dataset

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| dataset_id | integer | NO |  |  |
| dataset_name | character varying(60) | YES |  |  |
| license | text | YES |  |  |

## fibre_detail

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| material_id | integer | NO |  | Foreign key to material.material_id |
| length_mm | numeric | YES |  |  |
| diameter_mm | numeric | YES |  |  |
| aspect_ratio | numeric | YES |  |  |
| tensile_strength_mpa | numeric | YES |  |  |

## material

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| material_id | integer | NO |  |  |
| class_code | character varying(8) | NO |  | Foreign key to material_class.class_code |
| subtype_code | character varying(20) | YES |  |  |
| brand_name | text | YES |  |  |
| manufacturer | text | YES |  |  |
| standard_ref | character varying(30) | YES |  |  |
| country_of_origin | character varying(60) | YES |  |  |
| date_added | date | YES |  |  |
| source_dataset | character varying(50) | YES |  |  |

## material_class

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| class_code | character varying(8) | NO |  |  |
| class_name | character varying(60) | YES |  |  |

## material_property

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| property_id | integer | NO |  |  |
| material_id | integer | NO |  | Foreign key to material.material_id |
| property_name | character varying(60) | YES |  | Foreign key to property_dictionary.property_name |
| property_group | character varying(30) | YES |  |  |
| value_num | numeric | YES |  |  |
| unit_id | integer | YES |  | Foreign key to unit_lookup.unit_id |
| test_method_id | integer | YES |  | Foreign key to test_method.test_method_id |
| test_date | date | YES |  |  |

## mix_component

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| component_id | integer | NO |  |  |
| mix_id | integer | NO |  | Foreign key to concrete_mix.mix_id |
| material_id | integer | NO |  | Foreign key to material.material_id |
| dosage_kg_m3 | numeric | NO |  |  |
| dosage_pct_binder | numeric | YES |  |  |
| replacement_pct | numeric | YES |  |  |
| is_cementitious | boolean | YES |  |  |

## performance_result

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| result_id | integer | NO |  |  |
| mix_id | integer | NO |  | Foreign key to concrete_mix.mix_id |
| category | character varying(15) | YES |  |  |
| test_method_id | integer | YES |  | Foreign key to test_method.test_method_id |
| age_days | integer | YES |  |  |
| value_num | numeric | YES |  |  |
| unit_id | integer | YES |  | Foreign key to unit_lookup.unit_id |
| specimen_id | integer | YES |  | Foreign key to specimen.specimen_id |
| curing_regime_id | integer | YES |  | Foreign key to curing_regime.curing_regime_id |
| test_conditions | text | YES |  |  |

## property_dictionary

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| property_name | character varying(60) | NO |  |  |
| display_name | character varying(120) | YES |  |  |
| property_group | character varying(30) | YES |  |  |
| default_unit_id | integer | YES |  | Foreign key to unit_lookup.unit_id |

## scm_detail

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| material_id | integer | NO |  | Foreign key to material.material_id |
| scm_type_code | character varying(20) | YES |  |  |
| loi_pct | numeric | YES |  |  |

## specimen

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| specimen_id | integer | NO |  |  |
| shape | character varying(20) | YES |  |  |
| nominal_length_mm | numeric | YES |  |  |
| nominal_diameter_mm | numeric | YES |  |  |
| notes | text | YES |  |  |

## staging_raw

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| raw_id | integer | NO |  |  |
| dataset_id | integer | YES |  | Foreign key to dataset.dataset_id |
| row_json | jsonb | YES |  |  |
| ingest_ts | timestamp with time zone | YES |  |  |

## standard

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| standard_id | integer | NO |  |  |
| code | character varying(30) | NO |  |  |
| title | text | YES |  |  |

## sustainability_metric

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| metric_id | integer | NO |  |  |
| mix_id | integer | NO |  | Foreign key to concrete_mix.mix_id |
| metric_code | character varying(15) | YES |  |  |
| value_num | numeric | YES |  |  |
| unit_id | integer | YES |  | Foreign key to unit_lookup.unit_id |
| method_ref | character varying(30) | YES |  |  |

## test_method

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| test_method_id | integer | NO |  |  |
| standard_id | integer | YES |  | Foreign key to standard.standard_id |
| clause | character varying(30) | YES |  |  |
| description | text | YES |  |  |

## unit_lookup

| Column | Type | Nullable | Description | Notes |
|--------|------|----------|-------------|-------|
| unit_id | integer | NO |  |  |
| unit_symbol | character varying(20) | NO |  |  |
| si_factor | numeric | YES |  |  |
| description | text | YES |  |  |

## Common Query Examples

### Get Mix Compositions with Material Details

```sql

SELECT 
    cm.mix_code,
    m.material_type,
    m.subtype,
    mc.quantity_kg_m3,
    mc.w_c_ratio
FROM mixcomposition mc
JOIN concretemix cm ON mc.mix_id = cm.mix_id
LEFT JOIN material m ON mc.material_id = m.material_id
ORDER BY cm.mix_code

```

### Get Strength vs W/C Ratio for 28-Day Tests

```sql

SELECT 
    cm.mix_code,
    cm.source_dataset,
    mc.w_c_ratio,
    pr.test_value as strength_28d
FROM mixcomposition mc
JOIN material m ON mc.material_id = m.material_id
JOIN concretemix cm ON mc.mix_id = cm.mix_id
JOIN performanceresult pr ON cm.mix_id = pr.mix_id
WHERE 
    m.material_type = 'cement' AND
    pr.test_type = 'compressive_strength' AND
    pr.test_age_days = 28 AND
    mc.w_c_ratio IS NOT NULL
ORDER BY mc.w_c_ratio

```

