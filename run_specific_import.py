#!/usr/bin/env python3

import sys
import os
import argparse
import importlib.util
from pathlib import Path

def main():
    """
    Runner script for the configuration-driven dataset importer.
    
    Usage:
        python run_specific_import.py ds2_config
        python run_specific_import.py etl.ds3_config --verbose
    """
    
    parser = argparse.ArgumentParser(
        description="Run dataset import using configuration files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_specific_import.py ds2_config
  python run_specific_import.py etl.ds2_config --verbose
  python run_specific_import.py etl.ds3_config --dry-run
        """
    )
    
    parser.add_argument(
        'config_module',
        help='Configuration module name (e.g., ds2_config or etl.ds2_config)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration and show what would be imported without actually importing'
    )
    
    args = parser.parse_args()
    
    try:
        # Import the configuration module
        config_module = load_config_module(args.config_module)
        
        if not hasattr(config_module, 'CONFIG'):
            print(f"ERROR: Configuration module '{args.config_module}' does not have a CONFIG dictionary")
            sys.exit(1)
        
        config = config_module.CONFIG
        
        # Validate configuration
        validation_errors = validate_config(config)
        if validation_errors:
            print("Configuration validation errors:")
            for error in validation_errors:
                print(f"  - {error}")
            sys.exit(1)
        
        print(f"Loaded configuration for: {config['dataset_meta']['name']}")
        print(f"CSV file: {config['dataset_meta']['csv_file_path']}")
        
        if args.dry_run:
            print("\n=== DRY RUN MODE ===")
            print_config_summary(config)
            return
        
        # Import the DatasetImporter
        from etl.importer_engine import DatasetImporter
        
        # Create and run the importer
        importer = DatasetImporter(config)
        
        if args.verbose:
            import logging
            logging.getLogger().setLevel(logging.DEBUG)
        
        print(f"\nStarting import for {config['dataset_meta']['name']}...")
        stats = importer.run_import()
        
        print(f"\nImport completed successfully!")
        print(f"Imported {stats['successful_mixes']} mixes with {stats['components_created']} components")
        print(f"Created {stats['performance_results_created']} performance results")
        
        if stats['failed_mixes'] > 0:
            print(f"Warning: {stats['failed_mixes']} mixes failed to import")
        
        if stats['validation_errors'] > 0:
            print(f"Warning: {stats['validation_errors']} validation errors encountered")
        
    except KeyboardInterrupt:
        print("\nImport cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def load_config_module(module_name):
    """Load a configuration module by name."""
    try:
        # Try to import as a regular module first
        if '.' in module_name:
            # Handle dotted module names like 'etl.ds2_config'
            module = importlib.import_module(module_name)
        else:
            # Try to find the module in common locations
            possible_paths = [
                f"{module_name}.py",
                f"etl/{module_name}.py",
                f"configs/{module_name}.py"
            ]
            
            module_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    module_path = path
                    break
            
            if not module_path:
                raise ImportError(f"Could not find configuration module '{module_name}' in any of: {possible_paths}")
            
            # Load the module from the file path
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        
        return module
        
    except ImportError as e:
        raise ImportError(f"Could not import configuration module '{module_name}': {e}")


def validate_config(config):
    """Validate the configuration dictionary."""
    errors = []
    
    # Check required top-level keys
    required_keys = ['dataset_meta', 'column_to_concretemix_fields', 'materials', 'performance_results']
    for key in required_keys:
        if key not in config:
            errors.append(f"Missing required configuration key: {key}")
    
    # Validate dataset_meta
    if 'dataset_meta' in config:
        meta = config['dataset_meta']
        required_meta_keys = ['name', 'csv_file_path']
        for key in required_meta_keys:
            if key not in meta:
                errors.append(f"Missing required dataset_meta key: {key}")
        
        # Check if CSV file exists
        if 'csv_file_path' in meta:
            csv_path = meta['csv_file_path']
            if not os.path.exists(csv_path):
                errors.append(f"CSV file not found: {csv_path}")
    
    # Validate materials
    if 'materials' in config:
        for i, material in enumerate(config['materials']):
            if 'material_class_code' not in material:
                errors.append(f"Material {i}: missing material_class_code")
            if 'fixed_properties' not in material:
                errors.append(f"Material {i}: missing fixed_properties")
            
            # Check if materials that should have quantities have csv_column_for_quantity
            if material.get('create_mix_component', True) and 'csv_column_for_quantity' not in material:
                errors.append(f"Material {i}: missing csv_column_for_quantity for component creation")
    
    # Validate performance_results
    if 'performance_results' in config:
        for i, perf in enumerate(config['performance_results']):
            required_perf_keys = ['property_pk', 'csv_column_for_value', 'unit_symbol']
            for key in required_perf_keys:
                if key not in perf:
                    errors.append(f"Performance result {i}: missing {key}")
    
    return errors


def print_config_summary(config):
    """Print a summary of the configuration."""
    print(f"\nDataset: {config['dataset_meta']['name']}")
    print(f"Description: {config['dataset_meta'].get('description', 'N/A')}")
    print(f"CSV file: {config['dataset_meta']['csv_file_path']}")
    
    print(f"\nMaterials to import ({len(config['materials'])}):")
    for i, material in enumerate(config['materials']):
        name = material['fixed_properties'].get('specific_name', 'Unknown')
        class_code = material['material_class_code']
        quantity_col = material.get('csv_column_for_quantity', 'N/A')
        create_component = material.get('create_mix_component', True)
        print(f"  {i+1}. {name} ({class_code}) - Quantity from: {quantity_col} - Component: {create_component}")
    
    print(f"\nPerformance results to import ({len(config['performance_results'])}):")
    for i, perf in enumerate(config['performance_results']):
        prop = perf['property_pk']
        value_col = perf['csv_column_for_value']
        unit = perf['unit_symbol']
        age = perf.get('fixed_age_days', 'Variable')
        print(f"  {i+1}. {prop} from {value_col} ({unit}) at {age} days")
    
    validation_rules = config.get('validation_rules', {})
    if validation_rules:
        print(f"\nValidation rules ({len(validation_rules)}):")
        for column, rules in validation_rules.items():
            rule_str = ", ".join([f"{k}: {v}" for k, v in rules.items()])
            print(f"  {column}: {rule_str}")


if __name__ == "__main__":
    main() 