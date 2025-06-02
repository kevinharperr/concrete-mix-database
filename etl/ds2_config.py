# ds2_config.py
from decimal import Decimal

CONFIG = {
    "dataset_meta": {
        "name": "Dataset 2",
        "description": "Database of hardened concrete properties made with recycled concrete aggregates (RCA) from 115 peer-reviewed journal articles. Focuses on coarse RCA replacement. Compiled by Jayasuriya et al. (2021).",
        "source_text": "Anuruddha Jayasuriya, Emily S. Shibata, Tola Chen, Matthew P. Adams (2021). Aggregated dataset.",
        "year_published": 2021,
        "csv_file_path": "etl/ds2.csv",
        "bibliographic_reference": {
            "author": "Jayasuriya, A., Shibata, E.S., Chen, T., Adams, M.P.",
            "title": "Development and statistical database analysis of hardened concrete properties made with recycled concrete aggregates",
            "publication": "Resources, Conservation & Recycling",
            "year": 2021,
            "doi": "10.1016/j.resconrec.2020.105121",
            "citation_text": "Jayasuriya, A., Shibata, E. S., Chen, T., & Adams, M. P. (2021). Development and statistical database analysis of hardened concrete properties made with recycled concrete aggregates. Resources, Conservation & Recycling, 164, 105121."
        }
    },

    "column_to_concretemix_fields": {
        # CSV_Column_Name: ConcreteMix_Model_Field_Name (or dict for transformation)
        "Mix Number": {"field": "mix_code", "prefix": "DS2-"},
        "Eff. W/C ratio": "w_c_ratio",
        # For w_b_ratio, it will be same as w_c_ratio as no SCMs in DS2
        "Slump mm": "slump_mm",
        "notes_from_columns": [  # To build the ConcreteMix.notes field
            {"csv_column": "Year of Publication", "prefix": "Original Source Year: "},
            {"csv_column": "Source", "prefix": "Original Source Ref: "},
        ]
    },

    "materials": [
        {
            "csv_column_for_quantity": "Cement Content kg/m^3",
            "material_class_code": "CEMENT",
            "fixed_properties": {"specific_name": "Portland Cement", "subtype_code": "CEM I"},
            "detail_model_data": {"strength_class": None},
            "is_cementitious": True
        },
        {  # Water - will be created as a Material, but MixComponent dosage calculated later
            "material_class_code": "WATER",
            "fixed_properties": {"specific_name": "Mixing Water"},
            "is_cementitious": False,
            "create_mix_component": False  # Special flag for importer engine
        },
        {
            "csv_column_for_quantity": "RCA Content",
            "material_class_code": "AGGR_C",
            "fixed_properties": {"specific_name": "Recycled Coarse Aggregate", "subtype_code": "RCA"},
            "detail_model_data": {
                "d_upper_mm_csv_col": "RCA Agg. Size",  # Assumed mm
                "d_lower_mm": {"fixed_value": Decimal("0.4")},  # Per our decision
                "bulk_density_kg_m3_csv_col": "RCA Bulk Density kg/m^3",
                "water_absorption_pct_csv_col": "RCA Water Absorption [%]"
            },
            "is_cementitious": False
        },
        {
            "csv_column_for_quantity": "NCA Content",
            "material_class_code": "AGGR_C",
            "fixed_properties": {"specific_name": "Natural Coarse Aggregate", "subtype_code": "NCA"},
            "detail_model_data": {
                "d_upper_mm_csv_col": "NCA Size (mm)",
                "d_lower_mm": {"fixed_value": Decimal("0.4")},  # Per our decision
                "bulk_density_kg_m3_csv_col": "NCA Bulk Density kg/m^3",
                "water_absorption_pct_csv_col": "NCA Water Absorption [%]"
            },
            "is_cementitious": False
        },
        {
            "csv_column_for_quantity": "NFA Content",
            "material_class_code": "AGGR_F",
            "fixed_properties": {"specific_name": "Natural Fine Aggregate", "subtype_code": "NFA"},
            "detail_model_data": {  # All NFA details are not in CSV, leave them to be null or default in model
                "fineness_modulus": None  # Explicitly state if not providing
            },
            "is_cementitious": False
        }
        # No SCMs or Admixtures for DS2
    ],

    "performance_results": [
        {
            "property_pk": "compressive_strength",  # The PK of PropertyDictionary ('property_name')
            "csv_column_for_value": "Compressive Strength",
            "fixed_age_days": 28,  # Critical assumption for DS2
            "unit_symbol": "MPa",
            "category": "hardened",  # Corresponds to PerformanceResult.HARDENED
            "test_method_description": "Compressive Strength Test (Cylinder/Cube)",  # Generic description
            "specimen_csv_column": "Specimen Type [in.]"
        }
    ],

    "validation_rules": {
        "Eff. W/C ratio": {"min": 0.15, "max": 1.0},  # Adjust based on actual DS2 data spread
        "Compressive Strength": {"min": 10, "max": 120},
        "Cement Content kg/m^3": {"min": 100, "max": 650},  # Increased to accommodate DS2 data
        "RCA Content": {"min": 0, "max": 2000},
        "NCA Content": {"min": 0, "max": 2000},
        "NFA Content": {"min": 0, "max": 1500},  # Increased from 1000 to accommodate research data
        "Slump mm": {"min": 0, "max": 300}
    }
} 