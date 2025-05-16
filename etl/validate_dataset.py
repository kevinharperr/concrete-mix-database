#!/usr/bin/env python
"""
Validate dataset before import.

This script validates a dataset against the defined validation rules
without actually importing it into the database. It generates a validation
report that can be used to assess data quality before proceeding with import.
"""

import os
import sys
import argparse
import logging
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import importers
from etl.standard_dataset_importer import StandardDatasetImporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('validation.log')
    ]
)

def setup_argparse():
    """Set up command-line argument parsing."""
    parser = argparse.ArgumentParser(description='Validate concrete mix dataset')
    parser.add_argument('dataset_path', help='Path to the CSV dataset file')
    parser.add_argument('--dataset-code', '-d', default='TEST', help='Dataset code identifier')
    parser.add_argument('--output', '-o', default=None, help='Output file for validation report (JSON)')
    parser.add_argument('--details', '-v', action='store_true', help='Include detailed validation results')
    parser.add_argument('--threshold', '-t', type=float, default=0.9, 
                        help='Validation success threshold (0.0-1.0)')
    return parser

class DatasetValidator:
    """Validates datasets using the importer validation logic."""
    
    def __init__(self, dataset_path, dataset_code='TEST', logger=None):
        """Initialize validator."""
        self.dataset_path = dataset_path
        self.dataset_code = dataset_code
        self.logger = logger or logging.getLogger('dataset_validator')
        
        self.data = None
        self.validation_results = {
            'dataset_path': dataset_path,
            'dataset_code': dataset_code,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_mixes': 0,
                'valid_mixes': 0,
                'invalid_mixes': 0,
                'validation_rate': 0.0
            },
            'thresholds_used': {},
            'issues_summary': {},
            'issues_by_mix': {}
        }
    
    def load_data(self) -> bool:
        """Load the dataset."""
        try:
            self.data = pd.read_csv(self.dataset_path)
            self.validation_results['summary']['total_mixes'] = len(self.data)
            self.logger.info(f"Loaded {len(self.data)} rows from {self.dataset_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load data: {str(e)}")
            return False
    
    def validate(self, include_details=False) -> Dict:
        """
        Validate the dataset.
        
        Args:
            include_details: Whether to include detailed validation results by mix
            
        Returns:
            Dict: Validation results
        """
        if self.data is None and not self.load_data():
            return self.validation_results
        
        # Initialize importer for validation (without actually importing)
        importer = StandardDatasetImporter(self.dataset_code, self.dataset_path)
        
        # Record thresholds used
        self.validation_results['thresholds_used'] = importer.validation_thresholds
        
        try:
            # Preprocess data
            importer.preprocess_data()
            
            # Validate each mix
            for idx, row in self.data.iterrows():
                mix_code = row.get('mix_code', f"{self.dataset_code}_mix{idx}")
                
                # Extract mix data
                mix_data = {
                    'mix_code': mix_code,
                    'date_created': row.get('date_created'),
                    'region_country': row.get('region_country'),
                    'strength_class': row.get('strength_class'),
                    'target_slump_mm': row.get('target_slump_mm')
                }
                
                # Extract components
                components = importer.extract_mix_components(row)
                
                # Validate mix data
                mix_valid, mix_validation = importer.validate_mix_data(mix_data)
                
                # Validate components
                components_valid, components_validation = importer.validate_mix_components(components)
                
                # Combine validation results
                is_valid = mix_valid and components_valid
                validation_issues = mix_validation.get('issues', []) + components_validation.get('issues', [])
                
                # Update summary stats
                if is_valid:
                    self.validation_results['summary']['valid_mixes'] += 1
                else:
                    self.validation_results['summary']['invalid_mixes'] += 1
                    
                    # Count issue types
                    for issue in validation_issues:
                        issue_type = issue.split(':')[0].strip()
                        self.validation_results['issues_summary'][issue_type] = (
                            self.validation_results['issues_summary'].get(issue_type, 0) + 1
                        )
                
                # Include detailed results if requested
                if include_details or not is_valid:
                    self.validation_results['issues_by_mix'][mix_code] = {
                        'is_valid': is_valid,
                        'issues': validation_issues,
                        'components_count': len(components),
                        'w_b_ratio': components_validation.get('w_b_ratio')
                    }
            
            # Calculate validation rate
            total = self.validation_results['summary']['total_mixes']
            valid = self.validation_results['summary']['valid_mixes']
            self.validation_results['summary']['validation_rate'] = (
                round(valid / total, 4) if total > 0 else 0.0
            )
            
            self.logger.info(f"Validation complete: "
                            f"{valid}/{total} mixes valid "
                            f"({self.validation_results['summary']['validation_rate']*100:.1f}%)")
            
            return self.validation_results
            
        except Exception as e:
            self.logger.error(f"Error during validation: {str(e)}")
            self.validation_results['error'] = str(e)
            return self.validation_results
    
    def save_report(self, output_file=None) -> str:
        """
        Save the validation report to a file.
        
        Args:
            output_file: Path to save the report (if None, generate a filename)
            
        Returns:
            str: Path to the saved report file
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"validation_report_{self.dataset_code}_{timestamp}.json"
        
        try:
            with open(output_file, 'w') as f:
                json.dump(self.validation_results, f, indent=2)
            
            self.logger.info(f"Validation report saved to {output_file}")
            return output_file
        
        except Exception as e:
            self.logger.error(f"Failed to save report: {str(e)}")
            return None

def main():
    """Main function."""
    parser = setup_argparse()
    args = parser.parse_args()
    
    logger = logging.getLogger('validate_dataset')
    logger.info(f"Validating dataset: {args.dataset_path}")
    
    # Run validation
    validator = DatasetValidator(args.dataset_path, args.dataset_code, logger)
    results = validator.validate(include_details=args.details)
    
    # Save report if requested
    if args.output:
        validator.save_report(args.output)
    else:
        validator.save_report()
    
    # Check against threshold
    validation_rate = results['summary']['validation_rate']
    threshold_met = validation_rate >= args.threshold
    
    print(f"\nValidation Summary for {args.dataset_code}")
    print(f"{'='*40}")
    print(f"Total mixes:    {results['summary']['total_mixes']}")
    print(f"Valid mixes:    {results['summary']['valid_mixes']}")
    print(f"Invalid mixes:  {results['summary']['invalid_mixes']}")
    print(f"Validation rate: {validation_rate*100:.1f}%")
    print(f"Threshold:       {args.threshold*100:.1f}%")
    print(f"Threshold met:   {'✓' if threshold_met else '✗'}")
    
    # Show summary of issues
    if results['issues_summary']:
        print(f"\nCommon Issues:")
        for issue_type, count in sorted(results['issues_summary'].items(), 
                                        key=lambda x: x[1], reverse=True):
            print(f"  {issue_type}: {count} occurrences")
    
    return 0 if threshold_met else 1

if __name__ == "__main__":
    sys.exit(main())
