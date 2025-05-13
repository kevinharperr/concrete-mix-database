# DS6: Comprehensive Dataset for Recycled Aggregate Concrete with SCMs

## Overview

DS6 is a comprehensive database extracted from a wide-ranging literature review on recycled aggregate concrete (RAC) and natural aggregate concrete (NAC) mix designs. The database contains detailed mix proportions, cementitious material compositions, aggregate properties, and mechanical performance data compiled by Xie et al. (2020) from their paper "A unified model for predicting the compressive strength of recycled aggregate concrete containing supplementary cementitious materials" published in the Journal of Cleaner Production.

The database consists of two complementary datasets:

1. **Main dataset (ds6.csv)**: Contains 654 unique concrete mix designs extracted from 49 individual studies, with mix proportions and test results
2. **Material properties dataset (ds6_material_properties_of_mixes.csv)**: Contains 134 records with detailed chemical and physical properties of the binder materials

The database covers a wide range of cementitious materials used in combination with Ordinary Portland Cement (OPC), including fly ash, ground granulated blast furnace slag (GGBFS), silica fume, metakaolin, palm oil fuel ash, bagasse ash, and rice husk ash.

## Key Features and Research Value

This dataset is particularly valuable for:

1. Developing and validating predictive models for concrete containing recycled aggregates and supplementary cementitious materials
2. Studying the relationships between chemical composition of binders and concrete performance
3. Analyzing the effects of recycled aggregate properties on concrete strength
4. Investigating the combined effects of mix parameters (water-binder ratio, RCA replacement ratio, binder reactivity) on compressive strength

The database includes both cubic and cylindrical compressive strength test results at various ages (1, 3, 7, 14, 21, 28, 56, 90, and 180 days), offering comprehensive data for strength development modeling.

## Main Dataset Column Details

The main dataset (ds6.csv) includes:

### Mix Identification

- **reference_no**: Reference identifier for the original study
- **study_number**: Numerical identifier for each study (corresponds to reference_no)
- **mix_number**: Unique identifier for each concrete mix (1-654)
- **author**: Author(s) of the original study
- **year**: Publication year
- **specimen_code**: Original specimen identification code

### Binder Components (kg/m³)

- **Cement (kg/m3)**: Ordinary Portland Cement content
- **fly_ash_kg_m3**: Fly ash content
- **ggbfs_kg_m3**: Ground granulated blast furnace slag content
- **silica_fume_kg_m3**: Silica fume content
- **kaolin_kgm3**: Metakaolin content
- **other_scm1_kg_m3**, **other_scm1_type**: Content and type of additional SCM (e.g., palm oil fuel ash, rice husk ash)
- **other_scm2_kg_m3**, **other_scm2_type**: Content and type of second additional SCM

### Aggregate Components

- **nca_kg_m3**: Natural coarse aggregate content (total)
- **rca_kg_m3**: Recycled coarse aggregate content (total)
- **nfa_kg_m3**: Natural fine aggregate content (total)
- **rca_volume_ratio_%**: Volumetric replacement ratio of RCA

### Water and Admixtures

- **water_kg_m3**: Total water content
- **added_water_kg_m3**: Additional water for RCA absorption compensation
- **superplasticizer_kg_m3**: Superplasticizer content
- **water_eff_kg_m3**: Effective water content
- **wbr_total**: Total water-binder ratio

### Mix Ratios

- **b_coarseagg_ratio**: Binder to coarse aggregate ratio
- **binder_fineagg_ratio**: Binder to fine aggregate ratio

### Aggregate Properties

For each aggregate type (NCA1, NCA2, RCA1, RCA2, NFA1, NFA2):

- **sg**: Specific gravity
- **nms_mm**: Nominal maximum size (mm)
- **material_type**: Material type
- **crushing_index_pct**: Crushing index (%)
- **la_abrasion_pct**: Los Angeles abrasion value (%)
- **fineness_modulus**: Fineness modulus
- **w_abs_pct**: Water absorption (%)

### Reactivity Indices

- **reactivity_modulus**: Ratio of (CaO+MgO+Al₂O₃)/SiO₂
- **silica_modulus**: Ratio of SiO₂/(Al₂O₃+Fe₂O₃)
- **alumina_modulus**: Ratio of Al₂O₃/Fe₂O₃

### Specimen Details

- **cube_dimension**: Cube specimen dimension (mm)
- **cyl_dia_mm**: Cylinder specimen diameter (mm)
- **cyl_height_mm**: Cylinder specimen height (mm)

### Strength Test Results

- **fc_cube_[age]_mpa**: Cube compressive strength at different ages (MPa)
- **fc_cyl_[age]_mpa**: Cylinder compressive strength at different ages (MPa)

Where [age] is 1d, 3d, 7d, 14d, 21d, 28d, 56d, 90d, or 180d.

## Material Properties Dataset Column Details

The material properties dataset (ds6_material_properties_of_mixes.csv) includes:

### Material Identification

- **reference_no**: Reference identifier
- **study_no**: Study number
- **Authors**: Author names
- **year of study**: Publication year
- **Type of binder**: Description of binder type

### Chemical Composition (% by weight)

- **SiO2, Al2O3, Fe2O3, CaO, MgO, Na2O, K2O, SO3, TiO2, P2O5, SrO, Mn2O3, LOI**: Oxide content percentages

