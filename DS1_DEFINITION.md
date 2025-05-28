# Dataset 1 Definition Document

*Last Updated: 21.05.2025, 16:40* (User's date, actual update based on current review)

## Source Data Overview

- **Source file**: `etl/ds1.csv`
- **Number of concrete mixes**: 1030 mixes (1030 data rows in CSV)
- **Dataset description**: Laboratory-tested concrete mixes from Taiwan with varying cement, SCM, and aggregate contents. This dataset was used to model the strength of high-performance concrete using artificial neural networks.
- **Research paper**: "MODELING OF STRENGTH OF HIGH-PERFORMANCE CONCRETE USING ARTIFICIAL NEURAL NETWORKS", I.-C. Yeh, published 1998 in Cement and Concrete Research.
- **Component types present**:
  - Cement (Portland Cement, ASTM Type I)
  - SCM (blast furnace slag, fly ash)
  - Water (ordinary tap water)
  - Admixture (superplasticizer, ASTM C494 Type G)
  - Aggregates (coarse crushed natural rock, fine washed natural river sand)
- **Test results included**:
  - Compressive strength (Fck) in MPa at various ages
    - Ages present in CSV: 3, 7, 14, 28, 56, 90, 91, 100, 120, 180, 270, 360, 365 days.
- **Mix characteristics**:
  - Includes high-performance concrete mixes.
  - w/c ratios in CSV range from 0.28 to 1.88. Paper (Table 2) mentions dataset w/c range 0.24-2.73.
  - w/b ratios in CSV range from 0.24 to 0.78. Paper (Table 2) mentions dataset w/b range 0.24-0.87.
  - Mixes were designed to study the effects of SCM and admixture on concrete strength.

## Column Analysis

| Source Column | Data Type | Sample Values | Notes |
|---------------|-----------|---------------|-------|
| cement_kg_m3 | Decimal | 540.00, 332.50, 198.60 | Portland cement content |
| blas_furnace_slag_kg_m3 | Decimal | 0.00, 142.50, 132.40 | Ground granulated blast furnace slag |
| fly_ash_kg_m3 | Decimal | 0.00 | Fly ash content (mostly zero in this dataset, but some non-zero values exist) |
| water_kg_m3 | Decimal | 162.00, 228.00, 192.00 | Water content |
| superplasticizer_kg_m3 | Decimal | 2.50, 0.00 | Superplasticizer admixture |
| superplasticizer_percentage_weight_of_cement_% | Decimal | 0.46, 0.00 | SP as percentage of cement weight (by mass of cement) |
| natural_coarse_aggregate_kg_m3 | Decimal | 1040.00, 932.00, 978.40 | Coarse aggregate content |
| natural_fine_aggregate_kg_m3 | Decimal | 676.00, 594.00, 825.50 | Fine aggregate content |
| testing_age | Integer | 28, 270, 365, 90 | Age in days when tested |
| water_cement_ratio | Decimal | 0.30, 0.69, 0.97 | Water to cement ratio |
| water_binder_ratio | Decimal | 0.30, 0.48, 0.58 | Water to binder ratio (binder assumed Cement + Slag + Fly Ash) |
| coarse-agg_fine-agg_ratio | Decimal | 1.54, 1.57, 1.19 | Coarse to fine aggregate ratio |
| fck_mpa | Decimal | 79.99, 61.89, 40.27 | Compressive strength in MPa |

## Field Mappings

### Dataset Model

| Database Field | Value | Notes |
|----------------|-------|-------|
| dataset_name | "Dataset 1" | More descriptive name: Concrete Compressive Strength Data Set (Yeh, 1998) |
| description | "A collection of 1030 laboratory-tested concrete mixes from Taiwan with varying cement, SCM, and aggregate contents, used for predicting compressive strength. Data originally compiled by I-Cheng Yeh. Strengths measured at various ages." | Updated description |
| source | "I-Cheng Yeh, Department of Civil Engineering, Chung-Hua University, Taiwan. Originally from UCI Machine Learning Repository, sourced from research paper." | From paper author and common knowledge of this dataset's origin |
| year_published | 1998 | Publication year of source paper |
| biblio_reference | (Link to BibliographicReference record below) |  |

### BibliographicReference Model (to be created and linked to Dataset)

| Database Field | Value | Notes |
|----------------|-------|-------|
| title          | "MODELING OF STRENGTH OF HIGH-PERFORMANCE CONCRETE USING ARTIFICIAL NEURAL NETWORKS" | From paper |
| authors        | "I.-C. Yeh" | From paper |
| journal        | "Cement and Concrete Research" | From paper |
| year           | 1998 | From paper |
| doi            | "10.1016/S0008-8846(98)00165-3" | Extracted from PII S0008-8846(98)00165-3, common practice for Elsevier DOIs. |
| url            | (e.g., "https://doi.org/10.1016/S0008-8846(98)00165-3") |  |
| citation       | "Yeh, I.-C. (1998). Modeling of strength of high-performance concrete using artificial neural networks. Cement and Concrete Research, 28(12), 1797-1808." | Standard citation format |

### ConcreteMix Model

| Source Column                                  | Database Field      | Transformation                                                         | Notes                                                                                                   |
| ---------------------------------------------- | ------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| (N/A - to be generated)                        | mix_code            | Generate using format "DS1-{i}"                                        | Where i is a 1-based sequential row ID                                                                  |
| water_cement_ratio                             | w_c_ratio           | Direct mapping                                                         |                                                                                                         |
| water_binder_ratio                             | w_b_ratio           | Direct mapping                                                         |                                                                                                         |
| (N/A)                                          | slump_mm            | N/A                                                                    | Paper's experimental program mentions slump for a subset, but not in main dataset CSV.                  |
| (N/A)                                          | air_content_pct     | N/A                                                                    |                                                                                                         |
| (N/A)                                          | target_strength_mpa | N/A                                                                    | Will be later calculated from compressive strength values.                                              |
| (N/A)                                          | density_kg_m3       | N/A                                                                    |                                                                                                         |
| (N/A)                                          | mix_date            | N/A                                                                    |                                                                                                         |
| coarse-agg_fine-agg_ratio                      | notes               | Add prefix "CA/FA ratio (source): "                                    | Stored in notes as no dedicated field. This is a source-provided ratio. Columns could be created later. |
| superplasticizer_percentage_weight_of_cement_% | notes               | Add prefix "SP % of cement (source): ". Append if notes already exist. | Stored in notes. This is a source-provided percentage. Columns could be created later.                  |

### Material Components

It's assumed that for each distinct material type (e.g., "Portland Cement CEM I"), a single `Material` record will be created and reused for all mixes.

#### Cement

| Source Column | Model | Database Field | Detail Model | Detail Fields | Notes |
|---------------|-------|----------------|-------------|--------------|-------|
| cement_kg_m3 | MixComponent | dosage_kg_m3 | (Linked Material) |  |  |
| *(Implied)*  | Material     | material_class | material_class | class_code: "CEMENT" |  |
| *(Implied)*  | Material     | specific_name  |               | "Portland Cement" | Paper: "Portland cement (ASTM type I)" |
| *(Implied)*  | Material     | subtype_code   |               | "CEM I" | Assumed general classification based on ASTM Type I |
| *(Implied)*  | Material     | (Other fields) | CementDetail  | strength_class: "42.5N" | Assumed common strength class, not specified in paper for all 1030 mixes. |

#### Blast Furnace Slag (SCM)

| Source Column | Model | Database Field | Detail Model | Detail Fields | Notes |
|---------------|-------|----------------|-------------|--------------|-------|
| blas_furnace_slag_kg_m3 | MixComponent | dosage_kg_m3 | (Linked Material) |  | Only create if dosage_kg_m3 > 0 |
| *(Implied)*  | Material     | material_class | MaterialClass | class_code: "SCM" |  |
| *(Implied)*  | Material     | specific_name  |               | "Ground Granulated Blast Furnace Slag" |  |
| *(Implied)*  | Material     | subtype_code   |               | "GGBS" |  |
| *(Implied)*  | Material     | (Other fields) | ScmDetail     | scm_type_code: "S" (typical for slag) or "GGBS" |  |

#### Fly Ash (SCM)

| Source Column | Model | Database Field | Detail Model | Detail Fields | Notes |
|---------------|-------|----------------|-------------|--------------|-------|
| fly_ash_kg_m3 | MixComponent | dosage_kg_m3 | (Linked Material) |  | Only create if dosage_kg_m3 > 0 |
| *(Implied)*  | Material     | material_class | MaterialClass | class_code: "SCM" |  |
| *(Implied)*  | Material     | specific_name  |               | "Fly Ash" | Paper: "manufactured by power plant" |
| *(Implied)*  | Material     | subtype_code   |               | "FA" |  |
| *(Implied)*  | Material     | (Other fields) | ScmDetail     | scm_type_code: "F" (typical for Class F) or "FA" | Paper doesn't specify class (e.g. F or C). "FA" is generic. |

#### Water

| Source Column | Model | Database Field | Detail Model | Detail Fields | Notes |
|---------------|-------|----------------|-------------|--------------|-------|
| water_kg_m3   | MixComponent | dosage_kg_m3 | (Linked Material) |  |  |
| *(Implied)*  | Material     | material_class | MaterialClass | class_code: "WATER" |  |
| *(Implied)*  | Material     | specific_name  |               | "Mixing Water" | Paper: "ordinary tap water" |
| *(Implied)*  | Material     | (Other fields) | N/A         | N/A          | No detail model for water |

#### Superplasticizer (Admixture)

| Source Column          | Model        | Database Field | Detail Model      | Detail Fields           | Notes                                                      |
| ---------------------- | ------------ | -------------- | ----------------- | ----------------------- | ---------------------------------------------------------- |
| superplasticizer_kg_m3 | MixComponent | dosage_kg_m3 | (Linked Material) |                         | Only create if dosage_kg_m3 > 0                                |
| *(Implied)*            | Material     | material_class | MaterialClass     | class_code: "ADM"       |                                                            |
| *(Implied)*            | Material     | specific_name  |                   | "Superplasticizer"      |                                                            |
| *(Implied)*            | Material     | subtype_code   |                   | "ASTM C494 Type G"      | From paper's experimental program section.                 |
| *(Implied)*            | Material     | (Other fields) | AdmixtureDetail   | solid_content_pct: 40.0 | Assumed typical value, paper notes lack of detail on this. |

#### Coarse Aggregate

| Source Column | Model | Database Field | Detail Model | Detail Fields | Notes |
|---------------|-------|----------------|-------------|--------------|-------|
| natural_coarse_aggregate_kg_m3 | MixComponent | dosage_kg_m3 | (Linked Material) |  |  |
| *(Implied)*  | Material     | material_class | MaterialClass | class_code: "AGGR_C" |  |
| *(Implied)*  | Material     | specific_name  |               | "Natural Coarse Aggregate" | Paper: "crushed natural rock" |
| *(Implied)*  | Material     | subtype_code   |               | "NCA" |  |
| *(Implied)*  | Material     | (Other fields) | AggregateDetail | d_lower_mm: 4.0 (Assumed) | Paper mentions 10mm max for experimental subset, and <20mm for general dataset. |
|               |              |                |               | d_upper_mm: 20.0 (Assumed) |  |

#### Fine Aggregate

| Source Column | Model | Database Field | Detail Model | Detail Fields | Notes |
|---------------|-------|----------------|-------------|--------------|-------|
| natural_fine_aggregate_kg_m3 | MixComponent | dosage_kg_m3 | (Linked Material) |  |  |
| *(Implied)*  | Material     | material_class | MaterialClass | class_code: "AGGR_F" |  |
| *(Implied)*  | Material     | specific_name  |               | "Natural Fine Aggregate" | Paper: "washed, natural river sand" |
| *(Implied)*  | Material     | subtype_code   |               | "NFA" |  |
| *(Implied)*  | Material     | (Other fields) | AggregateDetail | d_lower_mm: 0.0 (Assumed) |  |
|               |              |                |               | d_upper_mm: 4.0 (Assumed) |  |
|               |              |                |               | fineness_modulus: 3.0 | From paper's experimental program section. Assumed for whole dataset. |

### Performance Results

For each row in the CSV, one `PerformanceResult` record will be created.

| Source Column | Database Field | Value/Link                                                                                                                                   | Notes                                                                                                                                                                                                                                                                            |
| ------------- | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| fck_mpa       | value_num      | Direct mapping                                                                                                                               |                                                                                                                                                                                                                                                                                  |
| testing_age   | age_days       | Direct mapping                                                                                                                               |                                                                                                                                                                                                                                                                                  |
| *(Implied)*   | property       | Link to `PropertyDictionary` record for "Compressive Strength"                                                                               | Property Name: "Compressive Strength", Category: "Hardened Mechanical", Default Unit: "MPa"                                                                                                                                                                                      |
| *(Implied)*   | unit           | Link to `UnitLookup` record for "MPa"                                                                                                        | Unit Name: "Megapascal", Symbol: "MPa", Dimension: "Pressure/Stress"                                                                                                                                                                                                             |
| *(Implied)*   | test_method    | Link to `TestMethod` record for "Compressive Strength Test (Cylinder)"                                                                       | Method Name: "Compressive Strength Test (Cylinder, General)", Description: "General compressive strength test on cylindrical specimens as per common practice, e.g., 15cm cylinders mentioned in Yeh (1998)"                                                                     |
| *(Implied)*   | specimen       | N/A directly from CSV. If Specimens are created, link here. For this dataset, it might be simpler to link PerformanceResult directly to Mix. | Paper mentions "specimens of different sizes and shapes...converted into 15-cm cylinders". Creating individual specimen records per result from this CSV alone is not feasible without more specimen-specific data per row. Assumed all results are for 15-cm cylinder specimen. |

## Import Sequence

1.  **Setup:**
    *   Create/Get `BibliographicReference` record for Yeh (1998).
    *   Create/Get `Dataset` record, linking the `BibliographicReference`.
    *   Create/Get `MaterialClass` records (CEMENT, SCM, WATER, ADM, AGGR_C, AGGR_F) if they don't exist.
    *   Create/Get `Material` records for each unique material type (e.g., Portland Cement CEM I, GGBS, Fly Ash FA, Mixing Water, Superplasticizer ASTM C494 Type G, Natural Coarse Aggregate, Natural Fine Aggregate).
        *   For each `Material`, create its corresponding detail record (`CementDetail`, `ScmDetail`, `AdmixtureDetail`, `AggregateDetail`) with the specified or assumed properties.
    *   Create/Get `PropertyDictionary` record for "Compressive Strength".
    *   Create/Get `UnitLookup` record for "MPa".
    *   Create/Get `TestMethod` record for "Compressive Strength Test (Cylinder, General)".
2.  **For each row in source data (`ds1.csv`):**
    a.  Create `ConcreteMix` record, linking to the `Dataset`. Populate `mix_code`, `w_c_ratio`, `w_b_ratio`, and `notes`.
    b.  For each material component column (`cement_kg_m3`, `blas_furnace_slag_kg_m3`, etc.):
        i.  If the quantity is greater than 0:
            1.  Create a `MixComponent` record.
            2.  Link it to the current `ConcreteMix`.
            3.  Link it to the pre-created `Material` record for that component type.
            4.  Set `dosage_kg_m3` from the CSV column.
    c.  Create `PerformanceResult` record:
        i.  Link to the current `ConcreteMix`.
        ii. Link to the "Compressive Strength" `PropertyDictionary` record.
        iii. Link to the "MPa" `UnitLookup` record.
        iv. Link to the "Compressive Strength Test (Cylinder, General)" `TestMethod` record.
        v.  Set `value_num` from `fck_mpa`.
        vi. Set `age_days` from `testing_age`.

## Validation Checks

1.  **Dataset Record**: Ensure `Dataset` and its `BibliographicReference` are created correctly.
2.  **Material Records**:
    *   Verify that a single `Material` record is created for each distinct material type (e.g., one for all cement, one for all GGBS).
    *   Ensure all `Material` records have the correct `MaterialClass`.
    *   Ensure all `Material` records have their corresponding detail records (`CementDetail`, `ScmDetail`, etc.) with correct information (e.g., `fineness_modulus` for fine aggregate).
3.  **ConcreteMix Records**:
    *   Verify `mix_code` uniqueness and format.
    *   `w_c_ratio` and `w_b_ratio` from CSV are correctly imported.
    *   `notes` field correctly populated with CA/FA ratio and SP percentage.
4.  **MixComponent Records**:
    *   Ensure `MixComponent` records are created only for components with `dosage_kg_m3 > 0`.
    *   Verify correct linking to `ConcreteMix` and `Material`.
    *   Total number of `MixComponent` records should be sum of non-zero component entries in CSV.
5.  **PerformanceResult Records**:
    *   Verify correct linking to `ConcreteMix`, `PropertyDictionary`, `UnitLookup`, `TestMethod`.
    *   `value_num` and `age_days` correctly imported.
6.  **Ratio Checks (cross-verify CSV data with component quantities):**
    *   `w_c_ratio` (from CSV) vs. `water_kg_m3 / cement_kg_m3`. (Allow for small floating point discrepancies).
    *   `w_b_ratio` (from CSV) vs. `water_kg_m3 / (cement_kg_m3 + blas_furnace_slag_kg_m3 + fly_ash_kg_m3)`. (Handle division by zero if all binder components are zero, though unlikely for valid mixes).
    *   `coarse-agg_fine-agg_ratio` (from CSV) vs. `natural_coarse_aggregate_kg_m3 / natural_fine_aggregate_kg_m3`. (Handle division by zero if fine aggregate is zero).
    *   `superplasticizer_percentage_weight_of_cement_%` (from CSV) vs. `(superplasticizer_kg_m3 / cement_kg_m3) * 100`. (Handle division by zero if cement is zero).
7.  **Data Range Validation (based on Yeh (1998), Table 1 & 2, and general knowledge):**
    *   Cement: 71 - 540 kg/m³ (Paper Table 1: min 71, max 600, avg 232.2)
    *   Blast Furnace Slag: 0 - 359.4 kg/m³ (Paper Table 1: min 0, max 359, avg 79.2)
    *   Fly Ash: 0 - 200.1 kg/m³ (Paper Table 1: min 0, max 175, avg 46.4)
    *   Water: 121.75 - 247 kg/m³ (Paper Table 1: min 120, max 228, avg 186.4 - CSV has slightly higher max)
    *   Superplasticizer: 0 - 32.2 kg/m³ (Paper Table 1: min 0, max 20.8, avg 5.5 - CSV has higher max)
    *   Coarse Aggregate: 801 - 1134.3 kg/m³ (Paper Table 1: min 730, max 1322, avg 943.5)
    *   Fine Aggregate: 594 - 992.6 kg/m³ (Paper Table 1: min 486, max 968, avg 819.9)
    *   w/c ratio (source): 0.28 - 1.88 (Paper Table 2: min 0.24, max 2.73, avg 0.97)
    *   w/b ratio (source): 0.24 - 0.78 (Paper Table 2: min 0.24, max 0.87, avg 0.56)
    *   Compressive strength: ~2.33 - 82.6 MPa
    *   Testing Age: 1 - 365 days
8.  **Count Checks**:
    *   Number of `ConcreteMix` records should be 1030.
    *   Number of `PerformanceResult` records should be 1030.