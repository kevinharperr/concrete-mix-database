# cdb_app/models.py
# Django models based on the refined schema in @cdb_database_dictionary.md

from django.db import models
# from django.contrib.auth.models import User # Import if needed for created_by fields later

# --- Lookup Tables ---

class UnitLookup(models.Model):
    """Stores units and their conversion factors to a base SI unit."""
    unit_id = models.AutoField(primary_key=True) # AutoField for integer PK
    unit_symbol = models.CharField(max_length=20, unique=True, help_text="e.g., kg/m³, MPa, %")
    si_factor = models.DecimalField(max_digits=15, decimal_places=9, null=True, blank=True, help_text="Factor to multiply by to get base SI unit (if applicable)")
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "unit_lookup"
        verbose_name = "Unit"
        verbose_name_plural = "Units"

    def __str__(self):
        return self.unit_symbol

class PropertyDictionary(models.Model):
    """Authoritative list of material properties."""
    CHEMICAL = "chemical"
    PHYSICAL = "physical"
    MECHANICAL = "mechanical" # Added example group
    THERMAL = "thermal" # Added example group
    GROUP_CHOICES = [
        (CHEMICAL, "Chemical Composition"),
        (PHYSICAL, "Physical Properties"),
        (MECHANICAL, "Mechanical Properties"),
        (THERMAL, "Thermal Properties"),
        # Add more relevant groups
    ]

    property_name = models.CharField(max_length=60, primary_key=True, help_text="Unique code/key for the property, e.g., 'cao_pct'")
    display_name = models.CharField(max_length=120, help_text="User-friendly name, e.g., 'CaO (%)'")
    property_group = models.CharField(max_length=30, choices=GROUP_CHOICES, help_text="Category of the property")
    default_unit = models.ForeignKey(UnitLookup, null=True, blank=True, on_delete=models.SET_NULL, related_name='+') # Use '+' for related_name if no reverse lookup needed

    class Meta:
        db_table = "property_dictionary"
        verbose_name = "Property Definition"
        verbose_name_plural = "Property Dictionary"

    def __str__(self):
        return self.display_name

class MaterialClass(models.Model):
    """High-level classification of materials (cement, scm, aggregate, etc.)."""
    class_code = models.CharField(max_length=8, primary_key=True, help_text="e.g., CEMENT, SCM, AGGR_C, AGGR_F")
    class_name = models.CharField(max_length=60, blank=True, null=True)

    class Meta:
        db_table = "material_class"
        verbose_name = "Material Class"
        verbose_name_plural = "Material Classes"

    def __str__(self):
        return self.class_name or self.class_code

class Standard(models.Model):
    """Reference standards (e.g., EN 197-1)."""
    standard_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=30, unique=True, help_text="e.g., EN 197-1, ASTM C150")
    title = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "standard"
        verbose_name = "Standard"
        verbose_name_plural = "Standards"

    def __str__(self):
        return self.code

