# Script to fix the JSON formatting in mapping CSV files
import csv
import json
import os
from pathlib import Path

def fix_file(file_path, output_path=None):
    if output_path is None:
        # Create a backup of the original file
        backup_path = str(file_path) + '.bak'
        # Check if backup already exists and remove it
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.rename(file_path, backup_path)
        output_path = file_path
    
    rows = []
    with open(backup_path if output_path == file_path else file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)
        
        for row in reader:
            if len(row) >= 4:  # Make sure we have enough columns
                # Extract JSON field and fix if necessary
                json_str = row[3].strip()
                
                # Skip empty JSON
                if not json_str or json_str == '{}':
                    rows.append(row)
                    continue
                
                # Check if JSON is valid
                try:
                    json.loads(json_str)
                    rows.append(row)  # Already valid
                except json.JSONDecodeError:
                    # Try to fix common issues with JSON
                    # Check if it starts with { but doesn't end with }
                    if json_str.startswith('{') and not json_str.endswith('}'):
                        json_str += '}'
                    
                    # Add quotes around unquoted keys
                    json_str = json_str.replace("'class_code':", '"class_code":').replace("'subtype_code':", '"subtype_code":').replace("'specific_name':", '"specific_name":').replace("'is_cementitious':", '"is_cementitious":').replace("'source_type_column':", '"source_type_column":').replace("'prefix':", '"prefix":').replace("'property_name':", '"property_name":').replace("'property_group':", '"property_group":').replace("'bind_to_reference':", '"bind_to_reference":').replace("'bind_to_study':", '"bind_to_study":').replace("'bind_to_type':", '"bind_to_type":').replace("'subtype_from_value':", '"subtype_from_value":')
                    
                    # Fix true/false values
                    json_str = json_str.replace('True', 'true').replace('False', 'false')
                    
                    # Fix missing commas
                    for field in ['class_code', 'subtype_code', 'specific_name', 'is_cementitious', 'source_type_column', 'prefix', 'property_name', 'property_group', 'bind_to_reference', 'bind_to_study', 'bind_to_type']:
                        if f'"{field}":' in json_str:
                            # Find where this field ends (next quote after the field name + value)
                            field_start = json_str.find(f'"{field}":') 
                            if field_start >= 0:
                                value_start = field_start + len(f'"{field}":') 
                                # If the value starts with a quote, find the end quote
                                if value_start < len(json_str) and json_str[value_start:].strip().startswith('"'):
                                    value_start = json_str.find('"', value_start) + 1
                                    value_end = json_str.find('"', value_start)
                                    if value_end >= 0 and value_end + 1 < len(json_str) and json_str[value_end + 1] != ',':
                                        if json_str[value_end + 1] != '}':  # Don't add comma before closing brace
                                            json_str = json_str[:value_end + 1] + ',' + json_str[value_end + 1:]
                                # For non-string values (true, false, numbers)
                                else:
                                    # Find the end of the value (space, }, or field start)
                                    next_space = json_str.find(' ', value_start)
                                    next_brace = json_str.find('}', value_start)
                                    next_quote = json_str.find('"', value_start)
                                    
                                    # Find the first of these endings
                                    value_end = min(x for x in [next_space, next_brace, next_quote] if x >= 0)
                                    
                                    # Add comma if not already present and not at the end
                                    if value_end < len(json_str) - 1 and json_str[value_end] != ',' and json_str[value_end] != '}':
                                        json_str = json_str[:value_end] + ',' + json_str[value_end:]
                    
                    # Try parsing the fixed JSON
                    try:
                        parsed = json.loads(json_str)
                        # Success! Update the row
                        row[3] = json_str
                        print(f"Fixed JSON: {json_str}")
                    except json.JSONDecodeError as e:
                        print(f"Still can't parse: {json_str} - Error: {e}")
                    
                    rows.append(row)
            else:
                rows.append(row)  # Keep row as-is if it doesn't have enough columns
    
    # Write back to the output file
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    print(f"Processed {len(rows) - 1} rows in {file_path}")

# Manually fix the DS6 mapping files
print("Fixing DS6 column mapping...")
fix_file('etl/column_map_DS6.csv')

print("\nFixing DS6 properties column mapping...")
fix_file('etl/column_map_DS6_properties.csv')

print("\nFixing simple mapping file...")
fix_file('etl/simple_map.csv')

# Validate the fixed files
print("\nValidating fixed files...")

def validate_file(file_path):
    print(f"Validating {file_path}...")
    valid_rows = 0
    invalid_rows = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        
        for row in reader:
            if len(row) >= 4 and row[3].strip() and row[3].strip() != '{}':
                try:
                    json.loads(row[3])
                    valid_rows += 1
                except json.JSONDecodeError as e:
                    invalid_rows += 1
                    print(f"Invalid JSON in row: {row[0]} - {e}")
    
    print(f"Valid rows: {valid_rows}, Invalid rows: {invalid_rows}")
    return invalid_rows == 0

ds6_valid = validate_file('etl/column_map_DS6.csv')
ds6_props_valid = validate_file('etl/column_map_DS6_properties.csv')

if ds6_valid and ds6_props_valid:
    print("\nAll mapping files have been fixed and validated!")
else:
    print("\nThere are still some issues with the mapping files.")
