# Concrete Mix Database Schema Dictionary

*Last Updated: 22.05.2025, 01:15*

## Overview

This document provides a comprehensive reference of the Concrete Mix Database (CDB) schema, including all models, fields, relationships, and constraints. Use this as the definitive source of truth when developing import scripts, queries, or making schema changes.

The database follows a relational structure with Django models mapped to PostgreSQL tables. All tables use the naming convention specified in each model's `Meta.db_table` attribute rather than Django's default naming pattern.

## Core Models

### Dataset

**Table**: `dataset`

*Represents a collection of concrete mixes from a specific source or experiment.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| dataset_id | AutoField | Primary Key | Unique identifier |
| dataset_name | CharField(100) | Non-null | Name of the dataset |
| description | TextField | Nullable | Detailed description |
| source | CharField(200) | Nullable | Origin of the dataset |
| import_date | DateTimeField | Non-null, Auto | Date when data was first imported |
| last_import_date | DateTimeField | Nullable, Auto | Date when data was last updated |
| year_published | IntegerField | Nullable | Year when the dataset was published |
| biblio_reference | ForeignKey(BibliographicReference) | Nullable, On Delete: SET NULL | Academic reference if applicable |

**Relationships**:
- Has many `ConcreteMix` (related name: `concrete_mixes`)

### ConcreteMix

**Table**: `concrete_mix`

*Represents a single concrete mix design with its properties and components.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| mix_id | AutoField | Primary Key | Unique identifier |
| dataset | ForeignKey(Dataset) | Non-null, On Delete: PROTECT | Dataset this mix belongs to |
| mix_code | CharField(50) | Nullable, Indexed | Mix identifier within dataset |
| w_c_ratio | DecimalField(6,3) | Nullable | Water to cement ratio |
| w_b_ratio | DecimalField(6,3) | Nullable | Water to binder ratio |
| target_slump_mm | DecimalField(8,2) | Nullable | Target slump in mm |
| slump_mm | DecimalField(8,2) | Nullable | Measured slump in mm |
| air_content_pct | DecimalField(5,2) | Nullable | Air content percentage |
| target_strength_mpa | DecimalField(8,2) | Nullable | Target compressive strength in MPa |
| density_kg_m3 | DecimalField(8,2) | Nullable | Fresh concrete density in kg/m³ |
| mix_date | DateField | Nullable | Date when mix was created |
| notes | TextField | Nullable | Additional notes |

**Relationships**:
- Belongs to one `Dataset` (foreign key: `dataset`)
- Has many `MixComponent` (related name: `components`)
- Has many `Specimen` (related name: `specimens`)
- Has many `ConcreteMixReference` (related name: `references`)
- Has many `PerformanceResult` (related name: `performance_results`)
- Has many `SustainabilityMetric` (related name: `sustainability_metrics`)
- Has many `MixStrengthClassification` (related name: `strength_classifications`)

### Material

**Table**: `material`

*Represents a concrete component material (cement, aggregate, etc).*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| material_id | AutoField | Primary Key | Unique identifier |
| material_class | ForeignKey(MaterialClass) | Non-null, On Delete: RESTRICT | Material classification |
| subtype_code | CharField(60) | Nullable, Indexed | Specific type within class |
| specific_name | TextField | Nullable | Most specific name from source |
| manufacturer | TextField | Nullable | Material manufacturer |
| density_kg_m3 | DecimalField(8,2) | Nullable | Material density in kg/m³ |
| description | TextField | Nullable | Additional description |
| origin | CharField(100) | Nullable | Geographical origin |

**Relationships**:
- Belongs to one `MaterialClass` (foreign key: `material_class`)
- Has many `MixComponent` (related name: `mix_usages`)
- Has many `MaterialProperty` (related name: `properties`)
- Has one `CementDetail` (related name: `cement_detail`)
- Has one `ScmDetail` (related name: `scm_detail`)
- Has one `AggregateDetail` (related name: `aggregate_detail`)
- Has one `AdmixtureDetail` (related name: `admixture_detail`)
- Has one `FibreDetail` (related name: `fibre_detail`)