class TestMethod(models.Model):
    """Specific test methods, potentially linked to standards."""
    test_method_id = models.AutoField(primary_key=True)
    standard = models.ForeignKey(Standard, null=True, blank=True, on_delete=models.SET_NULL)
    clause = models.CharField(max_length=30, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "test_method"
        verbose_name = "Test Method"
        verbose_name_plural = "Test Methods"

    def __str__(self):
        return f"{self.standard.code if self.standard else 'Custom'} - {self.description or 'Unnamed Method'}"[:80]

class CuringRegime(models.Model):
    """Defines curing conditions."""
    curing_regime_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Water bath 20C, Sealed 23C 50%RH")

    class Meta:
        db_table = "curing_regime"
        verbose_name = "Curing Regime"
        verbose_name_plural = "Curing Regimes"

    def __str__(self):
        return self.description or f"Regime {self.curing_regime_id}"

class Dataset(models.Model):
    """Information about the source datasets."""
    dataset_id = models.AutoField(primary_key=True)
    dataset_name = models.CharField(max_length=60, unique=True, help_text="e.g., DS1, DS6")
    license = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "dataset"
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"

    def __str__(self):
        return self.dataset_name

# --- Core Data Tables ---

class BibliographicReference(models.Model):
    """Bibliographic details for sources."""
    reference_id = models.AutoField(primary_key=True)
    author = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    publication = models.TextField(blank=True, null=True) # Changed from CharField
    year = models.IntegerField(blank=True, null=True)
    doi = models.CharField(max_length=100, blank=True, null=True)
    citation_text = models.TextField(blank=True, null=True, help_text="Original citation string if available")

    class Meta:
        db_table = "bibliographic_reference"
        verbose_name = "Bibliographic Reference"
        verbose_name_plural = "Bibliographic References"

    def __str__(self):
        return f"{self.author or 'Unknown'} ({self.year or 'N/A'})"[:80]

class Material(models.Model):
    """Core material information."""
    material_id = models.AutoField(primary_key=True) # Use AutoField or BigAutoField
    material_class = models.ForeignKey(
        MaterialClass,
        db_column="class_code",
        on_delete=models.RESTRICT, # Prevent deleting a class if materials use it
        related_name="materials",
        help_text="High-level material classification"
    )
    subtype_code = models.CharField(max_length=60, blank=True, null=True, db_index=True, help_text="Specific type within class, e.g., CEM I, Fly Ash Class F, ground_granulated_blast_furnace_slag")
    # Renamed brand_name to specific_name for broader use
    specific_name = models.TextField(blank=True, null=True, help_text="Most specific name from source, e.g., CEM I 52.5 R, OPC-32.5, Tap Water")
    manufacturer = models.TextField(blank=True, null=True)
    standard = models.ForeignKey(Standard, db_column="standard_ref", blank=True, null=True, on_delete=models.SET_NULL, related_name="materials") # Link to Standard table
    country_of_origin = models.CharField(max_length=60, blank=True, null=True)
    date_added = models.DateField(null=True, blank=True, auto_now_add=True) # Use auto_now_add?
    source_dataset = models.CharField(max_length=50, blank=True, null=True, db_index=True, help_text="Original dataset identifier (e.g., DS1, DS6)")

    class Meta:
        db_table = "material"
        verbose_name = "Material"
        verbose_name_plural = "Materials"
        indexes = [
            models.Index(fields=['material_class', 'subtype_code']),
        ]

    def __str__(self):
        return f"{self.specific_name or self.subtype_code or self.material_class.class_code} (ID: {self.material_id})"

class ConcreteMix(models.Model):
    """Represents a single concrete mix design."""
    mix_id = models.AutoField(primary_key=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.PROTECT, related_name="concrete_mixes") # Should not be nullable
    mix_code = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    date_created = models.DateField(blank=True, null=True)
    region_country = models.CharField(max_length=60, blank=True, null=True)
    strength_class = models.CharField(max_length=10, blank=True, null=True, help_text="e.g., C30/37")
    target_slump_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    w_c_ratio = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True, help_text="Water/(Cement) ratio")
    w_b_ratio = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True, help_text="Water/(Binder=Cement+SCM) ratio")
    wb_k_reported = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True, help_text="Water/Binder ratio with k-value consideration (DIN 1045-2)")
    k_flag = models.BooleanField(default=False, help_text="Indicates if the w/b ratio considers k-value concept for SCMs")
    notes = models.TextField(blank=True, null=True)
    references = models.ManyToManyField(
        BibliographicReference,
        through='ConcreteMixReference', # Explicitly define the through table
        related_name='concrete_mixes'
    )

    class Meta:
        db_table = "concrete_mix"
        verbose_name = "Concrete Mix"
        verbose_name_plural = "Concrete Mixes"

    def __str__(self):
        return self.mix_code or f"Mix ID {self.mix_id}"

class ConcreteMixReference(models.Model):
    """Junction table for the many-to-many relationship between mixes and references."""
    mix = models.ForeignKey(ConcreteMix, on_delete=models.CASCADE)
    reference = models.ForeignKey(BibliographicReference, on_delete=models.CASCADE)

    class Meta:
        db_table = "concrete_mix_reference"
        unique_together = ('mix', 'reference') # Prevent duplicate links
        verbose_name = "Mix Reference Link"
        verbose_name_plural = "Mix Reference Links"

    def __str__(self):
        return f"Mix {self.mix_id} -> Ref {self.reference_id}"

class MixComponent(models.Model):
    """Links materials to a concrete mix with dosage."""
    component_id = models.AutoField(primary_key=True)
    mix = models.ForeignKey(ConcreteMix, on_delete=models.CASCADE, related_name="components") # Cascade delete if mix is deleted
    material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name="mix_usages") # Protect material from deletion if used in mix
    dosage_kg_m3 = models.DecimalField(max_digits=10, decimal_places=3, help_text="Dosage in kg per cubic meter") # Changed from Numeric to Decimal
    # Removed calculated fields like pct_binder, replacement_pct
    is_cementitious = models.BooleanField(null=True, blank=True, help_text="Flag if this component counts towards binder content (for W/B calc)")

    class Meta:
        db_table = "mix_component"
        unique_together = ('mix', 'material') # Usually one material per mix
        verbose_name = "Mix Component"
        verbose_name_plural = "Mix Components"

    def __str__(self):
        return f"{self.material} in Mix {self.mix_id}"

