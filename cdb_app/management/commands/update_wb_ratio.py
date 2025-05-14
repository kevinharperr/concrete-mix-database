from django.core.management.base import BaseCommand
from cdb_app.models import ConcreteMix, MixComponent, Material, MaterialClass
from django.db.models import Sum, F, Q
from django.db import transaction
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Calculate and update water-binder ratio values in the database using simple Water/(Cement+SCMs) formula'

    def handle(self, *args, **options):
        self.stdout.write('Starting water-binder ratio update using Water/(Cement+SCMs) calculation...')
        
        # Step 1: Check and update cementitious flags for all materials
        self.check_cementitious_flags()
        
        # Step 2: Update all w_b_ratio values using the simple water-binder calculation
        self.update_all_wb_ratios()
        
    def check_cementitious_flags(self):
        """
        Verify and update the is_cementitious flag for all materials in mix components.
        Material is cementitious if it belongs to CEMENT or SCM material classes.
        """
        self.stdout.write('Checking cementitious flags for materials...')
        
        # Get all mix components
        components = MixComponent.objects.select_related('material', 'material__material_class')
        
        # Track counters
        updated_count = 0
        verified_count = 0
        processed_materials = set()
        
        with transaction.atomic():
            for comp in components:
                # Skip materials we've already processed
                if comp.material_id in processed_materials:
                    continue
                    
                processed_materials.add(comp.material_id)
                
                # Determine if material should be cementitious
                material_class = comp.material.material_class.class_code if comp.material.material_class else ''
                should_be_cementitious = material_class in ['CEMENT', 'SCM']
                
                # Special case handling: 'FA-B' should be considered cementitious even if current flag is False
                subtype = comp.material.subtype_code or ''
                if subtype.lower() in ['fa-b', 'fa', 'sf', 'ggbs', 'cfa']:
                    should_be_cementitious = True
                
                # Update if needed
                if comp.is_cementitious != should_be_cementitious:
                    # Update all components with this material
                    components_to_update = MixComponent.objects.filter(material=comp.material)
                    update_count = components_to_update.update(is_cementitious=should_be_cementitious)
                    updated_count += 1
                    
                    self.stdout.write(f"  Updated material {comp.material.material_id} '{comp.material.specific_name or subtype}' "
                             f"({material_class}): is_cementitious={should_be_cementitious} "
                             f"[{update_count} components]")
                else:
                    verified_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Cementitious flags check complete: '
            f'Updated {updated_count} materials, '
            f'Verified {verified_count} materials'
        ))
    
    def update_all_wb_ratios(self):
        """
        Update all water-binder ratios in the database using the simple
        Water/(Cement+SCMs) calculation.
        """
        self.stdout.write('Updating water-binder ratios...')
        
        # Get all mixes
        mixes = ConcreteMix.objects.all()
        self.stdout.write(f'Found {mixes.count()} mixes to process')
        
        # Track counters
        updated_count = 0
        failed_count = 0
        
        for mix in mixes:
            try:
                # Calculate the simple water-binder ratio
                wb_ratio = self.calculate_simple_wb_ratio(mix)
                
                if wb_ratio is not None:
                    # Check if value is significantly different from existing value
                    update_needed = True
                    if mix.w_b_ratio is not None:
                        try:
                            # Ensure both are Decimal objects for safe comparison
                            existing_value = mix.w_b_ratio if isinstance(mix.w_b_ratio, Decimal) else Decimal(str(mix.w_b_ratio))
                            new_value = wb_ratio if isinstance(wb_ratio, Decimal) else Decimal(str(wb_ratio))
                            diff = abs(existing_value - new_value)
                            
                            if diff <= Decimal('0.001'):
                                update_needed = False
                        except Exception as e:
                            logger.error(f"Error comparing values for mix {mix.mix_id}: {str(e)}")
                    
                    if update_needed:
                        old_value = mix.w_b_ratio
                        mix.w_b_ratio = wb_ratio
                        mix.save(update_fields=['w_b_ratio'])
                        updated_count += 1
                        
                        if old_value is not None:
                            try:
                                # Convert both to Decimal for safe comparison
                                old_decimal = Decimal(str(old_value))
                                new_decimal = Decimal(str(wb_ratio))
                                if abs(new_decimal - old_decimal) > Decimal('0.1'):
                                    self.stdout.write(f"  Mix {mix.mix_id}: w/b ratio updated from {old_value} to {wb_ratio}")
                            except Exception as e:
                                logger.error(f"Error comparing values for mix {mix.mix_id}: {str(e)}")
                else:
                    failed_count += 1
                    self.stdout.write(self.style.WARNING(f"  No water or binder content found for mix {mix.mix_id}"))
            except Exception as e:
                failed_count += 1
                logger.error(f"Error updating mix {mix.mix_id}: {str(e)}")
        
        self.stdout.write(self.style.SUCCESS(
            f'Water-binder ratio update complete: '
            f'Updated {updated_count} mixes, '
            f'Failed to update {failed_count} mixes'
        ))
    
    def calculate_simple_wb_ratio(self, mix):
        """
        Calculate water-binder ratio using the simple formula:
        w/b = Water / (Cement + ALL SCMs)
        
        This counts ALL cementitious materials (both cement and SCMs) as binder,
        using the is_cementitious flag to identify them.
        """
        # Get all components for this mix
        components = MixComponent.objects.filter(mix=mix).select_related('material')
        
        # If no components found, can't calculate
        if not components.exists():
            return None
        
        # Find water content (kg/m3)
        water_components = components.filter(
            material__material_class__class_code='WATER'
        )
        water_content = water_components.aggregate(
            total=Sum('dosage_kg_m3')
        )['total'] or 0
        
        # Find total binder content using the is_cementitious flag (kg/m3)
        binder_components = components.filter(
            is_cementitious=True
        )
        binder_content = binder_components.aggregate(
            total=Sum('dosage_kg_m3')
        )['total'] or 0
        
        # If no binder or water found, can't calculate
        if binder_content <= 0 or water_content <= 0:
            return None
        
        # Calculate w/b ratio
        wb_ratio = water_content / binder_content
        return round(wb_ratio, 3)
    
    def calculate_wb_ratio(self, mix):
        """
        Original calculation method - maintained for backward compatibility.
        Now simply calls calculate_simple_wb_ratio for consistent calculation.
        """
        return self.calculate_simple_wb_ratio(mix)

    def get_detailed_mix_composition(self, mix):
        """
        Get detailed breakdown of mix composition for debugging or reporting.
        """
        components = MixComponent.objects.filter(mix=mix).select_related('material', 'material__material_class')
        
        # Initialize content values
        water_content = 0
        cement_content = 0
        scm_content = 0
        other_content = 0
        cementitious_content = 0
        
        # Process components
        component_details = []
        for comp in components:
            material_class = comp.material.material_class.class_code if comp.material.material_class else 'UNKNOWN'
            dosage = comp.dosage_kg_m3 or 0
            is_cementitious = comp.is_cementitious
            
            # Track totals
            if material_class == 'WATER':
                water_content += dosage
            elif material_class == 'CEMENT':
                cement_content += dosage
            elif material_class == 'SCM':
                scm_content += dosage
            else:
                other_content += dosage
                
            if is_cementitious:
                cementitious_content += dosage
                
            # Record component details
            component_details.append({
                'material_id': comp.material.material_id,
                'material_class': material_class,
                'subtype': comp.material.subtype_code,
                'dosage': dosage,
                'is_cementitious': is_cementitious
            })
        
        # Calculate ratios
        wb_simple = water_content / cementitious_content if cementitious_content > 0 else None
        wc_ratio = water_content / cement_content if cement_content > 0 else None
        
        return {
            'mix_id': mix.mix_id,
            'mix_code': mix.mix_code,
            'water_content': water_content,
            'cement_content': cement_content,
            'scm_content': scm_content,
            'cementitious_content': cementitious_content,
            'w_b_ratio_simple': round(wb_simple, 3) if wb_simple else None,
            'w_c_ratio': round(wc_ratio, 3) if wc_ratio else None,
            'stored_w_b_ratio': mix.w_b_ratio,
            'stored_w_c_ratio': mix.w_c_ratio,
            'stored_wb_k_reported': mix.wb_k_reported,
            'components': component_details
        }
