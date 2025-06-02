# Dataset 3 Definition Document

*Last Updated: 28.05.2025, 18:20*

## Source Data Overview

-   **Source file**: `etl/ds3.csv`
-   **Number of concrete mixes**: 734 mixes (734 data rows in CSV).
-   **Dataset description**: A multinational dataset comprising 2,300 concrete mixtures (subset of 734 used for this import) incorporating recycled aggregates, used for predicting compressive strength with ensemble learning algorithms. Data compiled from 81 studies.
-   **Research paper**: "Accuracy Prediction of Compressive Strength of Concrete Incorporating Recycled Aggregate Using Ensemble Learning Algorithms: Multinational Dataset", Menghay Phoeuk and Minho Kwon, published 2023 in Advances in Civil Engineering.
-   **Component types present**:
    -   Cement (Portland Cement)
    *   Water (Effective Water)
    *   Natural Coarse Aggregate (NCA)
    *   Recycled Coarse Aggregate (RCA)
    *   Natural Fine Aggregate (NFA)
    *   Fly Ash (SCM)
    *   Silica Fume (SCM)
    *   Blast Furnace Slag (BFS/GGBS - SCM)
    *   Superplasticizer (SP - Admixture)
-   **Test results included**:
    -   Compressive Strength (`CS fck (mpa)`) - **All results are for 28-day strength.** Values are normalized to represent equivalent strength of 100x200 mm cylindrical specimens.
-   **Mix characteristics**:
    *   Focus on Recycled Aggregate Concrete (RAC).
    *   Includes various SCMs and superplasticizer.
    *   W/C ratio to be calculated from `eff_water (kg/m3)` and `cement (kg/m3)`.
    *   W/B ratio to be calculated from `eff_water (kg/m3)` and sum of (cement + fly ash + silica fume + BFS).
    *   Original source paper reference and year for each mix are available and will be stored in notes.
    *   Country of origin for each mix study is available.

## Column Analysis (from `ds3.csv`)

| Source CSV Column       | Data Type     | Sample Values (illustrative) | Notes                                                                                                                      |
| :---------------------- | :------------ | :--------------------------- | :------------------------------------------------------------------------------------------------------------------------- |
| mix_number              | Integer       | 1, 100, 500, 734             | Unique identifier within this CSV.                                                                                         |
| mix_mark(reference ...) | Text          | (empty), K200N, HC             | Original mix code from source study. To be stored in `ConcreteMix.notes`.                                                |
| cement (kg/m3)          | Decimal       | 280, 435.7, 380, 216         | Cement content in kg/m³.                                                                                                   |
| eff_water (kg/m3)       | Decimal       | 180, 204.8, 195              | Effective water content in kg/m³.                                                                                          |
| NCA (kg/m3)             | Decimal       | 832, 0, 1107, 780.6          | Natural Coarse Aggregate content in kg/m³.                                                                                 |
| RCA (kg/m3)             | Decimal       | 0, 334.6, 189.24, 539        | Recycled Coarse Aggregate content in kg/m³.                                                                                |
| NFA (kg/m3)             | Decimal       | 1045, 564.3, 710             | Natural Fine Aggregate content in kg/m³.                                                                                   |
| fly ash (kg/m3)         | Decimal       | 0, 136.5, 76, 123.5          | Fly Ash content in kg/m³.                                                                                                  |
| silica fume (kg/m3)     | Decimal       | 0, 28.5, 39, 17.5            | Silica Fume content in kg/m³.                                                                                              |
| BFS (kg/m3)             | Decimal       | 0, 71, 142, 214.5            | Blast Furnace Slag content in kg/m³.                                                                                       |
| SP (kg/m3)              | Decimal       | 0, 5.01, 2.54, 4.1           | Superplasticizer content in kg/m³.                                                                                         |
| Testing Age (day)       | Integer       | 28, 7, 90, 1, 3, 14, 56      | Age of concrete at testing. (Paper Table 3 indicates range 1-90 for CS prediction model, CSV seems to contain various ages for this dataset) |
| CS fck (mpa)            | Decimal       | 22.45, 56.21, 30.15, 10.76   | Compressive strength in MPa. **All values are for 28-day strength, normalized to 100x200mm cylinder equivalent.**      |
| ref.                    | Text          | Alexandridou et al, Singh et al | Original source paper reference for the mix data. To be stored in `ConcreteMix.notes`.                                   |
| year                    | Integer       | 2018, 2017                   | Year of the original source paper. To be stored in `ConcreteMix.notes`.                                                    |
| country                 | Text          | Greece, India, China         | Country of origin of the study for the mix. To be stored in `ConcreteMix.region_country`.                                    |