class Specimen(models.Model):
    """Details of test specimens."""
    specimen_id = models.AutoField(primary_key=True)
    # Added ForeignKey to ConcreteMix
    mix = models.ForeignKey(ConcreteMix, on_delete=models.CASCADE, related_name="specimens") # Specimen belongs to a mix
    shape = models.CharField(max_length=20, blank=True, null=True, help_text="e.g., Cube, Cylinder, Prism")
    nominal_length_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    nominal_diameter_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "specimen"
        verbose_name = "Specimen"
        verbose_name_plural = "Specimens"

    def __str__(self):
        dims = []
        if self.nominal_diameter_mm:
            dims.append(f"d{self.nominal_diameter_mm}")
        if self.nominal_length_mm:
            dims.append(f"l{self.nominal_length_mm}")
        dim_str = "x".join(dims) or "Unknown Dims"
        return f"{self.shape or 'Shape?'} ({dim_str}) for Mix {self.mix_id}"

class PerformanceResult(models.Model):
    """Stores results from various performance tests."""
    FRESH = 'fresh'
    HARDENED = 'hardened'
    DURABILITY = 'durability'
    CATEGORY_CHOICES = [
        (FRESH, 'Fresh Concrete Properties'),
        (HARDENED, 'Hardened Concrete Properties'),
        (DURABILITY, 'Durability Properties'),
    ]

    result_id = models.AutoField(primary_key=True)
    mix = models.ForeignKey(ConcreteMix, on_delete=models.CASCADE, related_name="performance_results") # Result belongs to a mix
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, db_index=True)
    test_method = models.ForeignKey(TestMethod, null=True, blank=True, on_delete=models.SET_NULL) # Changed from IntegerField
    age_days = models.IntegerField(null=True, blank=True, db_index=True)
    value_num = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True) # Changed from Numeric
    unit = models.ForeignKey(UnitLookup, null=True, blank=True, on_delete=models.SET_NULL) # Changed from IntegerField
    specimen = models.ForeignKey(Specimen, null=True, blank=True, on_delete=models.SET_NULL) # Changed from IntegerField
    curing_regime = models.ForeignKey(CuringRegime, null=True, blank=True, on_delete=models.SET_NULL) # Changed from IntegerField
    test_conditions = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "performance_result"
        verbose_name = "Performance Result"
        verbose_name_plural = "Performance Results"
        indexes = [
            models.Index(fields=['mix', 'category', 'age_days']),
        ]

    def __str__(self):
        return f"{self.test_method or 'Test'} for Mix {self.mix_id} at {self.age_days} days"

class SustainabilityMetric(models.Model):
    """Stores sustainability metrics for a mix."""
    metric_id = models.AutoField(primary_key=True)
    mix = models.ForeignKey(ConcreteMix, on_delete=models.CASCADE, related_name="sustainability_metrics") # Metric belongs to a mix
    metric_code = models.CharField(max_length=15, blank=True, null=True, help_text="e.g., GWP, EmbodiedEnergy")
    value_num = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True) # Changed from Numeric
    unit = models.ForeignKey(UnitLookup, null=True, blank=True, on_delete=models.SET_NULL) # Changed from IntegerField
    method_ref = models.CharField(max_length=30, blank=True, null=True, help_text="Reference to calculation method or standard")

    class Meta:
        db_table = "sustainability_metric"
        verbose_name = "Sustainability Metric"
        verbose_name_plural = "Sustainability Metrics"

    def __str__(self):
        return f"{self.metric_code or 'Metric'} for Mix {self.mix_id}"

class MaterialProperty(models.Model):
    """Stores specific properties of materials."""
    property_id = models.AutoField(primary_key=True)
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="properties") # Property belongs to a material
    property_name = models.ForeignKey(
        PropertyDictionary,
        db_column="property_name",
        on_delete=models.RESTRICT, # Prevent deleting dictionary entry if used
        related_name="material_values"
    )
    # Removed property_group (lives in PropertyDictionary)
    value_num = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True) # Changed from Numeric
    unit = models.ForeignKey(UnitLookup, null=True, blank=True, on_delete=models.SET_NULL) # Changed from IntegerField
    test_method = models.ForeignKey(TestMethod, null=True, blank=True, on_delete=models.SET_NULL) # Changed from IntegerField
    test_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "material_property"
        verbose_name = "Material Property"
        verbose_name_plural = "Material Properties"
        unique_together = ('material', 'property_name') # Usually one value per property per material

    def __str__(self):
        return f"{self.property_name} for Material {self.material_id}"

