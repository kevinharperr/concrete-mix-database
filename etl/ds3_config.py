from decimal import Decimal

CONFIG = {
    "dataset_meta": {
        "name": "Dataset 3",
        "description": "Multinational dataset of concrete with recycled aggregates (primarily coarse RCA) and various SCMs, used for compressive strength prediction. Compiled by Phoeuk and Kwon (2023) from 81 studies. Compressive strength values normalized to 100x200mm cylinder equivalent. Testing ages vary as per source data.",
        "source_text": "Menghay Phoeuk, Minho Kwon (2023). Aggregated dataset from 81 prior studies.",
        "year_published": 2023,
        "csv_file_path": "etl/ds3.csv",
        "bibliographic_reference": {
            "author": "Phoeuk, M., Kwon, M.",
            "title": "Accuracy Prediction of Compressive Strength of Concrete Incorporating Recycled Coarse Aggregate Using Machine Learning",
            "publication": "Materials",
            "year": 2023,
            "doi": "10.3390/ma16124459",
            "citation_text": "Phoeuk, M.; Kwon, M. Accuracy Prediction of Compressive Strength of Concrete Incorporating Recycled Coarse Aggregate Using Machine Learning. Materials 2023, 16, 4459."
        }
    },
    
    "column_to_concretemix_fields": {
        # CSV_Column_Name: ConcreteMix_Model_Field_Name (or dict for transformation)
        "mix_number": {"field": "mix_code", "prefix": "DS3-"},
        "country": "region_country",
        # W/C and W/B ratios will be calculated from constituent columns
        # w_c_ratio = eff_water (kg/m3) / cement (kg/m3)
        # w_b_ratio = eff_water (kg/m3) / (cement (kg/m3) + fly ash (kg/m3) + silica fume (kg/m3) + BFS (kg/m3))
        "notes_from_columns": [  # To build the ConcreteMix.notes field
            {"csv_column": "mix_number", "prefix": "Mix Number: "},
            {"csv_column": "ref.", "prefix": "Original Source: "},
            {"csv_column": "year", "prefix": "Year: "},
        ]
    },
    
    "materials": [
        {
            "csv_column_for_quantity": "cement (kg/m3)",
            "material_class_code": "CEMENT",
            "fixed_properties": {"specific_name": "Portland Cement", "subtype_code": "CEM I"},
            "detail_model_data": {"strength_class": None},
            "is_cementitious": True
        },
        {  # Water - FIXED: Now creates components for ratio calculation
            "csv_column_for_quantity": "eff_water (kg/m3)  ",  # Fixed: exact column name with trailing spaces
            "material_class_code": "WATER",
            "fixed_properties": {"specific_name": "Effective Water"},
            "is_cementitious": False
            # Removed create_mix_component: False to allow water components
        },
        {
            "csv_column_for_quantity": "NCA (kg/m3)",
            "material_class_code": "AGGR_C",
            "fixed_properties": {"specific_name": "Natural Coarse Aggregate", "subtype_code": "NCA"},
            "detail_model_data": {
                # All aggregate details are not in DS3 CSV, will be null
            },
            "is_cementitious": False
        },
        {
            "csv_column_for_quantity": "RCA (kg/m3)",
            "material_class_code": "AGGR_C",
            "fixed_properties": {"specific_name": "Recycled Coarse Aggregate", "subtype_code": "RCA"},
            "detail_model_data": {
                # All aggregate details are not in DS3 CSV, will be null
            },
            "is_cementitious": False
        },
        {
            "csv_column_for_quantity": "NFA,sand (kg/m3)",
            "material_class_code": "AGGR_F",
            "fixed_properties": {"specific_name": "Natural Fine Aggregate", "subtype_code": "NFA"},
            "detail_model_data": {
                # All aggregate details are not in DS3 CSV, will be null
            },
            "is_cementitious": False
        },
        {
            "csv_column_for_quantity": "fly ash (kg/m3)",
            "material_class_code": "SCM",
            "fixed_properties": {"specific_name": "Fly Ash", "subtype_code": "FA"},
            "detail_model_data": {"scm_type_code": "FA"},
            "is_cementitious": True
        },
        {
            "csv_column_for_quantity": "silica fume (kg/m3)",
            "material_class_code": "SCM",
            "fixed_properties": {"specific_name": "Silica Fume", "subtype_code": "SF"},
            "detail_model_data": {"scm_type_code": "SF"},
            "is_cementitious": True
        },
        {
            "csv_column_for_quantity": "BFS (kg/m3) ",  # Note: this also has trailing space
            "material_class_code": "SCM",
            "fixed_properties": {"specific_name": "Blast Furnace Slag", "subtype_code": "BFS"},
            "detail_model_data": {"scm_type_code": "BFS"},
            "is_cementitious": True
        },
        {
            "csv_column_for_quantity": "SP (kg/m3)",
            "material_class_code": "ADM",
            "fixed_properties": {"specific_name": "Superplasticizer", "subtype_code": "SP"},
            "detail_model_data": {
                # All admixture details are not in DS3 CSV, will be null
            },
            "is_cementitious": False
        }
    ],
    
    "performance_results": [
        {
            "property_pk": "compressive_strength",  # The PK of PropertyDictionary ('property_name')
            "csv_column_for_value": "CS fck (mpa)",
            "csv_column_for_age": "Testing Age (day)",  # Unlike DS2, DS3 has variable testing ages
            "unit_symbol": "MPa",
            "category": "hardened",  # Corresponds to PerformanceResult.HARDENED
            "test_method_description": "Compressive Strength (Normalized 100x200mm Cyl)",  # Reflects normalization
            "specimen_details": {
                # Since all CS values are normalized to 100x200mm cylinder equivalent
                "shape": "Cylinder",
                "nominal_diameter_mm": Decimal("100.0"),
                "nominal_length_mm": Decimal("200.0")
            }
        }
    ],
    
    "validation_rules": {
        "cement (kg/m3)": {"min": 113, "max": 680},  # Based on DS3_DEFINITION range checks
        "eff_water (kg/m3)  ": {"min": 110, "max": 277},  # Fixed: exact column name with trailing spaces
        "CS fck (mpa)": {"min": 3.6, "max": 110},
        "Testing Age (day)": {"min": 1, "max": 90},
        "NCA (kg/m3)": {"min": 0, "max": 2000},
        "RCA (kg/m3)": {"min": 0, "max": 2000},
        "NFA,sand (kg/m3)": {"min": 0, "max": 1500},
        "fly ash (kg/m3)": {"min": 0, "max": 400},
        "silica fume (kg/m3)": {"min": 0, "max": 150},  # Increased from 100 to 150 based on validation errors
        "BFS (kg/m3) ": {"min": 0, "max": 250},  # Fixed: exact column name with trailing space
        "SP (kg/m3)": {"min": 0, "max": 40}  # Increased from 20 to 40 based on validation errors
    }
} 