**Self-Correction during `DS3_DEFINITION.md` creation:**
*   The initial statement that all DS3 data is 28-day strength was based on the paper's abstract and analysis focus. However, the `ds3.csv` file clearly contains a "Testing Age (day)" column with values other than 28 (e.g., 1, 7, 90).
*   **Decision for DS3 Definition:** We will import the `Testing Age (day)` as provided in the CSV for each `PerformanceResult`. The note about normalization to 100x200mm cylinder equivalents for `CS fck (mpa)` remains valid.

## Field Mappings

### Dataset Model

| Database Field     | Value                                                                                                 | Notes                                 |
| :----------------- | :---------------------------------------------------------------------------------------------------- | :------------------------------------ |
| dataset_name       | "Dataset 3"                                                                                           | Chosen for simplicity.                |
| description        | "Multinational dataset of concrete with recycled aggregates (primarily coarse RCA) used for compressive strength prediction with ensemble learning. Compiled by Phoeuk and Kwon (2023) from 81 studies. Compressive strength values normalized to 100x200mm cylinder equivalent." |  |
| source             | "Menghay Phoeuk, Minho Kwon (2023). Aggregated dataset from 81 prior studies."                          | Main compilers of this dataset.     |
| year_published     | 2023                                                                                                  | Year of the Phoeuk and Kwon paper.    |
| biblio_reference   | (Link to BibliographicReference record for Phoeuk and Kwon, 2023)                                     |                                       |

### BibliographicReference Model (for the main DS3 paper by Phoeuk and Kwon)

| Database Field   | Value                                                                                                         |
| :--------------- | :------------------------------------------------------------------------------------------------------------ |
| author           | "Phoeuk, M., Kwon, M."                                                                                         |
| title            | "Accuracy Prediction of Compressive Strength of Concrete Incorporating Recycled Aggregate Using Ensemble Learning Algorithms: Multinational Dataset" |
| publication      | "Advances in Civil Engineering"                                                                                 |
| year             | 2023                                                                                                          |
| doi              | "10.1155/2023/5076429"                                                                                        |
| url              | "https://doi.org/10.1155/2023/5076429"                                                                         |
| citation_text    | "Phoeuk, M., & Kwon, M. (2023). Accuracy Prediction of Compressive Strength of Concrete Incorporating Recycled Aggregate Using Ensemble Learning Algorithms: Multinational Dataset. Advances in Civil Engineering, 2023, 5076429." |

### ConcreteMix Model

| Source CSV Column             | Database Field   | Transformation / Notes                                                                                                                                                                                            |
| :---------------------------- | :--------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| mix_number                    | mix_code         | Generate using format "DS3-{mix\_number}"                                                                                                                                                                      |
| eff_water (kg/m3), cement (kg/m3) | w_c_ratio        | Calculated: `eff_water / cement`. Handle division by zero if cement is 0.                                                                                                                                         |
| eff_water (kg/m3), cement (kg/m3), fly ash (kg/m3), silica fume (kg/m3), BFS (kg/m3) | w_b_ratio    | Calculated: `eff_water / (cement + fly_ash + silica_fume + BFS)`. Handle division by zero. SCMs are cementitious. |
| (Not in CSV)                  | slump_mm         | Null. (To be added later from source papers if possible)                                                                                                                                                        |
| (Not in CSV)                  | air_content_pct  | Null. (To be added later)                                                                                                                                                                                       |
| (Not in CSV)                  | target_strength_mpa | Null. (To be added later)                                                                                                                                                                                       |
| (Not in CSV)                  | density_kg_m3    | Null. (To be added later)                                                                                                                                                                                       |
| country                       | region_country   | Direct mapping.                                                                                                                                                                                                 |
| mix_mark(reference...), ref., year | notes        | Concatenate: "Original Mix Mark: {mix\_mark}; Original Source Year: {year}; Original Source Ref: {ref.}"                                                                                                         |

### Material Components

#### Cement

| Source CSV Column | Model        | Database Field   | Detail Model   | Detail Fields              | Notes                                              |
| :---------------- | :----------- | :--------------- | :------------- | :------------------------- | :------------------------------------------------- |
| cement (kg/m3)    | MixComponent | dosage_kg_m3     |                |                            |                                                    |
| *(Implied)*       | Material     | material_class   |                | `class_code`: "CEMENT"     |                                                    |
| *(Implied)*       | Material     | specific_name    |                | "Portland Cement"          |                                                    |
| *(Implied)*       | Material     | subtype_code     |                | "CEM I"                    | Assumed default, can be refined.                   |
| *(Implied)*       | Material     | (Other fields)   | CementDetail   | `strength_class`: Null     | To be filled later from source papers if possible. |
|                   |              | `is_cementitious`|                | True                       |                                                    |