# --- Material Detail Tables (OneToOne relationships) ---

class CementDetail(models.Model):
    """Details specific to cement materials."""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, primary_key=True, related_name="cement_detail")
    strength_class = models.CharField(max_length=10, blank=True, null=True)
    clinker_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "cement_detail"
        verbose_name = "Cement Detail"
        verbose_name_plural = "Cement Details"

    def __str__(self):
        return f"Details for Cement {self.material_id}"

class ScmDetail(models.Model):
    """Details specific to SCM materials."""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, primary_key=True, related_name="scm_detail")
    scm_type_code = models.CharField(max_length=20, blank=True, null=True, help_text="e.g., F, N, SF, G") # From standards like ASTM C618, EN 450 etc.
    loi_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "scm_detail"
        verbose_name = "SCM Detail"
        verbose_name_plural = "SCM Details"

    def __str__(self):
        return f"Details for SCM {self.material_id}"

class AggregateDetail(models.Model):
    """Details specific to aggregate materials."""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, primary_key=True, related_name="aggregate_detail")
    d_lower_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Lower bound size")
    d_upper_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Upper bound size (D)")
    bulk_density_kg_m3 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    water_absorption_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    fineness_modulus = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "aggregate_detail"
        verbose_name = "Aggregate Detail"
        verbose_name_plural = "Aggregate Details"

    def __str__(self):
        return f"Details for Aggregate {self.material_id}"

class AggregateConstituent(models.Model):
    """Constituent percentages for recycled/mixed aggregates (EN 12620)."""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, primary_key=True, related_name="aggregate_constituent")
    rc_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Recycled Concrete")
    ru_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Unbound Aggregate")
    ra_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Bituminous Asphalt")
    rb_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Brick")
    fl_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Floating Lightweight")
    x_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Other (Glass, etc.)")
    rg_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Glass") # Explicit Glass

    class Meta:
        db_table = "aggregate_constituent"
        verbose_name = "Aggregate Constituent"
        verbose_name_plural = "Aggregate Constituents"

    def __str__(self):
        return f"Constituents for Aggregate {self.material_id}"

class AdmixtureDetail(models.Model):
    """Details specific to admixture materials."""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, primary_key=True, related_name="admixture_detail")
    solid_content_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    specific_gravity = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    chloride_content_pct = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)

    class Meta:
        db_table = "admixture_detail"
        verbose_name = "Admixture Detail"
        verbose_name_plural = "Admixture Details"

    def __str__(self):
        return f"Details for Admixture {self.material_id}"

class FibreDetail(models.Model):
    """Details specific to fibre materials."""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, primary_key=True, related_name="fibre_detail")
    length_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    diameter_mm = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    aspect_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tensile_strength_mpa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "fibre_detail"
        verbose_name = "Fibre Detail"
        verbose_name_plural = "Fibre Details"

    def __str__(self):
        return f"Details for Fibre {self.material_id}"

# --- Utility/Staging Tables ---

class ColumnMap(models.Model):
    """Maps source CSV columns to target database tables/columns for ETL."""
    map_id = models.AutoField(primary_key=True) # Added primary key
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    source_column = models.CharField(max_length=128)
    target_table = models.CharField(max_length=64, blank=True, null=True)
    target_column = models.CharField(max_length=64, blank=True, null=True)
    unit_hint = models.CharField(max_length=20, blank=True, null=True)
    needs_conversion = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "column_map"
        unique_together = ('dataset', 'source_column')
        verbose_name = "Column Map"
        verbose_name_plural = "Column Maps"

    def __str__(self):
        return f"{self.dataset.dataset_name}: {self.source_column} -> {self.target_table}.{self.target_column}"

class StagingRaw(models.Model):
    """Optional table to stage raw row data during import."""
    raw_id = models.AutoField(primary_key=True)
    dataset = models.ForeignKey(Dataset, null=True, blank=True, on_delete=models.SET_NULL)
    row_json = models.JSONField(null=True, blank=True)
    ingest_ts = models.DateTimeField(null=True, blank=True, auto_now_add=True)

    class Meta:
        db_table = "staging_raw"
        verbose_name = "Staging Raw Data"
        verbose_name_plural = "Staging Raw Data"

    def __str__(self):
        return f"Raw data {self.raw_id} from {self.dataset.dataset_name}"

# Removed duplicate SustainabilityMetrics model - using SustainabilityMetric (singular) instead