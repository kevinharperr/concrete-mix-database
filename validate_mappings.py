# Script to validate column mapping files
import csv
import json
from pathlib import Path

def validate_mapping_file(file_path):
    print(f"Validating mapping file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                json_str = row.get('extra_kwargs', '{}')
                try:
                    json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"\nError in row {i}, column 'extra_kwargs'")
                    print(f"Value: {json_str}")
                    print(f"Error: {e}")
                    print(f"Position: line {e.lineno}, column {e.colno}, char {e.pos}")
                    return False
        print("All rows validated successfully.")
        return True
    except Exception as e:
        print(f"Error opening or reading file: {e}")
        return False

def fix_mapping_file(file_path):
    fixed_rows = []
    fixed_any = False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        fixed_rows.append(headers)
        
        for i, row in enumerate(reader, 1):
            if len(row) >= 4:  # Make sure we have enough columns
                # Try to parse and fix JSON in extra_kwargs
                try:
                    json.loads(row[3])
                    fixed_rows.append(row)  # No fix needed
                except json.JSONDecodeError:
                    # Common JSON syntax issues:
                    # 1. Single quotes instead of double quotes
                    # 2. Unquoted keys
                    # 3. Trailing commas
                    # 4. Boolean values not lowercase
                    fixed_json = row[3]
                    
                    # Replace single quotes with double quotes but be careful with already escaped quotes
                    if "'" in fixed_json:
                        fixed_json = fixed_json.replace("'", '"')
                    
                    # Try to fix True/False capitalization
                    fixed_json = fixed_json.replace('True', 'true').replace('False', 'false')
                    
                    # Remove trailing commas before closing braces
                    fixed_json = fixed_json.replace(',}', '}')
                    
                    try:
                        # Verify our fix worked
                        json.loads(fixed_json)
                        row[3] = fixed_json
                        fixed_rows.append(row)
                        fixed_any = True
                        print(f"Fixed JSON in row {i}: {fixed_json}")
                    except json.JSONDecodeError as e:
                        print(f"Failed to fix JSON in row {i}: {e}")
                        fixed_rows.append(row)  # Add the original row anyway
            else:
                fixed_rows.append(row)  # Add as-is if not enough columns
    
    if fixed_any:
        # Write the fixed data back to the file
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(fixed_rows)
        print(f"Fixed mapping file saved to: {file_path}")
    
    return fixed_any

# Validate mapping files
mapping_files = [
    Path('etl/column_map_DS6.csv'),
    Path('etl/column_map_DS6_properties.csv')
]

for file_path in mapping_files:
    print(f"\nProcessing {file_path}")
    valid = validate_mapping_file(file_path)
    
    if not valid:
        print(f"Attempting to fix {file_path}...")
        fixed = fix_mapping_file(file_path)
        if fixed:
            # Validate again after fixing
            print("Validating fixed file:")
            validate_mapping_file(file_path)
        else:
            print(f"No automatic fixes applied to {file_path}")
