from django.core.management.base import BaseCommand, CommandError
from cdb_app.models import ConcreteMix, Dataset
from django.db import transaction

class Command(BaseCommand):
    help = 'Standardizes the mix codes for DS6 dataset to ensure proper DS6- prefix'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode. No changes will be made.'))
        
        # Get the DS6 dataset
        try:
            ds6_dataset = Dataset.objects.using("cdb").get(dataset_name="DS6")
            self.stdout.write(f"Found DS6 dataset: {ds6_dataset.dataset_name}")
        except Dataset.DoesNotExist:
            raise CommandError("DS6 dataset not found in database!")
            
        # Find all DS6 mixes without the proper prefix
        bad_mixes = ConcreteMix.objects.using("cdb").filter(
            dataset=ds6_dataset
        ).exclude(
            mix_code__startswith="DS6-"
        )
        
        total_bad_mixes = bad_mixes.count()
        self.stdout.write(f"Found {total_bad_mixes} mixes with incorrect mix codes")
        
        if total_bad_mixes == 0:
            self.stdout.write(self.style.SUCCESS("All DS6 mix codes have the proper prefix!"))
            return
            
        # Get all existing DS6 mix codes to avoid conflicts
        existing_mix_codes = set(
            ConcreteMix.objects.using("cdb")
            .filter(mix_code__startswith="DS6-")
            .values_list('mix_code', flat=True)
        )
        
        # Process mixes in a transaction
        with transaction.atomic(using="cdb"):
            mixes_fixed = 0
            duplicates_handled = 0
            
            for mix in bad_mixes:
                old_mix_code = mix.mix_code
                
                # Generate and validate new mix code
                if old_mix_code.isdigit():
                    # For numeric mix codes, use DS6-{old_code}
                    new_mix_code = f"DS6-{old_mix_code}"
                else:
                    # For non-numeric mix codes, still add prefix
                    new_mix_code = f"DS6-{old_mix_code}"
                
                # Handle potential duplicates
                if new_mix_code in existing_mix_codes:
                    suffix = 1
                    while f"{new_mix_code}-{suffix}" in existing_mix_codes:
                        suffix += 1
                        
                    new_mix_code = f"{new_mix_code}-{suffix}"
                    duplicates_handled += 1
                
                # Update the mix code
                self.stdout.write(f"Changing mix code from '{old_mix_code}' to '{new_mix_code}'")
                
                if not dry_run:
                    mix.mix_code = new_mix_code
                    mix.save(using="cdb")
                    existing_mix_codes.add(new_mix_code)  # Add to existing set to avoid future conflicts
                
                mixes_fixed += 1
                
                # Progress indicator for large datasets
                if mixes_fixed % 100 == 0:
                    self.stdout.write(f"Progress: {mixes_fixed}/{total_bad_mixes} mixes fixed")
            
            if dry_run:
                self.stdout.write(self.style.SUCCESS(f"DRY RUN COMPLETED. Would have fixed {mixes_fixed} mixes, with {duplicates_handled} duplicates handled."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Successfully fixed {mixes_fixed} mixes, with {duplicates_handled} duplicates handled."))
