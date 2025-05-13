# Script to create properly formatted column mapping CSV
import csv
import json

# Define the column mapping data
data = [
    {"source_column": "item number", "target_table": "concrete_mix", "target_column": "mix_code", "extra_kwargs": ""},
    {"source_column": "mix_name_ref", "target_table": "concrete_mix", "target_column": "notes", "extra_kwargs": json.dumps({"prefix": "Original mix ref: "})},
    {"source_column": "binder(s)", "target_table": "concrete_mix", "target_column": "notes", "extra_kwargs": json.dumps({"prefix": "Binder(s): "})},
    {"source_column": "cement type", "target_table": "concrete_mix", "target_column": "notes", "extra_kwargs": json.dumps({"prefix": "Cement type: "})},
    {"source_column": "cemen_strength_class", "target_table": "concrete_mix", "target_column": "notes", "extra_kwargs": json.dumps({"prefix": "Cement strength class: "})},
    {"source_column": "clinker content", "target_table": "concrete_mix", "target_column": "notes", "extra_kwargs": json.dumps({"prefix": "Clinker content: "})},
    
    {"source_column": "cement content", "target_table": "mix_component", "target_column": "Cement", 
     "extra_kwargs": json.dumps({"class_code": "CEMENT", "is_cementitious": True, "source_type_column": "cement type"})},
    
    {"source_column": "scm1 content (kg/m3)", "target_table": "mix_component", "target_column": "SCM 1", 
     "extra_kwargs": json.dumps({"class_code": "SCM", "is_cementitious": True, "source_type_column": "scm1 type"})},
    
    {"source_column": "scm2 content (kg/m3)", "target_table": "mix_component", "target_column": "SCM 2", 
     "extra_kwargs": json.dumps({"class_code": "SCM", "is_cementitious": True, "source_type_column": "scm2 type"})},
    
    {"source_column": "water content (kg/m3)", "target_table": "mix_component", "target_column": "Water", 
     "extra_kwargs": json.dumps({"class_code": "WATER", "subtype_code": "water", "is_cementitious": False})},
    
    {"source_column": "admixture1_kgm3", "target_table": "mix_component", "target_column": "ADM 1", 
     "extra_kwargs": json.dumps({"class_code": "ADM", "is_cementitious": False, "source_type_column": "admixture1_type"})},
    
    {"source_column": "admixture2_kgm3", "target_table": "mix_component", "target_column": "ADM 2", 
     "extra_kwargs": json.dumps({"class_code": "ADM", "is_cementitious": False, "source_type_column": "admixture2_type"})},
    
    {"source_column": "water binder ratio", "target_table": "concrete_mix", "target_column": "w_b_ratio", "extra_kwargs": ""},
    
    {"source_column": "fcm. cube 150. wet curing (28 d)", "target_table": "performance_result", "target_column": "compressive_strength", 
     "extra_kwargs": json.dumps({"category": "hardened", "test_method_id": 1, "unit_id": 6, "age_days": 28})},
    
    {"source_column": "reference number", "target_table": "bibliographic_reference", "target_column": "citation_text", "extra_kwargs": ""}
]

# Write to CSV file
with open('../column_map_DS5.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=["source_column", "target_table", "target_column", "extra_kwargs"])
    writer.writeheader()
    writer.writerows(data)

print("Column mapping file created successfully.")
