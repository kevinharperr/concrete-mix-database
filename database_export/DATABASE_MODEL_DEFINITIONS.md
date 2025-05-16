# Concrete Mix Database: Model Definitions

This document provides a comprehensive overview of the Django models that define the Concrete Mix Database schema. These model definitions illustrate the relationships between tables and the fields available for analysis.

## Table of Contents

1. [Lookup Tables](#lookup-tables)
   - [UnitLookup](#unitlookup)
   - [PropertyDictionary](#propertydictionary)
   - [MaterialClass](#materialclass)
   - [Standard](#standard)
   - [TestMethod](#testmethod)
   - [CuringRegime](#curingregime)
   - [Dataset](#dataset)

2. [Core Data Tables](#core-data-tables)
   - [BibliographicReference](#bibliographicreference)
   - [Material](#material)
   - [ConcreteMix](#concretemix)
   - [ConcreteMixReference](#concretemixreference)
   - [MixComponent](#mixcomponent)
   - [Specimen](#specimen)
   - [PerformanceResult](#performanceresult)
   - [SustainabilityMetric](#sustainabilitymetric)
   - [MaterialProperty](#materialproperty)

3. [Material Detail Tables](#material-detail-tables)
   - [CementDetail](#cementdetail)
   - [ScmDetail](#scmdetail)
   - [AggregateDetail](#aggregatedetail)
   - [AggregateConstituent](#aggregateconstituent)
   - [AdmixtureDetail](#admixturedetail)
   - [FibreDetail](#fibredetail)

4. [Utility Tables](#utility-tables)
   - [ColumnMap](#columnmap)

5. [ER Diagram](#er-diagram)

---

## Lookup Tables

### UnitLookup

```python
class UnitLookup(models.Model):
    """Stores units and their conversion factors to a base SI unit."""
    unit_id = models.AutoField(primary_key=True)
    unit_symbol = models.CharField(max_length=20, unique=True, help_text="e.g., kg/m³, MPa, %")
    si_factor = models.DecimalField(max_digits=15, decimal_places=9, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
```

**Purpose**: Stores measurement units and their conversion factors to base SI units. Used throughout the database to ensure consistent unit handling.

---

### PropertyDictionary

```python
class PropertyDictionary(models.Model):
    """Authoritative list of material properties."""
    # Property groups
    CHEMICAL = "chemical"
    PHYSICAL = "physical"
    MECHANICAL = "mechanical"
    THERMAL = "thermal"
    GROUP_CHOICES = [...]

    property_name = models.CharField(max_length=60, primary_key=True)
    display_name = models.CharField(max_length=120)
    property_group = models.CharField(max_length=30, choices=GROUP_CHOICES)
    default_unit = models.ForeignKey(UnitLookup, null=True, blank=True, on_delete=models.SET_NULL)
```

**Purpose**: Central repository of all material properties. Categorizes properties and links them to appropriate default units.

---

### MaterialClass

```python
class MaterialClass(models.Model):
    """High-level classification of materials (cement, scm, aggregate, etc.)."""
    class_code = models.CharField(max_length=8, primary_key=True)
    class_name = models.CharField(max_length=60, blank=True, null=True)
```

**Purpose**: High-level classification system for materials (e.g., CEMENT, SCM, AGGR_C, AGGR_F).

---

### Standard

```python
class Standard(models.Model):
    """Reference standards (e.g., EN 197-1)."""
    standard_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=30, unique=True)
    title = models.TextField(blank=True, null=True)
```

**Purpose**: Defines industry standards like EN 197-1 or ASTM C150 that are referenced by materials or tests.

---

### TestMethod

```python
class TestMethod(models.Model):
    """Specific test methods, potentially linked to standards."""
    test_method_id = models.AutoField(primary_key=True)
    standard = models.ForeignKey(Standard, null=True, blank=True, on_delete=models.SET_NULL)
    clause = models.CharField(max_length=30, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
```

**Purpose**: Documents testing methodologies, typically linked to a specific industry standard.

---

### CuringRegime

```python
class CuringRegime(models.Model):
    """Defines curing conditions."""
    curing_regime_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=100, blank=True, null=True) 
```

**Purpose**: Defines the conditions under which concrete specimens were cured (e.g., "Water bath 20C", "Sealed 23C 50%RH").

---

### Dataset

```python
class Dataset(models.Model):
    """Information about the source datasets."""
    dataset_id = models.AutoField(primary_key=True)
    dataset_name = models.CharField(max_length=60, unique=True)
    license = models.TextField(blank=True, null=True)
```

**Purpose**: Tracks the origin of data, with each dataset having a unique identifier (e.g., DS1, DS2).

---

## Core Data Tables

### BibliographicReference

```python
class BibliographicReference(models.Model):
    """Bibliographic details for sources."""
    reference_id = models.AutoField(primary_key=True)
    author = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    publication = models.TextField(blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    doi = models.CharField(max_length=100, blank=True, null=True)
    citation_text = models.TextField(blank=True, null=True)
```

**Purpose**: References to research papers, reports, or other publications that are the source of concrete mix data.

---

### Material

```python
class Material(models.Model):
    """Core material information."""
    material_id = models.AutoField(primary_key=True)
    material_class = models.ForeignKey(MaterialClass, db_column="class_code", on_delete=models.RESTRICT)
    subtype_code = models.CharField(max_length=60, blank=True, null=True, db_index=True)
    specific_name = models.TextField(blank=True, null=True)
    manufacturer = models.TextField(blank=True, null=True)
    standard = models.ForeignKey(Standard, db_column="standard_ref", blank=True, null=True, on_delete=models.SET_NULL)
    country_of_origin = models.CharField(max_length=60, blank=True, null=True)
    date_added = models.DateField(null=True, blank=True, auto_now_add=True)
    source_dataset = models.CharField(max_length=50, blank=True, null=True, db_index=True)
```

**Purpose**: Central table for all concrete constituent materials, linking to more specific detail tables based on material type.

---

### ConcreteMix

```python
class ConcreteMix(models.Model):
    """Represents a single concrete mix design."""
    mix_id = models.AutoField(primary_key=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.PROTECT)
    mix_code = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    date_created = models.DateField(blank=True, null=True)
    region_country = models.CharField(max_length=60, blank=True, null=True)
    strength_class = models.CharField(max_length=10, blank=True, null=True)
    target_slump_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    w_c_ratio = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    w_b_ratio = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    wb_k_reported = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    k_flag = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    references = models.ManyToManyField(BibliographicReference, through='ConcreteMixReference')
```

**Purpose**: The central table representing concrete mix designs. Links to components, specimens, and test results.

**Note on w/b Ratios**: The database stores multiple types of water-binder ratios:
- `w_c_ratio`: Water-to-cement ratio (water divided by cement content only)
- `w_b_ratio`: Water-to-binder ratio (water divided by cement + all reactive SCMs)
- `wb_k_reported`: Water-to-binder ratio with k-value concept applied (typically following DIN 1045-2)

---

### ConcreteMixReference

```python
class ConcreteMixReference(models.Model):
    """Junction table for the many-to-many relationship between mixes and references."""
    mix = models.ForeignKey(ConcreteMix, on_delete=models.CASCADE)
    reference = models.ForeignKey(BibliographicReference, on_delete=models.CASCADE)
```

**Purpose**: Junction table linking concrete mixes to their bibliographic references.

---

### MixComponent

```python
class MixComponent(models.Model):
    """Links materials to a concrete mix with dosage."""
    component_id = models.AutoField(primary_key=True)
    mix = models.ForeignKey(ConcreteMix, on_delete=models.CASCADE, related_name="components")
    material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name="mix_usages")
    dosage_kg_m3 = models.DecimalField(max_digits=10, decimal_places=3)
    is_cementitious = models.BooleanField(null=True, blank=True) 
```

**Purpose**: Links materials to concrete mixes with specific dosages. The `is_cementitious` flag is crucial for w/b ratio calculations.

---

### Specimen

```python
class Specimen(models.Model):
    """Details of test specimens."""
    specimen_id = models.AutoField(primary_key=True)
    mix = models.ForeignKey(ConcreteMix, on_delete=models.CASCADE, related_name="specimens")
    shape = models.CharField(max_length=20, blank=True, null=True)
    nominal_length_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    nominal_diameter_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
```

**Purpose**: Defines test specimens created from concrete mixes, including their shape and dimensions.

---

### PerformanceResult

```python
class PerformanceResult(models.Model):
    """Stores results from various performance tests."""
    FRESH = 'fresh'
    HARDENED = 'hardened'
    DURABILITY = 'durability'
    CATEGORY_CHOICES = [...]

    result_id = models.AutoField(primary_key=True)
    mix = models.ForeignKey(ConcreteMix, on_delete=models.CASCADE, related_name="performance_results")
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, db_index=True)
    test_method = models.ForeignKey(TestMethod, null=True, blank=True, on_delete=models.SET_NULL)
    age_days = models.IntegerField(null=True, blank=True, db_index=True)
    value_num = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    unit = models.ForeignKey(UnitLookup, null=True, blank=True, on_delete=models.SET_NULL)
    specimen = models.ForeignKey(Specimen, null=True, blank=True, on_delete=models.SET_NULL)
    curing_regime = models.ForeignKey(CuringRegime, null=True, blank=True, on_delete=models.SET_NULL)
    test_conditions = models.TextField(blank=True, null=True)
```

**Purpose**: Stores test results for concrete mixes, categorized by fresh properties (e.g., slump), hardened properties (e.g., compressive strength), and durability properties.

---

### SustainabilityMetric

```python
class SustainabilityMetric(models.Model):
    """Stores sustainability metrics for a mix."""
    metric_id = models.AutoField(primary_key=True)
    mix = models.ForeignKey(ConcreteMix, on_delete=models.CASCADE, related_name="sustainability_metrics")
    metric_code = models.CharField(max_length=15, blank=True, null=True)
    value_num = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    unit = models.ForeignKey(UnitLookup, null=True, blank=True, on_delete=models.SET_NULL)
    method_ref = models.CharField(max_length=30, blank=True, null=True)
```

**Purpose**: Tracks environmental impact metrics for concrete mixes, such as Global Warming Potential (GWP) or Embodied Energy.

---

### MaterialProperty

```python
class MaterialProperty(models.Model):
    """Stores specific properties of materials."""
    property_id = models.AutoField(primary_key=True)
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="properties")
    property_name = models.ForeignKey(PropertyDictionary, db_column="property_name", on_delete=models.RESTRICT)
    value_num = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    unit = models.ForeignKey(UnitLookup, null=True, blank=True, on_delete=models.SET_NULL)
    test_method = models.ForeignKey(TestMethod, null=True, blank=True, on_delete=models.SET_NULL)
    test_date = models.DateField(null=True, blank=True)
```

**Purpose**: Records specific properties of materials, such as chemical composition, physical properties, and mechanical properties.

---

## Material Detail Tables

### CementDetail

```python
class CementDetail(models.Model):
    """Details specific to cement materials."""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, primary_key=True, related_name="cement_detail")
    strength_class = models.CharField(max_length=10, blank=True, null=True)
    clinker_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
```

**Purpose**: Extends the Material model with cement-specific properties.

---

### ScmDetail

```python
class ScmDetail(models.Model):
    """Details specific to SCM materials."""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, primary_key=True, related_name="scm_detail")
    scm_type_code = models.CharField(max_length=20, blank=True, null=True)
    loi_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
```

**Purpose**: Extends the Material model with supplementary cementitious material (SCM) properties.

---

### AggregateDetail

```python
class AggregateDetail(models.Model):
    """Details specific to aggregate materials."""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, primary_key=True, related_name="aggregate_detail")
    d_lower_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    d_upper_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    bulk_density_kg_m3 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    water_absorption_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    fineness_modulus = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
```

**Purpose**: Extends the Material model with aggregate-specific properties, including size range and physical characteristics.

---

### AggregateConstituent

```python
class AggregateConstituent(models.Model):
    """Constituent percentages for recycled/mixed aggregates (EN 12620)."""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, primary_key=True, related_name="aggregate_constituent")
    rc_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True) # Recycled Concrete
    ru_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True) # Unbound Aggregate
    ra_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True) # Bituminous Asphalt
    rb_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True) # Brick
    fl_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True) # Floating Lightweight
    x_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True) # Other (Glass, etc.)
    rg_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True) # Glass
```

**Purpose**: Specifically for recycled aggregates, tracks the percentages of different source materials according to EN 12620 standards.

---

### AdmixtureDetail

```python
class AdmixtureDetail(models.Model):
    """Details specific to admixture materials."""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, primary_key=True, related_name="admixture_detail")
    solid_content_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    specific_gravity = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    chloride_content_pct = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
```

**Purpose**: Extends the Material model with admixture-specific properties like solid content and chloride content.

---

### FibreDetail

```python
class FibreDetail(models.Model):
    """Details specific to fibre materials."""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, primary_key=True, related_name="fibre_detail")
    length_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    diameter_mm = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    aspect_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tensile_strength_mpa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
```

**Purpose**: Extends the Material model with fibre-specific properties such as dimensions and tensile strength.

---

## Utility Tables

### ColumnMap

```python
class ColumnMap(models.Model):
    """Maps source CSV columns to target database tables/columns for ETL."""
    map_id = models.AutoField(primary_key=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    source_column = models.CharField(max_length=128)
    target_table = models.CharField(max_length=64, blank=True, null=True)
    target_column = models.CharField(max_length=64, blank=True, null=True)
    unit_hint = models.CharField(max_length=20, blank=True, null=True)
    needs_conversion = models.BooleanField(null=True, blank=True)
```

**Purpose**: Supports the ETL (Extract, Transform, Load) process by mapping source dataset columns to the appropriate database tables and columns.

---

## Key Relationships

### Primary Model Relationships

1. **ConcreteMix → MixComponent → Material**
   - A concrete mix has multiple components
   - Each component references a specific material
   - Materials have a material class (e.g., CEMENT, SCM)

2. **ConcreteMix → PerformanceResult**
   - A mix has multiple performance test results
   - Results are categorized (fresh, hardened, durability)
   - Results may reference a specimen and curing regime

3. **Material → MaterialProperty**
   - Materials have multiple properties
   - Properties are defined in the PropertyDictionary
   - Properties may have units and test methods

4. **Material → Detail Tables**
   - Materials may have specialized details based on their class
   - One-to-one relationships to detail tables like CementDetail, ScmDetail, etc.

## Common Query Patterns

1. **Finding Mix Components and Water-Binder Ratio**:
   ```python
   # Get a concrete mix by ID
   mix = ConcreteMix.objects.get(pk=mix_id)
   
   # Get all components of the mix
   components = mix.components.all().select_related('material')
   
   # Examine w/b ratio
   print(f"W/B Ratio: {mix.w_b_ratio}")
   ```

2. **Finding Strength Test Results**:
   ```python
   # Get strength test results for a mix
   results = PerformanceResult.objects.filter(
       mix_id=mix_id,
       category='hardened',
       test_method__description__contains='compressive strength'
   )
   ```

3. **Material Properties Query**:
   ```python
   # Get all chemical properties for a material
   properties = MaterialProperty.objects.filter(
       material_id=material_id,
       property_name__property_group='chemical'
   ).select_related('property_name', 'unit')
   ```

## Notes on Water-Binder Ratio Calculations

The water-binder ratio is calculated using the formula:

```
w/b = Water / (Cement + ALL SCMs)
```

Where:
- Water is the total water content in kg/m³
- Cement is the cement content in kg/m³
- SCMs are supplementary cementitious materials in kg/m³

The `MixComponent.is_cementitious` flag is used to identify which components should be counted in the denominator for this calculation.

---

## Database Issues and Known Limitations

1. **DS2 Dataset Issues**: 
   - Mix codes in the DS2 dataset (dataset_id=9) do not consistently match the original dataset row numbers.
   - Many mixes are missing essential components like aggregates.
   - There are systematic import errors (e.g., data from mix #979 imported into a mix coded as DS2-734).

2. **High Water-Binder Ratios**:
   - Some mixes show abnormally high w/b ratios (>0.7).
   - These are primarily due to import errors rather than calculation issues.
   - The formula for w/b ratio calculation is correct but works with incorrect data in some cases.

3. **Material Classification**:
   - Some materials like 'CFA' (Coal Fly Ash) were not consistently recognized as cementitious.
   - Updates to the `is_cementitious` flags have been made but data consistency requires further verification.

---

## Recommended Analysis Approach

When analyzing this database, consider the following approach:

1. **Filter by Dataset**: Some datasets have higher data quality than others. Consider excluding problematic datasets like DS2 for critical analyses.

2. **Verify Components**: For any mix being analyzed, first verify that it has a complete set of components (cement, water, aggregates).

3. **Check Reasonable Ranges**: Apply validation rules to filter out mixes with unreasonable parameter values (e.g., w/b ratio > 0.7).

4. **Age-Specific Analysis**: When analyzing strength results, be aware that tests may have been conducted at different ages (not just the standard 28 days).

---

## Query Examples for Common Analysis Tasks

### Example 1: Finding Mixes with Specific SCM Types

```sql
SELECT cm.mix_id, cm.mix_code, m.specific_name, mc.dosage_kg_m3
FROM concrete_mix cm
JOIN mix_component mc ON cm.mix_id = mc.mix_id
JOIN material m ON mc.material_id = m.material_id
JOIN material_class mc2 ON m.class_code = mc2.class_code
WHERE mc2.class_code = 'SCM' AND m.subtype_code LIKE '%fly%ash%';
```

### Example 2: Analyzing Strength Development Over Time

```sql
SELECT cm.mix_id, cm.mix_code, pr.age_days, pr.value_num, u.unit_symbol
FROM concrete_mix cm
JOIN performance_result pr ON cm.mix_id = pr.mix_id
JOIN unit_lookup u ON pr.unit_id = u.unit_id
JOIN test_method tm ON pr.test_method_id = tm.test_method_id
WHERE tm.description LIKE '%compressive%strength%'
ORDER BY cm.mix_id, pr.age_days;
```

### Example 3: Calculating Average w/b Ratio by Strength Class

```sql
SELECT strength_class, AVG(w_b_ratio) as avg_wb, COUNT(*) as count
FROM concrete_mix
WHERE strength_class IS NOT NULL AND w_b_ratio BETWEEN 0.2 AND 0.7
GROUP BY strength_class
ORDER BY avg_wb;
```

---

## Using Pandas for Analysis

Pandas provides a powerful way to analyze this database. Here's an example of loading and analyzing mix data:

```python
import pandas as pd
import psycopg2
import matplotlib.pyplot as plt

# Connect to the database
conn = psycopg2.connect(
    dbname="cdb",
    user="postgres",
    password="your_password",
    host="localhost"
)

# Query mix data with w/b ratios
query = """
SELECT 
    cm.mix_id, cm.mix_code, cm.w_b_ratio, cm.strength_class,
    ds.dataset_name
FROM 
    concrete_mix cm
JOIN
    dataset ds ON cm.dataset_id = ds.dataset_id
WHERE
    cm.w_b_ratio IS NOT NULL
ORDER BY
    cm.mix_id
"""

# Load into DataFrame
mixes_df = pd.read_sql(query, conn)

# Basic analysis
print(f"Total mixes with w/b data: {len(mixes_df)}")

# Summary statistics by dataset
pivot = mixes_df.pivot_table(
    values='w_b_ratio',
    index='dataset_name',
    aggfunc=['mean', 'std', 'min', 'max', 'count']
)

print("\nW/B Ratio Statistics by Dataset:")
print(pivot)

# Plot histogram of w/b ratios
plt.figure(figsize=(10, 6))
mixes_df['w_b_ratio'].hist(bins=20)
plt.title('Distribution of Water-Binder Ratios')
plt.xlabel('Water-Binder Ratio')
plt.ylabel('Frequency')
plt.grid(False)
plt.show()
```

---

## Further Documentation

For more detailed information on database issues and the refresh plan, please refer to:

1. [DATABASE_REFRESH_PLAN.md](./DATABASE_REFRESH_PLAN.md) - Comprehensive plan for refreshing the database
2. [LESSONS_LEARNED.md](./LESSONS_LEARNED.md) - Key insights and challenges from the project

---

*This document was generated on May 15, 2025, as part of the Concrete Mix Database sharing package.*