### MixComponent

**Table**: `mix_component`

*Represents a specific material used in a concrete mix with quantity.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| component_id | AutoField | Primary Key | Unique identifier |
| mix | ForeignKey(ConcreteMix) | Non-null, On Delete: CASCADE | Concrete mix |
| material | ForeignKey(Material) | Non-null, On Delete: PROTECT | Material used |
| dosage_kg_m3 | DecimalField(10,3) | Non-null | Dosage in kg/m³ |
| volume_fraction | DecimalField(6,4) | Nullable | Volume fraction |
| mass_fraction | DecimalField(6,4) | Nullable | Mass fraction |
| notes | TextField | Nullable | Additional notes |
| is_cementitious | BooleanField | Nullable | Flag if component counts towards binder content |

**Relationships**:
- Belongs to one `ConcreteMix` (foreign key: `mix`)
- Belongs to one `Material` (foreign key: `material`)

### MaterialClass

**Table**: `material_class`

*Represents a category of construction materials (e.g., cement, aggregate).*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| class_code | CharField(8) | Primary Key | Short code identifier (e.g., CEMENT, SCM, AGGR_C, AGGR_F) |
| class_name | CharField(60) | Nullable | Full descriptive name |

**Relationships**:
- Has many `Material` (related name: `materials`)

## Performance Models

### Specimen

**Table**: `specimen`

*Represents a physical test specimen made from a concrete mix.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| specimen_id | AutoField | Primary Key | Unique identifier |
| mix | ForeignKey(ConcreteMix) | Non-null, On Delete: CASCADE | Concrete mix used |
| specimen_code | CharField(50) | Nullable | Specimen identifier |
| shape | CharField(50) | Nullable | Specimen shape |
| dimensions_mm | CharField(50) | Nullable | Dimensions in mm |
| date_cast | DateField | Nullable | Date specimen was cast |
| curing_regime | ForeignKey(CuringRegime) | Nullable, On Delete: SET NULL | Curing regime |
| notes | TextField | Nullable | Additional notes |

**Relationships**:
- Belongs to one `ConcreteMix` (foreign key: `mix`)
- Belongs to one `CuringRegime` (foreign key: `curing_regime`)
- Has many `PerformanceResult` (related name: `test_results`)

### PerformanceResult

**Table**: `performance_result`

*Represents a test result on a concrete specimen or mix.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| result_id | AutoField | Primary Key | Unique identifier |
| mix | ForeignKey(ConcreteMix) | Non-null, On Delete: CASCADE | Concrete mix tested |
| category | CharField(15) | Non-null | Category (choices: 'fresh', 'hardened', 'durability') |
| property | ForeignKey(PropertyDictionary) | Nullable, On Delete: PROTECT | Property being measured |
| test_method | ForeignKey(TestMethod) | Nullable, On Delete: SET NULL | Test method used |
| age_days | IntegerField | Nullable, Indexed | Test age in days |
| value_num | DecimalField(16,4) | Nullable | Numeric test result |
| unit | ForeignKey(UnitLookup) | Nullable, On Delete: SET NULL | Result unit |
| specimen | ForeignKey(Specimen) | Nullable, On Delete: SET NULL | Test specimen |
| curing_regime | ForeignKey(CuringRegime) | Nullable, On Delete: SET NULL | Curing regime used |
| test_conditions | TextField | Nullable | Test conditions details |

**Relationships**:
- Belongs to one `ConcreteMix` (foreign key: `mix`)
- Belongs to one `Specimen` (foreign key: `specimen`)
- Belongs to one `PropertyDictionary` (foreign key: `property`)
- Belongs to one `TestMethod` (foreign key: `test_method`)
- Belongs to one `UnitLookup` (foreign key: `unit`)

## Lookup/Reference Models

### PropertyDictionary

**Table**: `property_dictionary`