#### Water

| Source CSV Column   | Model        | Database Field   | Notes                                                                                    |
| :------------------ | :----------- | :--------------- | :--------------------------------------------------------------------------------------- |
| eff_water (kg/m3)   | MixComponent | dosage_kg_m3     |                                                                                          |
| *(Implied)*         | Material     | material_class   | `class_code`: "WATER"                                                                    |
| *(Implied)*         | Material     | specific_name    | "Effective Water" (Using "Mixing Water" for consistency with DS1 is also acceptable) |
|                     |              | `is_cementitious`| False                                                                                    |

#### Natural Coarse Aggregate (NCA)

| Source CSV Column | Model        | Database Field   | Detail Model      | Detail Fields       | Notes                                       |
| :---------------- | :----------- | :--------------- | :---------------- | :------------------ | :------------------------------------------ |
| NCA (kg/m3)       | MixComponent | dosage_kg_m3     |                   |                     | Only if dosage > 0.                         |
| *(Implied)*       | Material     | material_class   |                   | `class_code`: "AGGR_C"|                                             |
| *(Implied)*       | Material     | specific_name    |                   | "Natural Coarse Aggregate" |                                             |
| *(Implied)*       | Material     | subtype_code     |                   | "NCA"               |                                             |
| *(Implied)*       | Material     | (Other fields)   | AggregateDetail   | (All fields Null)   | Details not in CSV, to be added later.      |
|                   |              | `is_cementitious`|                   | False               |                                             |

#### Recycled Coarse Aggregate (RCA)

| Source CSV Column | Model        | Database Field   | Detail Model      | Detail Fields       | Notes                                       |
| :---------------- | :----------- | :--------------- | :---------------- | :------------------ | :------------------------------------------ |
| RCA (kg/m3)       | MixComponent | dosage_kg_m3     |                   |                     | Only if dosage > 0.                         |
| *(Implied)*       | Material     | material_class   |                   | `class_code`: "AGGR_C"|                                             |
| *(Implied)*       | Material     | specific_name    |                   | "Recycled Coarse Aggregate"|                                             |
| *(Implied)*       | Material     | subtype_code     |                   | "RCA"               |                                             |
| *(Implied)*       | Material     | (Other fields)   | AggregateDetail   | (All fields Null)   | Details not in CSV, to be added later.      |
|                   |              | `is_cementitious`|                   | False               |                                             |

#### Natural Fine Aggregate (NFA)

| Source CSV Column | Model        | Database Field   | Detail Model      | Detail Fields       | Notes                                       |
| :---------------- | :----------- | :--------------- | :---------------- | :------------------ | :------------------------------------------ |
| NFA (kg/m3)       | MixComponent | dosage_kg_m3     |                   |                     | Only if dosage > 0.                         |
| *(Implied)*       | Material     | material_class   |                   | `class_code`: "AGGR_F"|                                             |
| *(Implied)*       | Material     | specific_name    |                   | "Natural Fine Aggregate" |                                             |
| *(Implied)*       | Material     | subtype_code     |                   | "NFA"               |                                             |
| *(Implied)*       | Material     | (Other fields)   | AggregateDetail   | (All fields Null)   | Details not in CSV, to be added later.      |
|                   |              | `is_cementitious`|                   | False               |                                             |

#### Fly Ash (SCM)

| Source CSV Column | Model        | Database Field   | Detail Model   | Detail Fields              | Notes                                              |
| :---------------- | :----------- | :--------------- | :------------- | :------------------------- | :------------------------------------------------- |
| fly ash (kg/m3)   | MixComponent | dosage_kg_m3     |                |                            | Only if dosage > 0.                                |
| *(Implied)*       | Material     | material_class   |                | `class_code`: "SCM"        |                                                    |
| *(Implied)*       | Material     | specific_name    |                | "Fly Ash"                  |                                                    |
| *(Implied)*       | Material     | subtype_code     |                | "FA"                       | Generic.                                           |
| *(Implied)*       | Material     | (Other fields)   | ScmDetail      | `scm_type_code`: Null      | Specific type (e.g., F, C) to be added later.      |
|                   |              | `is_cementitious`|                | True                       |                                                    |

#### Silica Fume (SCM)

