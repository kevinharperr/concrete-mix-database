"""Material reference implementation for import_ds.py"""

def _process_row(self, dataset, raw_row, mapping: ColumnMap, row_num=0, link_only=False):
    """Process a single row of the dataset, applying the column mappings."""
    # Optionally save raw data in staging table for debugging/traceability
    try:
        cdb.StagingRaw.objects.using("cdb").create(
            dataset=dataset, row_json=raw_row
        )
    except Exception as e:
        self.stdout.write(self.style.WARNING(f"Warning: Could not save to staging table: {e}"))

    # 1. Generate mix_code with proper dataset prefix
    # If Mix_ID exists in the raw data, use it; otherwise, generate one
    mix_code = raw_row.get("Mix_ID") or raw_row.get("mix_code") or ""
    
    # Ensure mix_code has proper dataset prefix
    dataset_prefix = f"{dataset.dataset_name}-"
    if not mix_code.strip():
        # Generate a unique mix code based on dataset name and row number
        mix_code = f"{dataset_prefix}{row_num}"
        self.stdout.write(f"Generated mix code: {mix_code}")
    elif not mix_code.startswith(dataset_prefix):
        # Add prefix if not already present
        mix_code = f"{dataset_prefix}{mix_code}"
        self.stdout.write(f"Standardized mix code: {mix_code}")
    
    # 2. Get or create ConcreteMix record
    try:
        # Only one mix_code allowed per dataset+row, but we might have many different material_class components
        # Create the mix if it's new, unless in link-only mode
        if link_only:
            # In link-only mode, we only update existing mixes, we don't create new ones
            try:
                mix_object = cdb.ConcreteMix.objects.using("cdb").get(mix_code=mix_code)
                created = False
            except cdb.ConcreteMix.DoesNotExist:
                # In link-only mode, we skip mixes that don't exist
                self.stdout.write(f"Skipping mix {mix_code} - not found and in link-only mode")
                return
        else:
            # Normal mode - create mix if it doesn't exist
            mix_object, created = cdb.ConcreteMix.objects.using("cdb").get_or_create(
                mix_code=mix_code,
                defaults={
                    "dataset": dataset,
                    "notes": "",  # Will update with collected notes at end
                }
            )
        
        if created:
            self.stdout.write(f"Created new Mix: {mix_code}")
        else:
            self.stdout.write(f"Using existing Mix: {mix_code}")
            
        # For link-only mode, stop after creating the mix
        if link_only:
            return mix_object
            
        # Flag to track if mix is updated during processing
        mix_updated = False
        
        # 3. Initialize notes list to collect notes for the mix
        notes_list = []
        if mix_object.notes:  # Keep existing notes if any
            notes_list.append(mix_object.notes)
    
    except Exception as e:
        self.stdout.write(self.style.ERROR(f"Error creating/getting mix: {e}"))
        return

    # 4. Prepare containers for special processing
    biblio_ref_data = {}  # To collect bibliographic reference data
    component_calcs = {   # To collect data for component calculations
        'cement_kg_m3': None,
        'w_c_ratio': None,
        'cement_sand_ratio': None,
        'total_agg_cement_ratio': None,
        'rca_replacement_pct': None
    }
    aggregate_details = {  # To collect aggregate properties for later creation
        'RCA': {},
        'NFA': {},
        'NCA': {}
    }
    
    # Dictionary to track materials by reference key
    material_refs = {}
    
    # 4. Iterate through columns and apply mapping rules
    for col_name, value in raw_row.items():
        # Skip empty values
        if value is None or str(value).strip() == "":
            continue
            
        # Find mapping rule for this column
        rule = mapping.match(col_name)
        if not rule:
            continue  # No mapping rule for this column
            
        table = rule["target_table"]
        target_field = rule["target_column"]
        kw = rule["extra_kwargs"]
        
        # Extract source column name for error messages
        source_column = col_name
        
        # Pre-process values for component calculations based on column names
        # This collects values needed for ratio-based calculations later
        if table == "concrete_mix" and target_field == "w_c_ratio":
            component_calcs['w_c_ratio'] = self._cast_decimal(value)
        elif table == "concrete_mix" and target_field == "notes":  
            if kw.get("prefix") == "Total Agg/Cement Ratio:":
                component_calcs['total_agg_cement_ratio'] = self._cast_decimal(value)
            elif kw.get("prefix") == "Cement/Sand Ratio:":
                component_calcs['cement_sand_ratio'] = self._cast_decimal(value)
            elif kw.get("prefix") == "RCA Replacement Level (%):":
                component_calcs['rca_replacement_pct'] = self._cast_decimal(value)
        elif table == "mix_component" and kw.get("class_code") == "CEMENT":
            component_calcs['cement_kg_m3'] = self._cast_decimal(value)
        elif table == "bibliographic_reference":
            # Collect bibliographic data for later processing
            biblio_ref_data[target_field] = value
            
        try:
            # --- Handle different target tables ---
            
            # === CONCRETE MIX TABLE ===
            if table == "concrete_mix":
                if target_field == "notes":
                    # Add to notes collection with optional prefix
                    prefix = kw.get("prefix", "")
                    note_text = f"{prefix}{value}".strip()
                    if note_text:
                        notes_list.append(note_text)
                        mix_updated = True
                elif hasattr(mix_object, target_field):
                    # Cast value based on field type
                    if target_field in ["w_c_ratio", "w_b_ratio", "wb_k_reported", "target_slump_mm"]:
                        casted_value = self._cast_decimal(value)
                    elif target_field == "date_created":
                        # TODO: Add date parsing if needed
                        casted_value = value
                    else:
                        casted_value = value
                        
                    # Set attribute on mix object if cast successful
                    if casted_value is not None:
                        setattr(mix_object, target_field, casted_value)
                        
                        # If we're setting wb_k_reported, also set k_flag to True
                        if target_field == "wb_k_reported":
                            mix_object.k_flag = True
                            
                        mix_updated = True
                else:
                    self.stdout.write(self.style.WARNING(
                        f"Warning: Field '{target_field}' not found on ConcreteMix model"
                    ))
            
            # === MIX COMPONENT TABLE ===
            elif table == "mix_component":
                # Extract material information from mapping
                specific_name = kw.get("specific_name", target_field)  # Default material name is in target_field
                class_code = kw.get("class_code")
                subtype_code = kw.get("subtype_code")
                is_cementitious = kw.get("is_cementitious", False)
                reference_key = kw.get("reference_key")  # Get the reference key if provided
                
                # Check if we should use dynamic naming from another column
                source_type_column = kw.get("source_type_column")
                if source_type_column:
                    # Get the type name from the specified column
                    src_name = raw_row.get(source_type_column, "").strip()
                    
                    if src_name:
                        # Sanitize the name: strip, lowercase, replace spaces with underscores
                        # Keep alphanumerics and /,-,_
                        clean_name = re.sub(r'[^\w/\-]', '_', src_name.lower())
                        clean_name = re.sub(r'\s+', '_', clean_name)
                        
                        # Safety truncation to 60 characters (database field limit)
                        if len(clean_name) > 60:
                            self.stdout.write(self.style.WARNING(
                                f"Warning: Material name '{clean_name}' exceeds 60 characters and will be truncated"
                            ))
                            clean_name = clean_name[:60]
                        
                        # Use the sanitized name for both specific_name and subtype_code
                        specific_name = clean_name
                        subtype_code = clean_name
                        
                        self.stdout.write(f"Using dynamic material name from '{source_type_column}': {specific_name}")
                
                # Cast and validate dosage
                dosage = self._cast_decimal(value)
                if dosage is None or dosage < 0:  # Allow zero dosages (valid in some cases)
                    self.stdout.write(self.style.WARNING(
                        f"Warning: Invalid dosage '{value}' for {specific_name}, skipping"
                    ))
                    continue
                
                # Use the helper function to get or create material
                try:
                    material_object = get_or_create_material(
                        class_code=class_code,
                        subtype_code=subtype_code,
                        specific_name=specific_name,
                        extra={
                            "dataset": dataset.dataset_name
                        }
                    )
                    
                    # If this material has a reference key, store it for later use
                    if reference_key:
                        material_refs[reference_key] = material_object
                        self.stdout.write(f"Tracked material reference '{reference_key}': {material_object.specific_name} (ID: {material_object.material_id})")
                    
                    # Log what material we're using
                    self.stdout.write(f"Using material: {target_field} (Class: {class_code})")
                    
                    # Create or update the link between mix and material
                    mix_comp, created = cdb.MixComponent.objects.using("cdb").update_or_create(
                        mix=mix_object,
                        material=material_object,
                        defaults={
                            'dosage_kg_m3': dosage,
                            'is_cementitious': is_cementitious
                        }
                    )
                    
                    self.stdout.write(f"Added {target_field} ({dosage} kg/m³) to mix {mix_code}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Error creating material or component: {e}"
                    ))
            
            # === MATERIAL PROPERTY TABLE ===
            elif table == "material_property":
                # Simplified material property handling
                property_name = kw.get("property_name")
                property_group = kw.get("property_group")
                material_id = kw.get("material_id")
                material_ref_key = kw.get("material_ref_key")
                
                # Skip if missing required fields
                if not property_name or not property_group:
                    self.stdout.write(self.style.WARNING(
                        f"Warning: Missing property_name or property_group in mapping for {source_column}"
                    ))
                    continue
                
                # Validate value and convert to numeric
                value_num = self._cast_decimal(value)
                if value_num is None:
                    self.stdout.write(self.style.WARNING(
                        f"Warning: Invalid numeric value '{value}' for material property {property_name}"
                    ))
                    continue

                # Find the property in the PropertyDictionary
                try:
                    prop_dict, created = cdb.PropertyDictionary.objects.using("cdb").get_or_create(
                        property_name=property_name,
                        defaults={
                            "display_name": property_name.replace("_", " ").title(),
                            "property_group": property_group
                        }
                    )
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Error creating property dictionary entry: {e}"
                    ))
                    continue
                
                # Find material either by direct ID or through reference key
                material = None
                
                # First try reference key
                if material_ref_key and material_ref_key in material_refs:
                    material = material_refs[material_ref_key]
                    self.stdout.write(f"Using material from reference key '{material_ref_key}' for property {property_name}")
                # Then try direct material ID
                elif material_id:
                    try:
                        material = cdb.Material.objects.using("cdb").get(material_id=material_id)
                    except cdb.Material.DoesNotExist:
                        self.stdout.write(self.style.WARNING(
                            f"Warning: Material ID {material_id} not found"
                        ))
                
                # If we don't have a material, skip this property
                if not material:
                    self.stdout.write(self.style.WARNING(
                        f"Warning: No material found for property {property_name}"
                    ))
                    continue
                
                # Create or update the property value
                try:
                    mat_prop, created = cdb.MaterialProperty.objects.using("cdb").update_or_create(
                        material=material,
                        property_name=prop_dict,
                        defaults={
                            "value_num": value_num
                        }
                    )
                    
                    if created:
                        self.stdout.write(f"Added property {property_name}={value_num} to {material}")
                    else:
                        self.stdout.write(f"Updated property {property_name}={value_num} for {material}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Error saving material property: {e}"
                    ))
            
            # === AGGREGATE DETAIL TABLE ===
            elif table == "aggregate_detail":
                # Simplify aggregate detail handling by using material references
                material_id = kw.get("material_id")
                material_ref_key = kw.get("material_ref_key")
                field_name = target_field
                
                # Handle different detail fields (water_absorption_pct, d_upper_mm, etc.)
                # Convert to appropriate type based on field name
                if field_name in ["bulk_density_kg_m3", "water_absorption_pct", "fineness_modulus", "d_upper_mm", "d_lower_mm"]:
                    casted_value = self._cast_decimal(value)
                else:
                    # Default to string
                    casted_value = value
                    
                if casted_value is None:
                    self.stdout.write(self.style.WARNING(
                        f"Warning: Invalid value '{value}' for aggregate detail {field_name}"
                    ))
                    continue
                
                # Find material either by direct ID or through reference key
                material = None
                
                # First try reference key
                if material_ref_key and material_ref_key in material_refs:
                    material = material_refs[material_ref_key]
                    self.stdout.write(f"Using material from reference key '{material_ref_key}' for aggregate detail {field_name}")
                # Then try direct material ID
                elif material_id:
                    try:
                        material = cdb.Material.objects.using("cdb").get(material_id=material_id)
                    except cdb.Material.DoesNotExist:
                        self.stdout.write(self.style.WARNING(
                            f"Warning: Material ID {material_id} not found for aggregate detail"
                        ))
                
                # If we don't have a material, skip this property
                if not material:
                    self.stdout.write(self.style.WARNING(
                        f"Warning: No material found for aggregate detail {field_name}"
                    ))
                    continue
                
                # Get or create aggregate detail for this material
                try:
                    agg_detail, created = cdb.AggregateDetail.objects.using("cdb").get_or_create(
                        material=material,
                        defaults={
                            "bulk_density_kg_m3": None,
                            "water_absorption_pct": None,
                            "fineness_modulus": None,
                            "d_upper_mm": None,
                            "d_lower_mm": None
                        }
                    )
                    
                    # Set the field value
                    try:
                        setattr(agg_detail, field_name, casted_value)
                        agg_detail.save(using="cdb")
                        self.stdout.write(f"Set {material.specific_name} detail {field_name} = {casted_value}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f"Error setting aggregate detail field {field_name}: {e}"
                        ))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Error creating aggregate detail: {e}"
                    ))
            
            # === PERFORMANCE RESULT TABLE ===
            elif table == "performance_result":
                # Extract performance test information
                category = kw.get("category")
                unit_id = kw.get("unit_id")
                test_method_id = kw.get("test_method_id")
                age_days = kw.get("age_days")
                
                # Validate that we have at least a category
                if not category:
                    self.stdout.write(self.style.WARNING(
                        f"Warning: Missing category in mapping for {source_column}"
                    ))
                    continue
                
                # Cast the value to a decimal
                numeric_value = self._cast_decimal(value)
                if numeric_value is None:
                    self.stdout.write(self.style.WARNING(
                        f"Warning: Invalid numeric value '{value}' for performance result"
                    ))
                    continue
                
                # Create the performance result
                try:
                    # Create a unit lookup record if needed
                    unit_object = None
                    if unit_id:
                        unit_object, created = cdb.UnitLookup.objects.using("cdb").get_or_create(
                            unit_id=unit_id
                        )
                    
                    # Create a test method record if needed
                    test_method_object = None
                    if test_method_id:
                        test_method_object, created = cdb.TestMethod.objects.using("cdb").get_or_create(
                            test_method_id=test_method_id
                        )
                    
                    # Create the performance result record
                    perf_result, created = cdb.PerformanceResult.objects.using("cdb").update_or_create(
                        mix=mix_object,
                        category=category,
                        test_method=test_method_object,
                        age_days=age_days,
                        defaults={
                            "value_num": numeric_value,
                            "unit": unit_object
                        }
                    )
                    
                    self.stdout.write(f"Added {category} result: {numeric_value} at {age_days} days for mix {mix_code}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Error saving performance result: {e}"
                    ))
                        
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Error processing column '{source_column}' for table '{table}': {e}"
            ))
    
    # 5. Process bibliographic reference if we have enough info
    if biblio_ref_data.get("citation_text") or biblio_ref_data.get("author"):
        try:
            citation = biblio_ref_data.get("citation_text", "")
            if not citation and biblio_ref_data.get("author"):
                # Create a citation from author and year if available
                author = biblio_ref_data.get("author", "")
                year = biblio_ref_data.get("year", "")
                if author and year:
                    citation = f"[{author} et al. {year}]"
                else:
                    citation = f"[{author or year}]"
            
            if citation:
                # Check if the reference already exists
                biblio_ref, created = cdb.BibliographicReference.objects.using("cdb").get_or_create(
                    citation_text=citation,
                    defaults={
                        "author": biblio_ref_data.get("author", ""),
                        "year": biblio_ref_data.get("year", None),
                        "doi": biblio_ref_data.get("doi", ""),
                        "url": biblio_ref_data.get("url", "")
                    }
                )
                
                if created:
                    self.stdout.write(f"Created bibliographic reference: {citation}")
                else:
                    self.stdout.write(f"Using existing bibliographic reference: {citation}")
                
                # Link the reference to the mix
                cdb.ConcreteMixReference.objects.using("cdb").get_or_create(
                    mix=mix_object,
                    reference=biblio_ref
                )
                
                self.stdout.write(f"Linked reference to mix {mix_code}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Error processing bibliographic reference: {e}"
            ))
    
    # 6. Final updates to mix
    try:
        # Update notes if any were collected
        if notes_list:
            mix_object.notes = "\n".join(notes_list)
            mix_updated = True
            
        # Save the mix if it was updated
        if mix_updated:
            mix_object.save(using="cdb")
            self.stdout.write(f"Saved updates to mix {mix_code}")
    except Exception as e:
        self.stdout.write(self.style.ERROR(
            f"Error updating mix: {e}"
        ))
        
    return mix_object