### Physical Properties

- **blaine_fineness_ssa_m2_kg**: Specific surface area (m²/kg)
- **d50-median_particle_size_mm**: Median particle size (mm)
- **specific_gravity**: Specific gravity of the binder

### Reactivity Indices

- **Reactivity_modulus**: (CaO+MgO+Al₂O₃)/SiO₂
- **silica_modulus**: SiO₂/(Al₂O₃+Fe₂O₃)
- **alumina_modulus**: Al₂O₃/Fe₂O₃

## Data Selection Criteria

The dataset was constructed with specific criteria to ensure quality and consistency:

1. Complete chemical composition for each binder
2. Detailed concrete mix proportions
3. Binder fineness not exceeding 20,000 m²/kg (mixes with superfine materials excluded)
4. Only coarse recycled aggregates (nominal maximum size >4.75 mm)
5. SCMs used solely as binder materials (no surface treatments of RCA)
6. Standard fog room curing conditions
7. Standard specimen dimensions for compression testing

## Notes on Data Interpretation

- The water-binder ratio used is the "effective water-to-binder ratio," accounting for water from superplasticizers (typically 65% of superplasticizer weight) and excluding water absorbed by aggregates or added to compensate for RCA absorption
- The reference_no column uses the format "[number]" while study_number uses plain integers
- The mix_number is a sequential counter for all mixes across all studies
- Author and year columns can be combined for citation references

## Relevant Research Findings

Based on the unified model developed in the source paper, the key factors affecting the compressive strength of recycled aggregate concrete with SCMs are:

1. Water-to-binder ratio
2. RCA replacement percentage
3. Reactivity of the binder (quantified by reactivity moduli)

The model demonstrated that reactivity indices calculated from chemical composition (particularly CaO, MgO, SiO2, Al2O3, and Fe2O3 content) play a crucial role in predicting the performance of concrete containing SCMs and RCAs.

---

### FULL LIST OF COLUMNS IN DS6.CSV

Below is the complete header row of **ds6.csv** (92 columns, in the exact order they appear):

- reference_no
    
- study_number
    
- mix_number
    
- author
    
- year
    
- specimen_code
    
- Cement (kg/m3)
    
- fly_ash_kg_m3
    
- ggbfs_kg_m3
    
- silica_fume_kg_m3
    
- kaolin_kgm3
    
- other_scm1_kg_m3
    
- other_scm1_type
    
- other_scm2_kg_m3
    
- other_scm2_type
    
- nca_kg_m3
    
- rca_kg_m3
    
- nfa_kg_m3
    
- rca_volume_ratio_%
    
- water_kg_m3
    
- added_water_kg_m3
    
- superplasticizer_kg_m3
    
- water_eff_kg_m3
    
- wbr_total
    
- b_coarseagg_ratio
    
- binder_fineagg_ratio
    
- nca1_sg
    
- nca1_nms_mm
    
- nca1_material_type
    
- nca1_crushing_index_pct
    
- nca1_la_abrasion_pct
    
- nca1_fineness_modulus
    
- nca1_w_abs_pct
    
- nca2_sg
    
- nca2_nms_mm
    
- nca2_material_type
    
- nca2_crushing_index_pct
    
- nca2_la_abrasion_pct
    
- nca2_fineness_modulus
    
- nca2_w_abs_pct
    
- rca1_sg
    
- rca1_nms_mm
    
- rca1_material_type
    
- rca1_crushing_index_pct
    
- rca1_la_abrasion_pct
    
- rca1_fineness_modulus
    
- rca1_w_abs_pct
    
- rca2_sg
    
- rca2_nms_mm
    
- rca2_material_type
    
- rca2_crushing_index_pct
    
- rca2_la_abrasion_pct
    
- rca2_fineness_modulus
    
- rca2_w_abs_pct
    
- nfa1_sg
    
- nfa1_nms_mm
    
- nfa1_material_type
    
- nfa1_crushing_index_pct
    
- nfa1_la_abrasion_pct
    
- nfa1_fineness_modulus
    
- nfa1_w_abs_pct
    
- nfa2_sg
    
- nfa2_nms_mm
    
- nfa2_material_type
    
- nfa2_crushing_index_pct
    
- nfa2_la_abrasion_pct
    
- nfa2_fineness_modulus
    
- nfa2_w_abs_pct
    
- reactivity_modulus
    
- silica_modulus
    
- alumina_modulus
    
- cube_dimension
    
- fc_cube_1d_mpa
    
- fc_cube_3d_mpa
    
- fc_cube_7d_mpa
    
- fc_cube_14d_mpa
    
- fc_cube_21d_mpa
    
- fc_cube_28d_mpa
    
- fc_cube_56d_mpa
    
- fc_cube_90d_mpa
    
- fc_cube_180d_mpa
    
- cyl_dia_mm
    
- cyl_height_mm
    
- fc_cyl_1d_mpa
    
- fc_cyl_3d_mpa
    
- fc_cyl_7d_mpa
    
- fc_cyl_14d_mpa
    
- fc_cyl_21d_mpa
    
- fc_cyl_28d_mpa
    
- fc_cyl_56d_mpa
    
- fc_cyl_90d_mpa
    
- fc_cyl_180d_mpa