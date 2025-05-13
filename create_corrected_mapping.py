import csv
import json

def create_corrected_mapping():
    """Create a properly formatted mapping file with the correct column names"""
    # Define mappings with proper JSON and correct column names from DS6 dataset
    mappings = [
        # Basic mix info
        {"source_column": "study_number", "target_table": "concrete_mix", "target_column": "mix_code", 
         "extra_kwargs": json.dumps({"prefix": "DS6-"})},
        {"source_column": "mix_number", "target_table": "concrete_mix", "target_column": "notes", 
         "extra_kwargs": json.dumps({"prefix": "Mix number: "})},
        
        # Materials with reference keys
        {"source_column": "Cement (kg/m3)", "target_table": "mix_component", "target_column": "dosage_kg_m3", 
         "extra_kwargs": json.dumps({"class_code":"CEMENT", "subtype_code":"CEM I", 
                                  "specific_name":"Ordinary Portland Cement", "is_cementitious":True, 
                                  "reference_key":"CEMENT"})},
        {"source_column": "fly_ash_kg_m3", "target_table": "mix_component", "target_column": "dosage_kg_m3", 
         "extra_kwargs": json.dumps({"class_code":"SCM", "subtype_code":"FA", 
                                  "specific_name":"Fly Ash", "is_cementitious":True, 
                                  "reference_key":"FA"})},
        {"source_column": "ggbfs_kg_m3", "target_table": "mix_component", "target_column": "dosage_kg_m3", 
         "extra_kwargs": json.dumps({"class_code":"SCM", "subtype_code":"GGBFS", 
                                  "specific_name":"Ground Granulated Blast Furnace Slag", "is_cementitious":True, 
                                  "reference_key":"GGBFS"})},
        {"source_column": "nca_kg_m3", "target_table": "mix_component", "target_column": "dosage_kg_m3", 
         "extra_kwargs": json.dumps({"class_code":"AGGR_C", "subtype_code":"NCA", 
                                  "specific_name":"Natural Coarse Aggregate", 
                                  "reference_key":"NCA"})},
        {"source_column": "rca_kg_m3", "target_table": "mix_component", "target_column": "dosage_kg_m3", 
         "extra_kwargs": json.dumps({"class_code":"AGGR_C", "subtype_code":"RCA", 
                                  "specific_name":"Recycled Coarse Aggregate", 
                                  "reference_key":"RCA"})},
        {"source_column": "water_kg_m3", "target_table": "mix_component", "target_column": "dosage_kg_m3", 
         "extra_kwargs": json.dumps({"class_code":"WATER", "subtype_code":"WATER", 
                                  "specific_name":"Water", 
                                  "reference_key":"WATER"})},
        {"source_column": "w_c_ratio", "target_table": "concrete_mix", "target_column": "w_c_ratio", 
         "extra_kwargs": json.dumps({})},
        {"source_column": "wbr_total", "target_table": "concrete_mix", "target_column": "w_c_ratio", 
         "extra_kwargs": json.dumps({})},
        
        # Aggregate details
        {"source_column": "nca1_sg", "target_table": "aggregate_detail", "target_column": "bulk_density_kg_m3", 
         "extra_kwargs": json.dumps({"material_ref_key": "NCA"})},
        {"source_column": "nca1_w_abs_pct", "target_table": "aggregate_detail", "target_column": "water_absorption_pct", 
         "extra_kwargs": json.dumps({"material_ref_key": "NCA"})},
        {"source_column": "nca1_fineness_modulus", "target_table": "aggregate_detail", "target_column": "fineness_modulus", 
         "extra_kwargs": json.dumps({"material_ref_key": "NCA"})},
        {"source_column": "nca1_nms_mm", "target_table": "aggregate_detail", "target_column": "d_upper_mm", 
         "extra_kwargs": json.dumps({"material_ref_key": "NCA"})},
        {"source_column": "rca1_sg", "target_table": "aggregate_detail", "target_column": "bulk_density_kg_m3", 
         "extra_kwargs": json.dumps({"material_ref_key": "RCA"})},
        {"source_column": "rca1_w_abs_pct", "target_table": "aggregate_detail", "target_column": "water_absorption_pct", 
         "extra_kwargs": json.dumps({"material_ref_key": "RCA"})},
        {"source_column": "rca1_fineness_modulus", "target_table": "aggregate_detail", "target_column": "fineness_modulus", 
         "extra_kwargs": json.dumps({"material_ref_key": "RCA"})},
        {"source_column": "rca1_nms_mm", "target_table": "aggregate_detail", "target_column": "d_upper_mm", 
         "extra_kwargs": json.dumps({"material_ref_key": "RCA"})},
        
        # Material properties
        {"source_column": "nca1_crushing_index_pct", "target_table": "material_property", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"property_name": "crushing_index_pct", "property_group": "physical", 
                                  "material_ref_key": "NCA"})},
        {"source_column": "nca1_la_abrasion_pct", "target_table": "material_property", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"property_name": "la_abrasion_pct", "property_group": "physical", 
                                  "material_ref_key": "NCA"})},
        {"source_column": "rca1_crushing_index_pct", "target_table": "material_property", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"property_name": "crushing_index_pct", "property_group": "physical", 
                                  "material_ref_key": "RCA"})},
        {"source_column": "rca1_la_abrasion_pct", "target_table": "material_property", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"property_name": "la_abrasion_pct", "property_group": "physical", 
                                  "material_ref_key": "RCA"})},
        
        # Performance results - Cube specimens (using correct column names)
        {"source_column": "fc_cube_1d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 1, "specimen_type": "cube"})},
        {"source_column": "fc_cube_3d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 3, "specimen_type": "cube"})},
        {"source_column": "fc_cube_7d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 7, "specimen_type": "cube"})},
        {"source_column": "fc_cube_14d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 14, "specimen_type": "cube"})},
        {"source_column": "fc_cube_28d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 28, "specimen_type": "cube"})},
        {"source_column": "fc_cube_56d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 56, "specimen_type": "cube"})},
        {"source_column": "fc_cube_90d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 90, "specimen_type": "cube"})},
        {"source_column": "fc_cube_180d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 180, "specimen_type": "cube"})},
        
        # Performance results - Cylinder specimens (using correct column names)
        {"source_column": "fc_cyl_1d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 1, "specimen_type": "cylinder"})},
        {"source_column": "fc_cyl_3d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 3, "specimen_type": "cylinder"})},
        {"source_column": "fc_cyl_7d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 7, "specimen_type": "cylinder"})},
        {"source_column": "fc_cyl_14d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 14, "specimen_type": "cylinder"})},
        {"source_column": "fc_cyl_28d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 28, "specimen_type": "cylinder"})},
        {"source_column": "fc_cyl_56d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 56, "specimen_type": "cylinder"})},
        {"source_column": "fc_cyl_90d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 90, "specimen_type": "cylinder"})},
        {"source_column": "fc_cyl_180d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": json.dumps({"category": "hardened", "test_name": "compressive_strength", 
                                  "age_days": 180, "specimen_type": "cylinder"})},
        
        # Specimen dimensions
        {"source_column": "cyl_dia_mm", "target_table": "concrete_mix", "target_column": "notes", 
         "extra_kwargs": json.dumps({"prefix": "Cylinder diameter (mm): "})},
        {"source_column": "cyl_height_mm", "target_table": "concrete_mix", "target_column": "notes", 
         "extra_kwargs": json.dumps({"prefix": "Cylinder height (mm): "})},
    ]
    
    # Write to CSV
    with open('etl/ds6_corrected_mapping.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['source_column', 'target_table', 'target_column', 'extra_kwargs'])
        writer.writeheader()
        writer.writerows(mappings)
    
    print("Created corrected mapping file at etl/ds6_corrected_mapping.csv")
    
    # Verify JSON formatting
    print("\nVerifying JSON formatting...")
    with open('etl/ds6_corrected_mapping.csv', 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            try:
                parsed = json.loads(row['extra_kwargs'])
                print(f"Row {i}: Valid JSON")
            except json.JSONDecodeError as e:
                print(f"Row {i}: Invalid JSON - {e}")

if __name__ == "__main__":
    create_corrected_mapping()
