import csv
import json

def create_mapping_file():
    """Create a properly formatted reference key mapping file"""
    # Define the mapping data with proper JSON format
    mapping_data = [
        # Basic mix info
        {"source_column": "reference_no", "target_table": "bibliographic_reference", "target_column": "citation_text", "extra_kwargs": "{}"},
        {"source_column": "study_number", "target_table": "concrete_mix", "target_column": "mix_code", "extra_kwargs": "{\"prefix\": \"DS6-\"}"},
        {"source_column": "mix_number", "target_table": "concrete_mix", "target_column": "notes", "extra_kwargs": "{\"prefix\": \"Mix number: \"}"},
        {"source_column": "author", "target_table": "bibliographic_reference", "target_column": "author", "extra_kwargs": "{}"},
        {"source_column": "year", "target_table": "bibliographic_reference", "target_column": "year", "extra_kwargs": "{}"},
        {"source_column": "specimen_code", "target_table": "concrete_mix", "target_column": "notes", "extra_kwargs": "{\"prefix\": \"Specimen code: \"}"},
        
        # Materials with reference keys
        {"source_column": "Cement (kg/m3)", "target_table": "mix_component", "target_column": "dosage_kg_m3", 
         "extra_kwargs": "{\"class_code\":\"CEMENT\", \"subtype_code\":\"CEM I\", \"specific_name\":\"Ordinary Portland Cement\", \"is_cementitious\":true, \"reference_key\":\"CEMENT\"}"},
        {"source_column": "fly_ash_kg_m3", "target_table": "mix_component", "target_column": "dosage_kg_m3", 
         "extra_kwargs": "{\"class_code\":\"SCM\", \"subtype_code\":\"FA\", \"specific_name\":\"Fly Ash\", \"is_cementitious\":true, \"reference_key\":\"FA\"}"},
        {"source_column": "ggbfs_kg_m3", "target_table": "mix_component", "target_column": "dosage_kg_m3", 
         "extra_kwargs": "{\"class_code\":\"SCM\", \"subtype_code\":\"GGBFS\", \"specific_name\":\"Ground Granulated Blast Furnace Slag\", \"is_cementitious\":true, \"reference_key\":\"GGBFS\"}"},
        {"source_column": "nca_kg_m3", "target_table": "mix_component", "target_column": "dosage_kg_m3", 
         "extra_kwargs": "{\"class_code\":\"AGGR_C\", \"subtype_code\":\"NCA\", \"specific_name\":\"Natural Coarse Aggregate\", \"reference_key\":\"NCA\"}"},
        {"source_column": "rca_kg_m3", "target_table": "mix_component", "target_column": "dosage_kg_m3", 
         "extra_kwargs": "{\"class_code\":\"AGGR_C\", \"subtype_code\":\"RCA\", \"specific_name\":\"Recycled Coarse Aggregate\", \"reference_key\":\"RCA\"}"},
        {"source_column": "water_kg_m3", "target_table": "mix_component", "target_column": "dosage_kg_m3", 
         "extra_kwargs": "{\"class_code\":\"WATER\", \"subtype_code\":\"WATER\", \"specific_name\":\"Water\", \"reference_key\":\"WATER\"}"},
        {"source_column": "w_c_ratio", "target_table": "concrete_mix", "target_column": "w_c_ratio", "extra_kwargs": "{}"},
        
        # Material properties with reference keys
        {"source_column": "cement_sio2_pct", "target_table": "material_property", "target_column": "value_num", 
         "extra_kwargs": "{\"property_name\": \"sio2_pct\", \"property_group\": \"chemical\", \"material_ref_key\": \"CEMENT\"}"},
        {"source_column": "cement_al2o3_pct", "target_table": "material_property", "target_column": "value_num", 
         "extra_kwargs": "{\"property_name\": \"al2o3_pct\", \"property_group\": \"chemical\", \"material_ref_key\": \"CEMENT\"}"},
        
        # Aggregate details with reference keys
        {"source_column": "nca_sg", "target_table": "aggregate_detail", "target_column": "bulk_density_kg_m3", 
         "extra_kwargs": "{\"material_ref_key\": \"NCA\"}"},
        {"source_column": "nca_w_abs_pct", "target_table": "aggregate_detail", "target_column": "water_absorption_pct", 
         "extra_kwargs": "{\"material_ref_key\": \"NCA\"}"},
        {"source_column": "rca_sg", "target_table": "aggregate_detail", "target_column": "bulk_density_kg_m3", 
         "extra_kwargs": "{\"material_ref_key\": \"RCA\"}"},
        
        # Performance results
        {"source_column": "fcm_28d_mpa", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": "{\"category\": \"hardened\", \"test_name\": \"compressive_strength\", \"age_days\": 28}"},
        {"source_column": "slump_mm", "target_table": "performance_result", "target_column": "value_num", 
         "extra_kwargs": "{\"category\": \"fresh\", \"test_name\": \"slump\"}"},
    ]
    
    # Write to CSV file with proper formatting
    with open('etl/ds6_reference_mapping.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['source_column', 'target_table', 'target_column', 'extra_kwargs'])
        writer.writeheader()
        writer.writerows(mapping_data)
    
    print("Created reference mapping file at etl/ds6_reference_mapping.csv")
    print("Verifying JSON formatting...")
    
    # Verify the JSON is properly formatted
    issues = 0
    with open('etl/ds6_reference_mapping.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            try:
                json.loads(row.get('extra_kwargs') or "{}")
                print(f"Row {i}: {row['source_column']} - Valid JSON")
            except json.JSONDecodeError as e:
                print(f"Row {i}: {row['source_column']} - INVALID JSON: {e}")
                issues += 1
    
    if issues:
        print(f"Found {issues} JSON formatting issues")
    else:
        print("All JSON is properly formatted")

if __name__ == "__main__":
    create_mapping_file()
