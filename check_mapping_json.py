import csv
import json
import sys

def check_csv_json(filename):
    """Check if JSON in extra_kwargs column is valid"""
    print(f"Checking JSON in {filename}")
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            try:
                # Skip commented rows
                if row['source_column'].startswith('#'):
                    print(f"Line {i}: Skipping comment row")
                    continue
                    
                # Skip empty rows
                if not row['source_column'].strip():
                    print(f"Line {i}: Skipping empty row")
                    continue
                
                extra_kwargs = row.get('extra_kwargs', '{}')
                print(f"Line {i}: {row['source_column']} - extra_kwargs = {repr(extra_kwargs)}")
                
                # Try to parse JSON
                try:
                    parsed = json.loads(extra_kwargs or '{}')
                    print(f"  √ Valid JSON: {parsed}")
                except json.JSONDecodeError as e:
                    print(f"  ✗ Invalid JSON: {e}")
                    print(f"    Raw content: {repr(extra_kwargs)}")
            except Exception as e:
                print(f"Error processing row {i}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_csv_json(sys.argv[1])
    else:
        print("Please provide a CSV filename to check")
