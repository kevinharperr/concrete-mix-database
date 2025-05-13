# concrete_mix_app/models.py
# This is an auto-generated Django model module, subsequently edited.
from django.db import models
# Import the User model for potential future use with created_by, even if not used yet.
from django.contrib.auth.models import User

# Implementation for tracking object ownership without modifying legacy tables
class UserObjectTracking(models.Model):
    """Tracks ownership of objects created by users without modifying legacy tables."""
    content_type = models.CharField(max_length=50)  # Model name (e.g., 'Material', 'Concretemix')
    object_id = models.IntegerField()  # Primary key of the tracked object
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # This model IS managed by Django since it's new and not part of the legacy schema
        managed = True
        db_table = 'user_object_tracking'
        unique_together = ('content_type', 'object_id')
        verbose_name = "User Object Tracking"
        verbose_name_plural = "User Object Tracking"
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.content_type} #{self.object_id} created by {self.created_by}"

class Bibliographicreference(models.Model):
    reference_id = models.AutoField(primary_key=True)
    source_dataset = models.CharField(max_length=50, blank=True, null=True)
    author = models.CharField(max_length=255, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    publication = models.CharField(max_length=255, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    doi = models.CharField(max_length=100, blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        managed = False # Keep as False since the table exists
        db_table = 'bibliographicreference'
        verbose_name = "Bibliographic Reference"
        verbose_name_plural = "Bibliographic References"

    def __str__(self):
        return f"{self.author or 'Unknown'} ({self.year or 'N/A'}) - {self.title or 'No Title'}"[:80]

class Concretemix(models.Model):
    mix_id = models.AutoField(primary_key=True)
    mix_code = models.CharField(unique=True, max_length=50, blank=True, null=True)
    date_created = models.DateField(blank=True, null=True)
    source_dataset = models.CharField(max_length=50, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    target_strength_mpa = models.FloatField(blank=True, null=True)
    target_workability_mm = models.FloatField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    # Changed from IntegerField to ForeignKey
    reference = models.ForeignKey(
        Bibliographicreference,
        models.SET_NULL, # Use SET_NULL since null=True
        db_column='reference_id', # Explicitly state the DB column name
        blank=True,
        null=True,
        related_name='concrete_mixes'
    )
    # created_by field omitted for now (see note at top)

    class Meta:
        managed = False # Keep as False since the table exists
        db_table = 'concretemix'
        verbose_name = "Concrete Mix"
        verbose_name_plural = "Concrete Mixes"

    def __str__(self):
        return f"Mix {self.mix_code or self.mix_id}"

class Material(models.Model):
    material_id = models.AutoField(primary_key=True)
    material_type = models.CharField(max_length=50, blank=True, null=True)
    subtype = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    standard_reference = models.CharField(max_length=100, blank=True, null=True)
    date_added = models.DateField(blank=True, null=True)
    source_dataset = models.CharField(max_length=50, blank=True, null=True)
    # created_by field omitted for now

    class Meta:
        managed = False # Keep as False since the table exists
        db_table = 'material'
        verbose_name = "Material"
        verbose_name_plural = "Materials"

    def __str__(self):
        return f"{self.name or self.material_type or 'Unnamed Material'} ({self.subtype or 'No Subtype'})"

class Chemicalcomposition(models.Model):
    composition_id = models.AutoField(primary_key=True)
    material = models.ForeignKey(
        Material,
        models.SET_NULL, # Use SET_NULL since null=True
        blank=True,
        null=True,
        related_name='chemical_compositions'
    )
    sio2_pct = models.FloatField(blank=True, null=True)
    al2o3_pct = models.FloatField(blank=True, null=True)
    fe2o3_pct = models.FloatField(blank=True, null=True)
    cao_pct = models.FloatField(blank=True, null=True)
    mgo_pct = models.FloatField(blank=True, null=True)
    so3_pct = models.FloatField(blank=True, null=True)
    na2o_pct = models.FloatField(blank=True, null=True)
    k2o_pct = models.FloatField(blank=True, null=True)
    tio2_pct = models.FloatField(blank=True, null=True)
    p2o5_pct = models.FloatField(blank=True, null=True)
    loi_pct = models.FloatField(blank=True, null=True)
    date_added = models.DateField(blank=True, null=True)
    # created_by field omitted for now

    class Meta:
        managed = False # Keep as False since the table exists
        db_table = 'chemicalcomposition'
        verbose_name = "Chemical Composition"
        verbose_name_plural = "Chemical Compositions"

    def __str__(self):
        material_name = str(self.material) if self.material else "Unknown Material"
        return f"Chemical Composition for {material_name}"

class Materialproperty(models.Model):
    property_id = models.AutoField(primary_key=True)
    material = models.ForeignKey(
        Material,
        models.SET_NULL, # Use SET_NULL since null=True
        blank=True,
        null=True,
        related_name='material_properties'
    )
    property_name = models.CharField(max_length=100, blank=True, null=True)
    property_value = models.FloatField(blank=True, null=True)
    property_text = models.TextField(blank=True, null=True)
    property_unit = models.CharField(max_length=50, blank=True, null=True)
    test_method = models.CharField(max_length=100, blank=True, null=True)
    date_measured = models.DateField(blank=True, null=True)
    # Note: The specific RCA/NCA fields might be better normalized in a future DB version
    rca_bulk_density = models.FloatField(blank=True, null=True)
    rca_water_absorption = models.FloatField(blank=True, null=True)
    rca_size = models.FloatField(blank=True, null=True)
    nca_bulk_density = models.FloatField(blank=True, null=True)
    nca_water_absorption = models.FloatField(blank=True, null=True)
    nca_size = models.FloatField(blank=True, null=True)
    # created_by field omitted for now

    class Meta:
        managed = False # Keep as False since the table exists
        db_table = 'materialproperty'
        verbose_name = "Material Property"
        verbose_name_plural = "Material Properties"

    def __str__(self):
        material_name = str(self.material) if self.material else "Unknown Material"
        return f"{self.property_name or 'Unnamed Property'} for {material_name}"

class Mixcomposition(models.Model):
    composition_id = models.AutoField(primary_key=True)
    mix = models.ForeignKey(
        Concretemix,
        models.SET_NULL, # Use SET_NULL since null=True
        blank=True,
        null=True,
        related_name='mix_compositions'
    )
    material = models.ForeignKey(
        Material,
        models.SET_NULL, # Use SET_NULL since null=True
        blank=True,
        null=True,
        related_name='mix_compositions'
    )
    quantity_kg_m3 = models.FloatField(blank=True, null=True)
    percentage_by_weight = models.FloatField(blank=True, null=True)
    replacement_percentage = models.FloatField(blank=True, null=True)
    w_c_ratio = models.FloatField(blank=True, null=True)
    w_b_ratio = models.FloatField(blank=True, null=True)
    is_wb_ratio = models.BooleanField(blank=True, null=True)
    # created_by field omitted for now

    class Meta:
        managed = True # Changed to True to let Django manage this table
        db_table = 'mixcomposition'
        verbose_name = "Mix Composition"
        verbose_name_plural = "Mix Compositions"

    def __str__(self):
        mix_name = str(self.mix) if self.mix else "Unknown Mix"
        material_name = str(self.material) if self.material else "Unknown Material"
        return f"{material_name} in {mix_name}"

class Specimen(models.Model):
    specimen_id = models.AutoField(primary_key=True)
    specimen_type = models.CharField(max_length=100, blank=True, null=True)
    dimension_mm = models.CharField(max_length=100, blank=True, null=True)
    shape = models.CharField(max_length=50, blank=True, null=True)
    curing_regime = models.CharField(max_length=100, blank=True, null=True)
    standard_reference = models.CharField(max_length=100, blank=True, null=True)
    # created_by field omitted for now

    class Meta:
        managed = False # Keep as False since the table exists
        db_table = 'specimen'
        verbose_name = "Specimen"
        verbose_name_plural = "Specimens"

    def __str__(self):
        return f"{self.specimen_type or 'Unknown Type'} ({self.dimension_mm or 'N/A'}) - ID: {self.specimen_id}"


class Performanceresult(models.Model):
    result_id = models.AutoField(primary_key=True)
    mix = models.ForeignKey(
        Concretemix,
        models.SET_NULL, # Use SET_NULL since null=True
        blank=True,
        null=True,
        related_name='performance_results'
    )
    test_type = models.CharField(max_length=100, blank=True, null=True)
    test_age_days = models.IntegerField(blank=True, null=True)
    test_value = models.FloatField(blank=True, null=True)
    test_unit = models.CharField(max_length=50, blank=True, null=True)
    test_conditions = models.CharField(max_length=100, blank=True, null=True)
    curing_regime = models.CharField(max_length=100, blank=True, null=True)
    # Changed from IntegerField to ForeignKey
    specimen = models.ForeignKey(
        Specimen,
        models.SET_NULL, # Use SET_NULL since null=True
        db_column='specimen_id', # Explicitly state the DB column name
        blank=True,
        null=True,
        related_name='performance_results'
    )
    # created_by field omitted for now

    class Meta:
        managed = False # Keep as False since the table exists
        db_table = 'performanceresult'
        verbose_name = "Performance Result"
        verbose_name_plural = "Performance Results"

    def __str__(self):
        mix_name = str(self.mix) if self.mix else "Unknown Mix"
        return f"{self.test_type or 'Unknown Test'} for {mix_name} at {self.test_age_days or '?'} days"

class Durabilityresult(models.Model):
    result_id = models.AutoField(primary_key=True)
    mix = models.ForeignKey(
        Concretemix,
        models.SET_NULL, # Use SET_NULL since null=True
        blank=True,
        null=True,
        related_name='durability_results'
    )
    test_type = models.CharField(max_length=100, blank=True, null=True)
    test_age_days = models.IntegerField(blank=True, null=True)
    test_value = models.FloatField(blank=True, null=True)
    test_unit = models.CharField(max_length=50, blank=True, null=True)
    test_conditions = models.CharField(max_length=100, blank=True, null=True)
    specimen = models.ForeignKey(
        Specimen,
        models.SET_NULL, # Use SET_NULL since null=True
        blank=True,
        null=True,
        related_name='durability_results'
    )
    # created_by field omitted for now

    class Meta:
        managed = False # Keep as False since the table exists
        db_table = 'durabilityresult'
        verbose_name = "Durability Result"
        verbose_name_plural = "Durability Results"

    def __str__(self):
        mix_name = str(self.mix) if self.mix else "Unknown Mix"
        return f"{self.test_type or 'Unknown Test'} for {mix_name} at {self.test_age_days or '?'} days"


class Sustainabilitymetrics(models.Model):
    metric_id = models.AutoField(primary_key=True)
    mix = models.ForeignKey(
        Concretemix,
        models.SET_NULL, # Use SET_NULL since null=True
        blank=True,
        null=True,
        related_name='sustainability_metrics'
    )
    co2_footprint_kg_per_m3 = models.FloatField(blank=True, null=True)
    cost_per_m3 = models.FloatField(blank=True, null=True)
    clinker_factor = models.FloatField(blank=True, null=True)
    scm_percentage = models.FloatField(blank=True, null=True)
    recyclability_index = models.FloatField(blank=True, null=True)
    embodied_energy_mj_per_m3 = models.FloatField(blank=True, null=True)
    global_warming_potential_kg_co2e = models.FloatField(blank=True, null=True)
    # created_by field omitted for now

    class Meta:
        managed = False # Keep as False since the table exists
        db_table = 'sustainabilitymetrics'
        verbose_name = "Sustainability Metric"
        verbose_name_plural = "Sustainability Metrics"

    def __str__(self):
        mix_name = str(self.mix) if self.mix else "Unknown Mix"
        return f"Sustainability Metrics for {mix_name}"

class Datasetversion(models.Model):
    # This model seems informational about data imports, might not need direct user interaction often
    version_id = models.AutoField(primary_key=True)
    source_dataset = models.CharField(max_length=50, blank=True, null=True)
    import_date = models.DateField(blank=True, null=True)
    version_notes = models.TextField(blank=True, null=True)
    row_count = models.IntegerField(blank=True, null=True)
    has_material_properties = models.BooleanField(blank=True, null=True)
    has_chemical_composition = models.BooleanField(blank=True, null=True)
    has_performance_results = models.BooleanField(blank=True, null=True)
    has_durability_results = models.BooleanField(blank=True, null=True)
    has_sustainability_metrics = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False # Keep as False since the table exists
        db_table = 'datasetversion'
        verbose_name = "Dataset Version"
        verbose_name_plural = "Dataset Versions"

    def __str__(self):
        return f"Version {self.version_id} ({self.source_dataset or 'Unknown Source'}) - {self.import_date or 'No Date'}"