*Defines standardized material properties and their units.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| property_name | CharField(60) | Primary Key | Unique code/key for the property, e.g., 'cao_pct' |
| display_name | CharField(120) | Non-null | User-friendly name, e.g., 'CaO (%)' |
| property_group | CharField(30) | Non-null | Category of the property (choices: 'chemical', 'physical', 'mechanical', 'thermal') |
| default_unit | ForeignKey(UnitLookup) | Nullable, On Delete: SET NULL | Default unit |

**Relationships**:
- Has many `PerformanceResult` (related name: `result_property`)
- Has many `MaterialProperty` (related name: `material_property`)

### UnitLookup

**Table**: `unit_lookup`

*Defines measurement units used in the database.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| unit_id | AutoField | Primary Key | Unique identifier |
| unit_name | CharField(50) | Non-null | Unit name |
| unit_symbol | CharField(20) | Non-null | Unit symbol |
| dimension | CharField(50) | Nullable | Physical dimension |
| conversion_factor | DecimalField(12,6) | Nullable | Conversion factor to SI unit |
| base_unit | ForeignKey(UnitLookup) | Nullable, On Delete: SET NULL | Base unit (self reference) |

**Relationships**:
- Self-referential to `UnitLookup` (foreign key: `base_unit`)
- Has many `PropertyDictionary` (related name: `property_units`)
- Has many `PerformanceResult` (related name: `result_units`)

### TestMethod

**Table**: `test_method`

*Defines standardized test methods for concrete testing.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| test_method_id | AutoField | Primary Key | Unique identifier |
| standard | ForeignKey(Standard) | Nullable, On Delete: SET NULL | Related standard |
| clause | CharField(30) | Nullable | Specific clause in standard |
| description | TextField | Nullable | Detailed description |

**Relationships**:
- Belongs to one `Standard` (foreign key: `standard`)
- Has many `PerformanceResult` (related name: `results`)

### Standard

**Table**: `standard`

*Defines industry standards (e.g., ASTM, EN) referenced in the database.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| standard_id | AutoField | Primary Key | Unique identifier |
| code | CharField(50) | Non-null | Standard code (e.g., ASTM C39) |
| title | CharField(200) | Nullable | Standard title |
| organization | CharField(100) | Nullable | Standards organization |
| year | IntegerField | Nullable | Publication year |

**Relationships**:
- Has many `TestMethod` (related name: `test_methods`)
- Has many `ConcreteMixReference` (related name: `mix_references`)

### CuringRegime

**Table**: `curing_regime`

*Defines concrete specimen curing methods.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| regime_id | AutoField | Primary Key | Unique identifier |
| regime_name | CharField(100) | Non-null | Regime name |
| description | TextField | Nullable | Detailed description |
| temperature_c | DecimalField(5,2) | Nullable | Temperature in Celsius |
| humidity_pct | DecimalField(5,2) | Nullable | Relative humidity percentage |
| duration_days | IntegerField | Nullable | Duration in days |

**Relationships**:
- Has many `Specimen` (related name: `specimens`)

## Detail Models

### CementDetail

**Table**: `cement_detail`

*Provides specific properties for cement materials.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| material | OneToOneField(Material) | Primary Key, On Delete: CASCADE | Associated material |
| strength_class | CharField(10) | Nullable | Cement strength class |
| clinker_pct | DecimalField(6,2) | Nullable | Clinker percentage |

**Relationships**:
- One-to-one with `Material` (foreign key: `material`)

### ScmDetail

**Table**: `scm_detail`

*Provides specific properties for supplementary cementitious materials.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| material | OneToOneField(Material) | Primary Key, On Delete: CASCADE | Associated material |
| scm_type_code | CharField(20) | Nullable | SCM type code (e.g., F, N, SF) |
| loi_pct | DecimalField(6,2) | Nullable | Loss on ignition percentage |

**Relationships**:
- One-to-one with `Material` (foreign key: `material`)

### AggregateDetail

**Table**: `aggregate_detail`

