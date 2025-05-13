# Script to programmatically create a properly formatted mapping file for DS6 properties
import csv
import json

# Define the mapping data structure
mappings = [
    {"source_column": "reference_no", "target_table": "bibliographic_reference", "target_column": "citation_text", "extra_kwargs": {}},
    {"source_column": "study_no", "target_table": "concrete_mix", "target_column": "notes", "extra_kwargs": {"prefix": "Material properties study number: "}},
    {"source_column": "Authors", "target_table": "bibliographic_reference", "target_column": "author", "extra_kwargs": {}},
    {"source_column": "year of study", "target_table": "bibliographic_reference", "target_column": "year", "extra_kwargs": {}},
    {"source_column": "Type of binder", "target_table": "material", "target_column": "specific_name", "extra_kwargs": {"class_code": "SCM", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "subtype_from_value": True}},
    {"source_column": "SiO2 - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "sio2_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "Al2O3 - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "al2o3_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "Fe2O3 - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "fe2o3_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "CaO - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "cao_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "MgO - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "mgo_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "Na2O - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "na2o_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "K2O - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "k2o_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "SO3 - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "so3_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "TiO2 - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "tio2_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "P2O5 - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "p2o5_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "SrO - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "sro_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "Mn2O3 - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "mn2o3_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "LOI - Chemical compostion (w.r. %)", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "loi_pct", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "blaine_fineness_ssa_m2_kg", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "blaine_m2_kg", "property_group": "physical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "d50-median_particle_size_mm", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "median_particle_size_mm", "property_group": "physical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "Reactivity_modulus", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "reactivity_modulus", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "silica_modulus", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "silica_modulus", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "alumina_modulus", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "alumina_modulus", "property_group": "chemical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
    {"source_column": "specific_gravity", "target_table": "material_property", "target_column": "value_num", "extra_kwargs": {"property_name": "specific_gravity_g_cm3", "property_group": "physical", "bind_to_reference": "reference_no", "bind_to_study": "study_no", "bind_to_type": "Type of binder"}},
]

# Create the mapping file
with open('etl/column_map_DS6_properties_fixed2.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['source_column', 'target_table', 'target_column', 'extra_kwargs'])
    
    for mapping in mappings:
        # Convert the extra_kwargs dict to a proper JSON string
        extra_kwargs_json = json.dumps(mapping['extra_kwargs'])
        writer.writerow([
            mapping['source_column'],
            mapping['target_table'],
            mapping['target_column'],
            extra_kwargs_json
        ])

print("Created mapping file at: etl/column_map_DS6_properties_fixed2.csv")

# Validate the mapping file can be read back correctly
print("\nValidating mapping file...")
with open('etl/column_map_DS6_properties_fixed2.csv', 'r', newline='') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader, 1):
        try:
            # Try to parse the JSON
            extra_kwargs = json.loads(row['extra_kwargs'])
            print(f"Row {i}: {row['source_column']} -> {row['target_table']}.{row['target_column']} [OK]")
        except json.JSONDecodeError as e:
            print(f"Row {i}: Error parsing JSON: {e}")

print("\nMapping file created and validated successfully!")
