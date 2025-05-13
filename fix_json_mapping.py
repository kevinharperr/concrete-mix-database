# Script to fix JSON formatting in the column mapping file
import csv
import json
import re

# Path to the column mapping file
mapping_file = 'etl/column_map_DS6.csv'
output_file = 'etl/column_map_DS6_fixed.csv'

# Read the mapping file and fix the JSON formatting
fixed_rows = []
with open(mapping_file, 'r', newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    
    # Read header row
    header = next(reader)
    fixed_rows.append(header)
    
    # Process each row
    for row in reader:
        if len(row) >= 4:  # Make sure row has at least 4 columns
            # Get the extra_kwargs column
            extra_kwargs = row[3]
            
            # Skip if it's empty
            if extra_kwargs.strip():
                # Check if it's valid JSON
                try:
                    json_obj = json.loads(extra_kwargs)
                    # If valid, leave as is
                    fixed_rows.append(row)
                except json.JSONDecodeError:
                    # Fix common JSON errors
                    
                    # If surrounded by double quotes, extract the content
                    if extra_kwargs.startswith('"') and extra_kwargs.endswith('"'):
                        extra_kwargs = extra_kwargs[1:-1]
                    
                    # Replace single quotes with double quotes where appropriate
                    if '{' in extra_kwargs and '}' in extra_kwargs:
                        # Ensure property names have double quotes
                        fixed_json = re.sub(r'(\{|,)\s*([\w_]+)\s*:', r'\1"\2":', extra_kwargs)
                        
                        # Ensure string values have double quotes 
                        fixed_json = re.sub(r':\s*([^\s"\{\}\[\],]+)\s*(,|\})', r':"\1"\2', fixed_json)
                        
                        # Fix any remaining single quotes
                        fixed_json = fixed_json.replace("'", '"')
                        
                        # Validate the fixed JSON
                        try:
                            json.loads(fixed_json)
                            # Replace the row's extra_kwargs with fixed version
                            row[3] = fixed_json
                            fixed_rows.append(row)
                            print(f"Fixed: {extra_kwargs} -> {fixed_json}")
                        except json.JSONDecodeError as e:
                            print(f"Failed to fix: {extra_kwargs}, Error: {e}")
                            # Use empty JSON as fallback
                            row[3] = '{}'
                            fixed_rows.append(row)
                    else:
                        # Handle other cases
                        print(f"Skipping complex case: {extra_kwargs}")
                        # Use empty JSON as fallback
                        row[3] = '{}'
                        fixed_rows.append(row)
            else:
                # Keep row as is if extra_kwargs is empty
                fixed_rows.append(row)
        else:
            # Keep row as is if it doesn't have enough columns
            fixed_rows.append(row)

# Write the fixed rows to a new file
with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerows(fixed_rows)

print(f"Fixed mapping file created at {output_file}")