*Provides specific properties for aggregate materials.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| material | OneToOneField(Material) | Primary Key, On Delete: CASCADE | Associated material |
| d_lower_mm | DecimalField(8,2) | Nullable | Lower bound size in mm |
| d_upper_mm | DecimalField(8,2) | Nullable | Upper bound size in mm |
| bulk_density_kg_m3 | DecimalField(8,2) | Nullable | Bulk density in kg/m³ |
| water_absorption_pct | DecimalField(6,2) | Nullable | Water absorption percentage |
| fineness_modulus | DecimalField(6,2) | Nullable | Fineness modulus |

**Relationships**:
- One-to-one with `Material` (foreign key: `material`)
- Has many `AggregateConstituent` (related name: `constituents`)

### AdmixtureDetail

**Table**: `admixture_detail`

*Provides specific properties for chemical admixtures.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| material | OneToOneField(Material) | Primary Key, On Delete: CASCADE | Associated material |
| solid_content_pct | DecimalField(6,2) | Nullable | Solid content percentage |
| specific_gravity | DecimalField(6,3) | Nullable | Specific gravity |
| chloride_content_pct | DecimalField(6,3) | Nullable | Chloride content percentage |

**Relationships**:
- One-to-one with `Material` (foreign key: `material`)

### FibreDetail

**Table**: `fibre_detail`

*Provides specific properties for fibre materials.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| material | OneToOneField(Material) | Primary Key, On Delete: CASCADE | Associated material |
| fibre_type | CharField(50) | Nullable | Fibre type |
| length_mm | DecimalField(8,2) | Nullable | Fibre length in mm |
| diameter_mm | DecimalField(8,4) | Nullable | Fibre diameter in mm |
| aspect_ratio | DecimalField(8,2) | Nullable | Length to diameter ratio |
| tensile_strength_mpa | DecimalField(10,2) | Nullable | Tensile strength in MPa |

**Relationships**:
- One-to-one with `Material` (foreign key: `material`)

## Other Models

### MaterialProperty

**Table**: `material_property`

*Stores specific properties of materials.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| property_id | AutoField | Primary Key | Unique identifier |
| material | ForeignKey(Material) | Non-null, On Delete: CASCADE | Associated material |
| property | ForeignKey(PropertyDictionary) | Non-null, On Delete: CASCADE | Property type |
| value_num | DecimalField(12,6) | Nullable | Numeric property value |
| value_text | CharField(100) | Nullable | Text property value |
| unit | ForeignKey(UnitLookup) | Nullable, On Delete: SET NULL | Value unit |

**Relationships**:
- Belongs to one `Material` (foreign key: `material`)
- Belongs to one `PropertyDictionary` (foreign key: `property`)
- Belongs to one `UnitLookup` (foreign key: `unit`)

### BibliographicReference

**Table**: `bibliographic_reference`

*Stores academic references for datasets.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| reference_id | AutoField | Primary Key | Unique identifier |
| title | CharField(255) | Nullable | Publication title |
| authors | TextField | Nullable | Author names |
| journal | CharField(255) | Nullable | Journal name |
| year | IntegerField | Nullable | Publication year |
| doi | CharField(100) | Nullable | Digital Object Identifier |
| url | URLField | Nullable | Web link |
| citation | TextField | Nullable | Full citation text |

**Relationships**:
- Has many `Dataset` (related name: `datasets`)

### ConcreteMixReference

**Table**: `concrete_mix_reference`

*Links concrete mixes to standards they comply with.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| ref_id | AutoField | Primary Key | Unique identifier |
| mix | ForeignKey(ConcreteMix) | Non-null, On Delete: CASCADE | Concrete mix |
| standard | ForeignKey(Standard) | Non-null, On Delete: CASCADE | Compliance standard |
| compliance_notes | TextField | Nullable | Compliance details |

**Relationships**:
- Belongs to one `ConcreteMix` (foreign key: `mix`)
- Belongs to one `Standard` (foreign key: `standard`)

### SustainabilityMetric

**Table**: `sustainability_metric`

