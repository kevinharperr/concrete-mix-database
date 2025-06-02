#!/usr/bin/env python
"""
Data validation script to compare original datasets with database records.

Identifies discrepancies between original CSV dataset files and the
concrete mix database to find potential import errors.
"""
import os
import sys
import django
import pandas as pd
from decimal import Decimal
import re

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

# Import Django models
from django.db.models import Sum, Count
from cdb_app.models import ConcreteMix, MixComponent, Material, Dataset

class DatasetValidator:
    """Validates consistency between original datasets and database records."""
    
    # Define column mappings from CSV to database fields
    COLUMN_MAPPINGS = {
        'mix_number': ['Mix Number', 'Mix No.', 'mix_number', 'Mix_Number', 'MixNumber', 'Mix ID', 'MixID'],
        'cement': ['Cement Content kg/m^3', 'cement kg/m3', 'Cement kg/m3', 'Cement', 'cement'],
        'water': ['Water Content kg/m^3', 'water kg/m3', 'Water kg/m3', 'Effective water kg/m3', 'Water', 'water'],
        'w_c_ratio': ['Eff. W/C ratio', 'W/C ratio', 'w/c', 'W/C', 'wc', 'Water-cement ratio'],
        'nca': ['NCA Content', 'Natural aggregate kg/m3', 'Natural Coarse Aggregate', 'NCA'],
        'nfa': ['NFA Content', 'Natural fine aggregate kg/m3', 'Sand Content', 'Natural Fine Aggregate', 'NFA'],
        'rca': ['RCA Content', 'Recycled aggregate kg/m3', 'Recycled Coarse Aggregate', 'RCA'],
    }
    
    def __init__(self, dataset_mapping=None):
        """Initialize with dataset mapping (dataset_id to CSV path)."""
        self.dataset_mapping = dataset_mapping or {
            # Default mapping - can be overridden
            2: "etl/ds2.csv",
            3: "etl/ds3.csv"
        }
        self.results = {}
    
    def find_column(self, df, field_options):
        """Find the first matching column from options in the dataframe."""
        for option in field_options:
            if option in df.columns:
                return option
        return None
    
    def get_mix_number_from_code(self, mix_code, dataset_id):
        """Extract mix number from mix code like 'DS2-734'."""
        if not mix_code:
            return None
        
        # Try pattern DS{id}-{number}
        pattern = f"DS{dataset_id}-(\d+)"  # Properly escaped sequence
        match = re.match(pattern, mix_code)
        if match:
            return int(match.group(1))
        
        # For older codes that might just be numbers
        if mix_code.isdigit():
            return int(mix_code)
        
        return None
    
    def get_component_dosage(self, mix, material_class=None, subtype=None):
        """Get total dosage of components matching criteria in a mix."""
        query = MixComponent.objects.filter(mix=mix)
        
        if material_class:
            query = query.filter(material__material_class__class_code=material_class)
        
        if subtype:
            query = query.filter(material__subtype_code=subtype)
        
        result = query.aggregate(total=Sum('dosage_kg_m3'))['total']
        return result or Decimal('0')
    
    def values_match(self, v1, v2, tolerance=0.03):
        """Compare two numeric values with tolerance."""
        if v1 is None or v2 is None:
            return v1 == v2
        
        try:
            # Convert to Decimal for precise comparison
            d1 = Decimal(str(float(v1))) if v1 != '' else Decimal('0')
            d2 = Decimal(str(float(v2))) if v2 != '' else Decimal('0')
            
            # If both values are very small, consider them equal
            if d1 < Decimal('0.1') and d2 < Decimal('0.1'):
                return True
            
            # If one value is zero and the other is very small
            if (d1 == 0 and d2 < Decimal('1')) or (d2 == 0 and d1 < Decimal('1')):
                return True
            
            # For larger values, use percentage tolerance
            if d2 == 0:  # Avoid division by zero
                return d1 == 0
            
            return abs(d1 - d2) <= (d2 * Decimal(str(tolerance)))
        except (ValueError, TypeError):
            # If conversion fails, do string comparison
            return str(v1).strip() == str(v2).strip()
    
    def validate_dataset(self, dataset_id):
        """Compare dataset in database with original CSV."""
        csv_path = self.dataset_mapping.get(dataset_id)
        if not csv_path or not os.path.exists(csv_path):
            print(f"Dataset file not found: {csv_path}")
            return []
        
        print(f"\n{'-'*80}\nValidating dataset {dataset_id} against {csv_path}")
        
        # Load CSV data
        try:
            df = pd.read_csv(csv_path)
            print(f"Loaded {len(df)} records from CSV")
        except Exception as e:
            print(f"Error loading CSV: {str(e)}")
            return []
        
        # Find column names for this dataset
        field_columns = {}
        for field, options in self.COLUMN_MAPPINGS.items():
            column = self.find_column(df, options)
            field_columns[field] = column
            if not column:
                print(f"Warning: Could not find column for {field} in {csv_path}")
        
        # Get database mixes for this dataset
        db_mixes = ConcreteMix.objects.filter(dataset_id=dataset_id)
        print(f"Found {db_mixes.count()} mixes in database for dataset {dataset_id}")
        
        # Track mismatches
        mismatches = []
        
        # Find mix number column
        mix_number_col = self.find_column(df, self.COLUMN_MAPPINGS['mix_number'])
        if not mix_number_col:
            print(f"Error: Could not find mix number column in {csv_path}")
            return []
            
        # Create a set of available mix numbers in CSV
        try:
            csv_mix_numbers = set(df[mix_number_col].astype(int).tolist())
        except Exception as e:
            print(f"Error processing mix numbers from CSV: {str(e)}")
            # Try to handle non-numeric mix numbers
            csv_mix_numbers = set()
            for val in df[mix_number_col].values:
                try:
                    if pd.notna(val):
                        csv_mix_numbers.add(int(val))
                except (ValueError, TypeError):
                    pass
                    
        # Initialize db mix numbers tracker
        db_mix_numbers = set()
            
        # Process each mix in database
        for mix in db_mixes:
            mix_number = self.get_mix_number_from_code(mix.mix_code, dataset_id)
            if not mix_number:
                print(f"Warning: Could not extract mix number from {mix.mix_code}")
                continue
            
            db_mix_numbers.add(mix_number)
            
            # Find this mix in original data
            if mix_number not in csv_mix_numbers:
                print(f"Warning: Mix {mix.mix_code} (#{mix_number}) not found in original dataset")
                continue
                
            try:
                original = df[df[mix_number_col] == mix_number].iloc[0]
            except (IndexError, ValueError) as e:
                print(f"Error finding mix {mix_number} in CSV: {str(e)}")
                continue
            
            # Compare key fields
            discrepancies = []
            
            # Check cement content
            if field_columns.get('cement'):
                db_cement = self.get_component_dosage(mix, 'CEMENT')
                csv_cement = original.get(field_columns['cement'])
                if not self.values_match(db_cement, csv_cement):
                    discrepancies.append(f"Cement: DB={db_cement}, CSV={csv_cement}")
            
            # Check water content
            if field_columns.get('water'):
                db_water = self.get_component_dosage(mix, 'WATER')
                csv_water = original.get(field_columns['water'])
                if not self.values_match(db_water, csv_water):
                    discrepancies.append(f"Water: DB={db_water}, CSV={csv_water}")
            
            # Check w/c ratio
            if field_columns.get('w_c_ratio'):
                db_wc = mix.w_c_ratio
                csv_wc = original.get(field_columns['w_c_ratio'])
                if not self.values_match(db_wc, csv_wc):
                    discrepancies.append(f"W/C ratio: DB={db_wc}, CSV={csv_wc}")
            
            # Check NCA content
            if field_columns.get('nca'):
                db_nca = self.get_component_dosage(mix, 'AGGR_C', 'NCA')
                csv_nca = original.get(field_columns['nca'])
                if not self.values_match(db_nca, csv_nca):
                    discrepancies.append(f"NCA: DB={db_nca}, CSV={csv_nca}")
            
            # Check NFA content
            if field_columns.get('nfa'):
                db_nfa = self.get_component_dosage(mix, 'AGGR_F', 'NFA')
                csv_nfa = original.get(field_columns['nfa'])
                if not self.values_match(db_nfa, csv_nfa):
                    discrepancies.append(f"NFA: DB={db_nfa}, CSV={csv_nfa}")
            
            # Check RCA content
            if field_columns.get('rca'):
                db_rca = self.get_component_dosage(mix, 'AGGR_C', 'RCA')
                csv_rca = original.get(field_columns['rca'])
                if not self.values_match(db_rca, csv_rca):
                    discrepancies.append(f"RCA: DB={db_rca}, CSV={csv_rca}")
            
            # Check if any components are missing that should be present
            components = MixComponent.objects.filter(mix=mix).count()
            if components < 3:  # At minimum should have cement, water, and aggregate
                discrepancies.append(f"Missing components: only {components} found")
            
            if discrepancies:
                mismatches.append({
                    'mix_id': mix.mix_id,
                    'mix_code': mix.mix_code,
                    'mix_number': mix_number,
                    'discrepancies': discrepancies
                })
        
        # Check for missing mixes from CSV that should be in DB
        csv_only = csv_mix_numbers - db_mix_numbers
        db_only = db_mix_numbers - csv_mix_numbers
        
        # Report results
        print(f"\nFound {len(mismatches)} mixes with discrepancies out of {db_mixes.count()} total mixes")
        print(f"CSV-only mix numbers: {len(csv_only)} mixes in CSV not found in database")
        print(f"DB-only mix numbers: {len(db_only)} mixes in database not found in CSV")
        
        if mismatches:
            print("\nTop discrepancies:")
            for m in mismatches[:10]:  # Show first 10 discrepancies
                print(f"\nMix {m['mix_code']} (ID: {m['mix_id']}, Mix Number: {m['mix_number']}):")
                for d in m['discrepancies']:
                    print(f"  - {d}")
            
            if len(mismatches) > 10:
                print(f"...and {len(mismatches) - 10} more mixes with discrepancies")
        
        # Store results for this dataset
        self.results[dataset_id] = {
            'mismatches': mismatches,
            'csv_only': csv_only,
            'db_only': db_only
        }
        
        return mismatches
    
    def validate_all(self):
        """Validate all datasets in the mapping."""
        all_mismatches = {}
        for dataset_id in self.dataset_mapping:
            mismatches = self.validate_dataset(dataset_id)
            all_mismatches[dataset_id] = mismatches
        
        self.print_summary()
        return all_mismatches
    
    def print_summary(self):
        """Print summary of validation results."""
        print("\n\n" + "="*40)
        print("VALIDATION SUMMARY")
        print("="*40)
        
        total_mismatches = 0
        total_mixes = 0
        
        for dataset_id, result in self.results.items():
            mismatch_count = len(result['mismatches'])
            total_mismatches += mismatch_count
            dataset_mixes = ConcreteMix.objects.filter(dataset_id=dataset_id).count()
            total_mixes += dataset_mixes
            
            print(f"Dataset {dataset_id}: {mismatch_count} mismatches out of {dataset_mixes} mixes")
            print(f"  - {len(result['csv_only'])} mixes in CSV but not in database")
            print(f"  - {len(result['db_only'])} mixes in database but not in CSV")
        
        print("\nOVERALL:")
        print(f"Total mismatches: {total_mismatches} out of {total_mixes} mixes")
        if total_mixes > 0:
            percentage = (total_mismatches / total_mixes) * 100
            print(f"Percentage with issues: {percentage:.1f}%")

def get_available_datasets():
    """Find available dataset files in etl directory."""
    dataset_mapping = {}
    etl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'etl')
    
    if not os.path.exists(etl_dir):
        return dataset_mapping
    
    # Look for dataset files like ds1.csv, ds2.csv, etc.
    for filename in os.listdir(etl_dir):
        if filename.lower().startswith('ds') and filename.lower().endswith('.csv'):
            try:
                # Extract dataset number
                dataset_id = int(filename[2:-4])  # Extract number from 'ds2.csv'
                dataset_mapping[dataset_id] = os.path.join('etl', filename)
            except ValueError:
                continue
    
    return dataset_mapping

def main():
    # Find available datasets
    dataset_mapping = get_available_datasets()
    if not dataset_mapping:
        print("No dataset files found in 'etl' directory")
        return
    
    print(f"Found {len(dataset_mapping)} dataset files: {', '.join(dataset_mapping.values())}")
    
    # Create validator and run validation
    validator = DatasetValidator(dataset_mapping)
    validator.validate_all()

if __name__ == "__main__":
    main()