| Source CSV Column   | Model        | Database Field   | Detail Model   | Detail Fields              | Notes                                       |
| :------------------ | :----------- | :--------------- | :------------- | :------------------------- | :------------------------------------------ |
| silica fume (kg/m3) | MixComponent | dosage_kg_m3     |                |                            | Only if dosage > 0.                         |
| *(Implied)*         | Material     | material_class   |                | `class_code`: "SCM"        |                                             |
| *(Implied)*         | Material     | specific_name    |                | "Silica Fume"              |                                             |
| *(Implied)*         | Material     | subtype_code     |                | "SF"                       |                                             |
| *(Implied)*         | Material     | (Other fields)   | ScmDetail      | `scm_type_code`: "SF"      |                                             |
|                     |              | `is_cementitious`|                | True                       |                                             |

#### Blast Furnace Slag (BFS/GGBS - SCM)

| Source CSV Column | Model        | Database Field   | Detail Model   | Detail Fields              | Notes                                       |
| :---------------- | :----------- | :--------------- | :------------- | :------------------------- | :------------------------------------------ |
| BFS (kg/m3)       | MixComponent | dosage_kg_m3     |                |                            | Only if dosage > 0.                         |
| *(Implied)*       | Material     | material_class   |                | `class_code`: "SCM"        |                                             |
| *(Implied)*       | Material     | specific_name    |                | "Ground Granulated Blast Furnace Slag" | Preferred name.                             |
| *(Implied)*       | Material     | subtype_code     |                | "BFS"                      | Or "GGBS" if preferred for consistency.     |
| *(Implied)*       | Material     | (Other fields)   | ScmDetail      | `scm_type_code`: "S"       | General code for slag (or "BFS"/"GGBS").    |
|                   |              | `is_cementitious`|                | True                       |                                             |

#### Superplasticizer (SP - Admixture)

| Source CSV Column | Model        | Database Field   | Detail Model      | Detail Fields          | Notes                                       |
| :---------------- | :----------- | :--------------- | :---------------- | :--------------------- | :------------------------------------------ |
| SP (kg/m3)        | MixComponent | dosage_kg_m3     |                   |                        | Only if dosage > 0.                         |
| *(Implied)*       | Material     | material_class   |                   | `class_code`: "ADM"    |                                             |
| *(Implied)*       | Material     | specific_name    |                   | "Superplasticizer"     |                                             |
| *(Implied)*       | Material     | subtype_code     |                   | "SP"                   | Generic, specific type not available.       |
| *(Implied)*       | Material     | (Other fields)   | AdmixtureDetail   | (All fields Null)      | Details not in CSV, to be added later.      |

### Performance Results

For each row in the CSV, one `PerformanceResult` record will be created.

| Source CSV Column | Database Field   | Value/Link                                                              | Notes                                                                                                                            |
| :---------------- | :--------------- | :---------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------- |
| CS fck (mpa)      | value_num        | Direct mapping.                                                         | Compressive strength.                                                                                                            |
| Testing Age (day) | age_days         | Direct mapping.                                                         | Age at testing.                                                                                                                  |
| *(Implied)*       | property         | Link to `PropertyDictionary` PK: `"compressive_strength"`               | `display_name`: "Compressive Strength", `property_group`: `MECHANICAL`.                                                        |
| *(Implied)*       | unit             | Link to `UnitLookup` symbol: "MPa"                                      |                                                                                                                                  |
| *(Implied)*       | test_method      | Link to `TestMethod` description: "Compressive Strength Test (Normalized Cylindrical Equivalent)" | Reflects normalization.                                                                                          |
| *(Implied)*       | category         | `PerformanceResult.HARDENED`                                            |                                                                                                                                  |
| *(Implied)*       | specimen         | Link to a standard `Specimen` record for this dataset/mix.                | Shape: "Cylinder", Diameter: 100mm, Length: 200mm (due to normalization mentioned in paper). No per-row specimen data in CSV. |

## Validation Checks (Examples for DS3)

*   Verify calculated `w_c_ratio` and `w_b_ratio` are correctly stored.
*   Ensure `ConcreteMix.region_country` is populated from the `country` CSV column.
*   Check that `ConcreteMix.notes` correctly includes the original source `ref.` and `year`.
*   Confirm `PerformanceResult.age_days` matches `Testing Age (day)` from CSV.
*   Confirm that a standard Specimen (Cylinder 100x200mm) is linked to performance results.
*   Data range checks for key inputs (e.g., `cement (kg/m3)`: approx 113-680 from CSV, `eff_water (kg/m3)`: approx 110-277). Paper Table 3 gives ranges for *ML input features (ratios/%)* not raw quantities. `CS fck (mpa)`: CSV range ~3.6 to ~110 MPa. `Testing Age (day)`: CSV range 1 to 90 days.

---