*Stores environmental impact metrics for concrete mixes.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| metric_id | AutoField | Primary Key | Unique identifier |
| mix | ForeignKey(ConcreteMix) | Non-null, On Delete: CASCADE | Concrete mix |
| metric_name | CharField(100) | Non-null | Metric name |
| value | DecimalField(12,6) | Nullable | Metric value |
| unit | CharField(50) | Nullable | Metric unit |
| source | CharField(100) | Nullable | Data source |
| notes | TextField | Nullable | Additional notes |

**Relationships**:
- Belongs to one `ConcreteMix` (foreign key: `mix`)

### StrengthClass

**Table**: `strength_class`

*Defines concrete strength classification standards.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| class_id | AutoField | Primary Key | Unique identifier |
| class_code | CharField(20) | Non-null | Class code (e.g., C30/37) |
| standard_name | CharField(50) | Nullable | Standard name (e.g., EN 206) |
| min_strength | DecimalField(6,2) | Nullable | Minimum required strength |
| description | TextField | Nullable | Detailed description |

**Relationships**:
- Has many `MixStrengthClassification` (related name: `mix_classifications`)

### MixStrengthClassification

**Table**: `mix_strength_classification`

*Associates concrete mixes with strength classes.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Unique identifier |
| mix | ForeignKey(ConcreteMix) | Non-null, On Delete: CASCADE | Concrete mix |
| strength_class | ForeignKey(StrengthClass) | Non-null, On Delete: CASCADE | Strength class |
| classification_type | CharField(50) | Nullable | Classification method |
| notes | TextField | Nullable | Additional notes |

**Relationships**:
- Belongs to one `ConcreteMix` (foreign key: `mix`)
- Belongs to one `StrengthClass` (foreign key: `strength_class`)

## Import/Staging Models

### ColumnMap

**Table**: `column_map`

*Maps source data columns to database fields for imports.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| map_id | AutoField | Primary Key | Unique identifier |
| source_column | CharField(100) | Non-null | Source data column name |
| target_model | CharField(100) | Nullable | Target model name |
| target_field | CharField(100) | Nullable | Target field name |
| transformation | TextField | Nullable | Transformation logic |
| notes | TextField | Nullable | Additional notes |

### StagingRaw

**Table**: `staging_raw`

*Temporarily stores raw data during import process.*

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Unique identifier |
| source_file | CharField(255) | Nullable | Source file name |
| row_num | IntegerField | Nullable | Source row number |
| data_json | JSONField | Nullable | Raw data in JSON format |
| status | CharField(50) | Nullable | Processing status |
| error_message | TextField | Nullable | Error message if any |
| processed_date | DateTimeField | Nullable | Processing timestamp |

## Database Relationships Diagram

```
[Dataset] 1──*─┐
               │
[BibRef]────1──┘

               ┌──*─[MixComponent]─*──[Material]─1──[MaterialClass]
               │                       │
               │                       │
[Dataset]─1─*─[ConcreteMix]            └─1─┬─[CementDetail]
               │                           ├─[ScmDetail]
               │                           ├─[AggregateDetail]
               │                           ├─[AdmixtureDetail]
               │                           └─[FibreDetail]
               │
               ├──*─[Specimen]─*──[PerformanceResult]
               ├──*─[ConcreteMixReference]─*──[Standard]─1──*─[TestMethod]
               ├──*─[SustainabilityMetric]
               └──*─[MixStrengthClassification]─*──[StrengthClass]
```

## Important Notes for Import Scripts

1. **Primary Keys**: Most models use an auto-incrementing ID field as the primary key, except for detail models which use the material foreign key as their primary key.

2. **Detail Models**: When creating materials, don't forget to create appropriate detail records based on the material class.

3. **Field Naming**: Always use the exact field names as specified in this document. The database has evolved over time and some expected field names (like 'name' or 'description') may have been changed.

4. **Nullable Fields**: Fields marked as nullable can be imported with None/NULL values, but required fields must have valid values.

5. **Performance Results**: When importing performance results, ensure proper linkage to property dictionary and units.
