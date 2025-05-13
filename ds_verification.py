# ds_verification.py
# Script to perform health checks and quality audits on imported datasets

import os
import sys
import django
import collections
import decimal
import csv
from pathlib import Path

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete_mix_project.settings")
django.setup()

from cdb_app import models as cdb
from django.db.models import Count, Avg, Max, Min, F, Sum, FloatField, Q, Case, When, Value
from django.db.models.functions import Cast
from django.db.models.expressions import RawSQL
from decimal import Decimal

# Ensure reports directory exists
report_dir = Path("./reports")
report_dir.mkdir(exist_ok=True)

# Convert strings to Decimal for precise math
def to_decimal(value, default=None):
    if value is None:
        return default
    try:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    except (ValueError, decimal.InvalidOperation):
        return default

# Health check class to organize and report issues
class HealthCheck:
    def __init__(self, dataset_code):
        self.dataset_code = dataset_code
        self.issues = []
        self.csv_path = report_dir / f"{dataset_code.lower()}_health_flags.csv"
        self.threshold_wc_min = Decimal('0.2')
        self.threshold_wc_max = Decimal('1.2')
        self.threshold_strength_min = Decimal('5.0')  # MPa
        self.threshold_strength_max = Decimal('120.0')  # MPa
        self.threshold_density_max = Decimal('3000.0')  # kg/m³
        self.threshold_water_absorption_max = Decimal('15.0')  # %
        self.threshold_diameter_min = Decimal('75.0')  # mm
        self.threshold_diameter_max = Decimal('300.0')  # mm
        self.threshold_agg_sum_tolerance = Decimal('3.0')  # kg/m³
        self.threshold_wc_tolerance = Decimal('0.02')  # For comparing calculated vs reported W/C
        
        # Mix code cache for efficient checking
        self._mix_code_dict = {}
    
    def flag_issue(self, mix_code, issue_code, issue_description):
        """Flag an issue with a mix"""
        self.issues.append({
            'mix_code': mix_code,
            'issue_code': issue_code,
            'issue_description': issue_description
        })
    
    def save_issues_to_csv(self):
        """Save issues to CSV file"""
        if not self.issues:
            print(f"\nNo issues to save to CSV.")
            return
            
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['mix_code', 'issue_code', 'issue_description'])
            writer.writeheader()
            
            # Convert any Unicode symbols to ASCII for compatibility
            clean_issues = []
            for issue in self.issues:
                clean_desc = issue['issue_description'].replace('≥', '>=').replace('≠', '!=')
                clean_issues.append({
                    'mix_code': issue['mix_code'],
                    'issue_code': issue['issue_code'],
                    'issue_description': clean_desc
                })
            
            writer.writerows(clean_issues)
        
        print(f"\nIssues saved to {self.csv_path}")
        return self.csv_path
    
    def get_mix_code(self, mix_id):
        """Get mix code for a mix ID, with caching"""
        if mix_id not in self._mix_code_dict:
            try:
                self._mix_code_dict[mix_id] = cdb.ConcreteMix.objects.using("cdb").get(mix_id=mix_id).mix_code
            except cdb.ConcreteMix.DoesNotExist:
                self._mix_code_dict[mix_id] = f"Unknown-{mix_id}"
        return self._mix_code_dict[mix_id]
    
    def check_high_level_counts(self):
        """Check high-level counts of various entities"""
        print(f"\n1. High-Level Counts\n{'-'*30}")
        
        # ConcreteMix counts
        mix_count = cdb.ConcreteMix.objects.using("cdb").filter(
            dataset__dataset_name=self.dataset_code
        ).count()
        print(f"ConcreteMix count: {mix_count}")
        
        # MixComponent: Get mixes with fewer than 6 components
        mix_component_counts = cdb.MixComponent.objects.using("cdb").filter(
            mix__dataset__dataset_name=self.dataset_code
        ).values('mix').annotate(component_count=Count('material')).filter(component_count__lt=6)
        
        low_component_mixes = mix_component_counts.count()
        print(f"Mixes with < 6 components: {low_component_mixes}")
        
        for item in mix_component_counts:
            mix_code = self.get_mix_code(item['mix'])
            self.flag_issue(
                mix_code=mix_code,
                issue_code="LOW_COMPONENT_COUNT",
                issue_description=f"Mix has only {item['component_count']} components (expected ≥ 6)"
            )
        
        # PerformanceResult: Check for mixes with no hardened results
        mixes_without_hardened = cdb.ConcreteMix.objects.using("cdb").filter(
            dataset__dataset_name=self.dataset_code
        ).exclude(
            performance_results__category='hardened'
        )
        
        print(f"Mixes without hardened results: {mixes_without_hardened.count()}")
        
        for mix in mixes_without_hardened:
            self.flag_issue(
                mix_code=mix.mix_code,
                issue_code="NO_HARDENED_RESULTS",
                issue_description="Mix has no hardened performance results"
            )
        
        # Specimen: Check hardened results without linked specimens
        results_without_specimen = cdb.PerformanceResult.objects.using("cdb").filter(
            mix__dataset__dataset_name=self.dataset_code,
            category='hardened',
            specimen__isnull=True
        )
        
        print(f"Hardened results without specimens: {results_without_specimen.count()}")
        
        for result in results_without_specimen:
            self.flag_issue(
                mix_code=result.mix.mix_code,
                issue_code="NO_SPECIMEN",
                issue_description=f"Hardened result (id={result.result_id}) has no linked specimen"
            )
        
        # ConcreteMixReference: Mixes without references
        # We'll use raw SQL since the model's primary key is composite
        with django.db.connections['cdb'].cursor() as cursor:
            cursor.execute("""
                SELECT m.mix_id, m.mix_code FROM concrete_mix m
                JOIN dataset d ON m.dataset_id = d.dataset_id
                WHERE d.dataset_name = %s
                AND NOT EXISTS (
                    SELECT 1 FROM concrete_mix_reference r
                    WHERE r.mix_id = m.mix_id
                )
            """, [self.dataset_code])
            mixes_without_refs = cursor.fetchall()
        
        print(f"Mixes without bibliographic references: {len(mixes_without_refs)}")
        
        for mix_id, mix_code in mixes_without_refs:
            self.flag_issue(
                mix_code=mix_code,
                issue_code="NO_REFERENCE",
                issue_description="Mix has no linked bibliographic references"
            )
    
    def check_component_sanity(self):
        """Check component dosages and ratios for sanity"""
        print(f"\n2. Component Sanity Checks\n{'-'*30}")
        
        # 2.1 Get mixes with negative or NULL dosages
        components_with_issues = cdb.MixComponent.objects.using("cdb").filter(
            Q(mix__dataset__dataset_name=self.dataset_code) &
            (Q(dosage_kg_m3__lt=0) | Q(dosage_kg_m3__isnull=True))
        )
        
        null_or_negative_count = components_with_issues.count()
        print(f"Components with NULL or negative dosages: {null_or_negative_count}")
        
        for comp in components_with_issues:
            issue_desc = "NULL dosage" if comp.dosage_kg_m3 is None else f"Negative dosage: {comp.dosage_kg_m3}"
            self.flag_issue(
                mix_code=comp.mix.mix_code,
                issue_code="BAD_DOSAGE",
                issue_description=f"{comp.material.specific_name}: {issue_desc}"
            )
        
        # 2.2 Aggregate calculations and checks
        mixes = cdb.ConcreteMix.objects.using("cdb").filter(
            dataset__dataset_name=self.dataset_code
        )
        
        aggregate_mismatch_count = 0
        wc_ratio_mismatch_count = 0
        wc_ratio_out_of_range_count = 0
        
        for mix in mixes:
            # Get all components for this mix
            components = cdb.MixComponent.objects.using("cdb").filter(mix=mix)
            
            # Get cement, water and aggregate components for calculations
            try:
                water = components.filter(
                    material__material_class_id="WATER"
                ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
                
                # Get just cement components (CEMENT class only, not other cementitious materials)
                cement = components.filter(
                    material__material_class_id="CEMENT"
                ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
                
                nfa = components.filter(
                    material__material_class_id="AGGR_F"
                ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
                
                rca = components.filter(
                    material__subtype_code="RCA"
                ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
                
                nca = components.filter(
                    Q(material__material_class_id="AGGR_C") & 
                    ~Q(material__subtype_code="RCA")
                ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
                
                # Calculate total aggregate and coarse aggregate
                total_coarse = nca + rca
                total_aggregate = nfa + total_coarse
                
                # Check if there's a note about total aggregate:cement ratio
                if mix.notes and "Total Agg/Cement Ratio" in mix.notes:
                    # Parse notes to find expected total aggregate
                    try:
                        ratio_parts = [p for p in mix.notes.split(";") if "Total Agg/Cement Ratio" in p]
                        if ratio_parts:
                            ratio_text = ratio_parts[0].split(":")[1].strip()
                            agg_cement_ratio = to_decimal(ratio_text)
                            expected_agg = cement * agg_cement_ratio
                            
                            # Check if total aggregate matches expected within tolerance
                            if abs(total_aggregate - expected_agg) > self.threshold_agg_sum_tolerance:
                                aggregate_mismatch_count += 1
                                self.flag_issue(
                                    mix_code=mix.mix_code,
                                    issue_code="AGG_SUM_MISMATCH",
                                    issue_description=f"Aggregate sum ({total_aggregate:.1f}) doesn't match expected from ratio ({expected_agg:.1f})"
                                )
                    except (IndexError, ValueError):
                        pass
                
                # Calculate water-to-cement and water-to-binder ratios
                if cement > 0:
                    # Get SCM (supplementary cementitious materials) components
                    # Include materials of SCM class and also those marked as cementitious but not cement
                    scm = components.filter(
                        Q(material__material_class_id="SCM") | 
                        (Q(is_cementitious=True) & ~Q(material__material_class_id="CEMENT"))
                    ).aggregate(Sum('dosage_kg_m3'))['dosage_kg_m3__sum'] or Decimal('0')
                    
                    # Calculate binder total (cement + SCM)
                    binder = cement + scm
                    
                    # Calculate both ratios
                    calculated_wc = water / cement  # W/C ratio
                    calculated_wb = water / binder  # W/B ratio
                    
                    # Debug print for DS1-5 to verify calculations
                    if mix.mix_code == 'DS1-5':
                        print(f"DEBUG - Mix: {mix.mix_code}")
                        print(f"Water: {water}, Cement: {cement}, Binder: {binder}")
                        print(f"Calculated W/C: {calculated_wc}, Reported W/C: {mix.w_c_ratio}")
                        print(f"Calculated W/B: {calculated_wb}, Reported W/B: {mix.w_b_ratio}")
                        print(f"Tolerance: {self.threshold_wc_tolerance}")
                        print(f"W/C diff: {abs(calculated_wc - mix.w_c_ratio)}")
                        print(f"W/B diff: {abs(calculated_wb - mix.w_b_ratio) if mix.w_b_ratio else 'N/A'}")
                    
                    # Check water-to-cement ratio (W/C)
                    if mix.w_c_ratio is not None:
                        # Round to 2 decimal places before comparison to avoid floating point issues
                        calc_wc_rounded = round(calculated_wc, 2)
                        reported_wc_rounded = round(mix.w_c_ratio, 2)
                        
                        if abs(calc_wc_rounded - reported_wc_rounded) > self.threshold_wc_tolerance:
                            wc_ratio_mismatch_count += 1
                            self.flag_issue(
                                mix_code=mix.mix_code,
                                issue_code="WC_RATIO_MISMATCH",
                                issue_description=f"Calculated W/C ratio ({calculated_wc:.2f}) ≠ Reported W/C ratio ({mix.w_c_ratio:.2f})"
                            )
                    
                    # Check water-to-binder ratio (W/B)
                    if mix.w_b_ratio is not None:
                        # Round to 2 decimal places before comparison to avoid floating point issues
                        calc_wb_rounded = round(calculated_wb, 2)
                        reported_wb_rounded = round(mix.w_b_ratio, 2)
                        
                        # Only check mismatch if wb_k_reported is NULL - since k-value affects w/b calculations
                        if abs(calc_wb_rounded - reported_wb_rounded) > self.threshold_wc_tolerance and mix.wb_k_reported is None:
                            # Count as a W/C mismatch for reporting purposes
                            wc_ratio_mismatch_count += 1
                            self.flag_issue(
                                mix_code=mix.mix_code,
                                issue_code="WB_RATIO_MISMATCH",
                                issue_description=f"Calculated W/B ratio ({calculated_wb:.2f}) ≠ Reported W/B ratio ({mix.w_b_ratio:.2f})"
                            )
                    
                    # Check if W/C ratio is outside sane range
                    if calculated_wc < self.threshold_wc_min or calculated_wc > self.threshold_wc_max:
                        wc_ratio_out_of_range_count += 1
                        self.flag_issue(
                            mix_code=mix.mix_code,
                            issue_code="WC_RATIO_RANGE",
                            issue_description=f"W/C ratio ({calculated_wc:.2f}) outside normal range ({self.threshold_wc_min}-{self.threshold_wc_max})"
                        )
            
            except Exception as e:
                # Log any calculation errors to help with debugging
                print(f"Error calculating ratios for mix {mix.mix_code}: {e}")
        
        print(f"Mixes with aggregate sum mismatches: {aggregate_mismatch_count}")
        print(f"Mixes with W/C ratio mismatches: {wc_ratio_mismatch_count}")
        print(f"Mixes with W/C ratio out of normal range: {wc_ratio_out_of_range_count}")
    
    def check_strength_sanity(self):
        """Check compressive strength for outliers"""
        print(f"\n3. Strength Sanity & Outliers\n{'-'*30}")
        
        # Get compressive strength statistics
        strength_stats = cdb.PerformanceResult.objects.using("cdb").filter(
            mix__dataset__dataset_name=self.dataset_code,
            category='hardened'  # Using category instead of test_method__method_name
        ).aggregate(
            count=Count('result_id'),
            avg=Avg('value_num'),
            min=Min('value_num'),
            max=Max('value_num')
        )
        
        print(f"Compressive strength statistics:")
        print(f"  Count: {strength_stats['count']}")
        
        # Check if there are any strength results before trying to print statistics
        if strength_stats['count'] > 0 and strength_stats['avg'] is not None:
            print(f"  Average: {strength_stats['avg']:.2f} MPa")
            print(f"  Min: {strength_stats['min']:.2f} MPa")
            print(f"  Max: {strength_stats['max']:.2f} MPa")
            
            # Flag outliers
            low_strength_mixes = cdb.PerformanceResult.objects.using("cdb").filter(
                mix__dataset__dataset_name=self.dataset_code,
                category='hardened',
                value_num__lt=self.threshold_strength_min
            )
            
            for result in low_strength_mixes:
                self.flag_issue(
                    mix_code=self.get_mix_code(result.mix_id),
                    issue_code="STRENGTH_LOW",
                    issue_description=f"Low compressive strength: {result.value_num} MPa < {self.threshold_strength_min} MPa"
                )
            
            print(f"Strength outliers: {low_strength_mixes.count()}")
        else:
            print("  No strength data available")
            print("Strength outliers: 0")
    
    def check_aggregate_details(self):
        """Check aggregate details for completeness and outliers"""
        print(f"\n4. Aggregate Detail Completeness\n{'-'*30}")
        
        # First, get all RCA and NCA materials used in this dataset
        rca_materials = cdb.Material.objects.using("cdb").filter(
            mix_usages__mix__dataset__dataset_name=self.dataset_code,
            subtype_code="RCA"
        ).distinct()
        
        nca_materials = cdb.Material.objects.using("cdb").filter(
            mix_usages__mix__dataset__dataset_name=self.dataset_code,
            material_class_id="AGGR_C"
        ).exclude(subtype_code="RCA").distinct()
        
        print(f"RCA materials: {rca_materials.count()}")
        print(f"NCA materials: {nca_materials.count()}")
        
        # Check RCA details
        rca_with_bulk_density = 0
        rca_with_upper_size = 0
        rca_with_absorption = 0
        
        rca_density_issues = 0
        rca_absorption_issues = 0
        
        for material in rca_materials:
            # Try to get aggregate detail for this material
            try:
                detail = cdb.AggregateDetail.objects.using("cdb").get(material=material)
                
                # Check which properties are set
                if detail.bulk_density_kg_m3 is not None:
                    rca_with_bulk_density += 1
                    # Check for outliers
                    if (detail.bulk_density_kg_m3 == 0 or 
                        detail.bulk_density_kg_m3 > self.threshold_density_max):
                        rca_density_issues += 1
                        # Get mixes using this material
                        mixes = cdb.MixComponent.objects.using("cdb").filter(
                            mix__dataset__dataset_name=self.dataset_code,
                            material=material
                        ).values_list('mix__mix_code', flat=True).distinct()
                        
                        for mix_code in mixes:
                            self.flag_issue(
                                mix_code=mix_code,
                                issue_code="RCA_DENSITY_ISSUE",
                                issue_description=f"RCA density {detail.bulk_density_kg_m3} kg/m³ {'= 0' if detail.bulk_density_kg_m3 == 0 else '> threshold'}"
                            )
                
                if detail.d_upper_mm is not None:
                    rca_with_upper_size += 1
                
                if detail.water_absorption_pct is not None:
                    rca_with_absorption += 1
                    # Check for outliers
                    if detail.water_absorption_pct > self.threshold_water_absorption_max:
                        rca_absorption_issues += 1
                        # Get mixes using this material
                        mixes = cdb.MixComponent.objects.using("cdb").filter(
                            mix__dataset__dataset_name=self.dataset_code,
                            material=material
                        ).values_list('mix__mix_code', flat=True).distinct()
                        
                        for mix_code in mixes:
                            self.flag_issue(
                                mix_code=mix_code,
                                issue_code="RCA_ABSORPTION_ISSUE",
                                issue_description=f"RCA water absorption {detail.water_absorption_pct}% > threshold"
                            )
            except cdb.AggregateDetail.DoesNotExist:
                pass
        
        # Check NCA details
        nca_with_bulk_density = 0
        nca_with_upper_size = 0
        nca_with_absorption = 0
        
        nca_density_issues = 0
        nca_absorption_issues = 0
        
        for material in nca_materials:
            # Try to get aggregate detail for this material
            try:
                detail = cdb.AggregateDetail.objects.using("cdb").get(material=material)
                
                # Check which properties are set
                if detail.bulk_density_kg_m3 is not None:
                    nca_with_bulk_density += 1
                    # Check for outliers
                    if (detail.bulk_density_kg_m3 == 0 or 
                        detail.bulk_density_kg_m3 > self.threshold_density_max):
                        nca_density_issues += 1
                        # Get mixes using this material
                        mixes = cdb.MixComponent.objects.using("cdb").filter(
                            mix__dataset__dataset_name=self.dataset_code,
                            material=material
                        ).values_list('mix__mix_code', flat=True).distinct()
                        
                        for mix_code in mixes:
                            self.flag_issue(
                                mix_code=mix_code,
                                issue_code="NCA_DENSITY_ISSUE",
                                issue_description=f"NCA density {detail.bulk_density_kg_m3} kg/m³ {'= 0' if detail.bulk_density_kg_m3 == 0 else '> threshold'}"
                            )
                
                if detail.d_upper_mm is not None:
                    nca_with_upper_size += 1
                
                if detail.water_absorption_pct is not None:
                    nca_with_absorption += 1
                    # Check for outliers
                    if detail.water_absorption_pct > self.threshold_water_absorption_max:
                        nca_absorption_issues += 1
                        # Get mixes using this material
                        mixes = cdb.MixComponent.objects.using("cdb").filter(
                            mix__dataset__dataset_name=self.dataset_code,
                            material=material
                        ).values_list('mix__mix_code', flat=True).distinct()
                        
                        for mix_code in mixes:
                            self.flag_issue(
                                mix_code=mix_code,
                                issue_code="NCA_ABSORPTION_ISSUE",
                                issue_description=f"NCA water absorption {detail.water_absorption_pct}% > threshold"
                            )
            except cdb.AggregateDetail.DoesNotExist:
                pass
        
        # Print summary
        print(f"RCA materials with bulk density: {rca_with_bulk_density}/{rca_materials.count()}")
        print(f"RCA materials with upper size: {rca_with_upper_size}/{rca_materials.count()}")
        print(f"RCA materials with water absorption: {rca_with_absorption}/{rca_materials.count()}")
        print(f"RCA materials with density issues: {rca_density_issues}")
        print(f"RCA materials with absorption issues: {rca_absorption_issues}")
        
        print(f"NCA materials with bulk density: {nca_with_bulk_density}/{nca_materials.count()}")
        print(f"NCA materials with upper size: {nca_with_upper_size}/{nca_materials.count()}")
        print(f"NCA materials with water absorption: {nca_with_absorption}/{nca_materials.count()}")
        print(f"NCA materials with density issues: {nca_density_issues}")
        print(f"NCA materials with absorption issues: {nca_absorption_issues}")
    
    def check_reference_coverage(self):
        """Check reference coverage - which references are most used"""
        print(f"\n5. Reference Coverage\n{'-'*30}")
        
        # Get top 10 references by usage count
        # Using raw SQL since the model uses composite primary key
        with django.db.connections['cdb'].cursor() as cursor:
            cursor.execute("""
                SELECT r.reference_id, r.citation_text, COUNT(mr.mix_id) as mix_count
                FROM bibliographic_reference r
                JOIN concrete_mix_reference mr ON r.reference_id = mr.reference_id
                JOIN concrete_mix m ON m.mix_id = mr.mix_id
                JOIN dataset d ON m.dataset_id = d.dataset_id
                WHERE d.dataset_name = %s
                GROUP BY r.reference_id, r.citation_text
                ORDER BY mix_count DESC
                LIMIT 10
            """, [self.dataset_code])
            top_references = cursor.fetchall()
        
        print(f"Top 10 references by usage:")
        for ref_id, citation, count in top_references:
            # Truncate long citations
            citation_short = (citation[:60] + '...') if len(citation) > 60 else citation
            print(f"  ID {ref_id}: {citation_short} - {count} mixes")
    
    def check_specimen_sanity(self):
        """Check specimen dimensions for outliers and summarize shapes"""
        print(f"\n6. Specimen Sanity\n{'-'*30}")
        
        # Get unique shapes and dimension pairs with counts
        specimen_stats = cdb.Specimen.objects.using("cdb").filter(
            mix__dataset__dataset_name=self.dataset_code
        ).values(
            'shape', 'nominal_diameter_mm', 'nominal_length_mm'
        ).annotate(count=Count('specimen_id')).order_by('-count')
        
        print(f"Unique specimen shapes and dimensions:")
        for stat in specimen_stats:
            print(f"  {stat['shape']} {stat['nominal_diameter_mm']}×{stat['nominal_length_mm']} mm: {stat['count']} specimens")
        
        # Check for outlier dimensions
        specimens_with_issues = cdb.Specimen.objects.using("cdb").filter(
            mix__dataset__dataset_name=self.dataset_code
        ).filter(
            Q(nominal_diameter_mm__lt=self.threshold_diameter_min) | 
            Q(nominal_diameter_mm__gt=self.threshold_diameter_max)
        )
        
        print(f"Specimens with dimension issues: {specimens_with_issues.count()}")
        
        for specimen in specimens_with_issues:
            issue_desc = "diameter too small" if specimen.nominal_diameter_mm < self.threshold_diameter_min else "diameter too large"
            self.flag_issue(
                mix_code=specimen.mix.mix_code,
                issue_code="SPECIMEN_DIMENSION",
                issue_description=f"{specimen.shape} specimen {issue_desc}: {specimen.nominal_diameter_mm} mm"
            )
    
    def print_summary(self):
        """Print a summary of all issues found"""
        print(f"\n\nSummary of Issues\n{'-'*30}")
        
        # Group issues by code
        issue_counts = collections.Counter([issue['issue_code'] for issue in self.issues])
        mix_count = len(set([issue['mix_code'] for issue in self.issues]))
        
        print(f"Total mixes with issues: {mix_count}")
        print(f"Total issues found: {len(self.issues)}")
        print(f"\nIssues by type:")
        for code, count in issue_counts.most_common():
            print(f"  {code}: {count}")
    
    def run_all_checks(self):
        """Run all health checks"""
        print(f"Running health checks for dataset {self.dataset_code}...\n")
        
        self.check_high_level_counts()
        self.check_component_sanity()
        self.check_strength_sanity()
        self.check_aggregate_details()
        self.check_reference_coverage()
        self.check_specimen_sanity()
        
        self.print_summary()
        self.save_issues_to_csv()

# Main function to run health checks
def main():
    if len(sys.argv) < 2:
        print("Usage: python ds_verification.py <dataset_code>")
        print("Example: python ds_verification.py DS2")
        sys.exit(1)
    
    dataset_code = sys.argv[1]
    checker = HealthCheck(dataset_code)
    checker.run_all_checks()

if __name__ == "__main__":
    main()
