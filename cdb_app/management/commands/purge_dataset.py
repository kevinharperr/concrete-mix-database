# cdb_app/management/commands/purge_dataset.py
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from cdb_app.models import Dataset

class Command(BaseCommand):
    help = "Purge a dataset and all its related data"

    def add_arguments(self, parser):
        parser.add_argument('dataset_code', help='Dataset code (e.g., DS5)')

    def handle(self, *args, **options):
        dataset_code = options['dataset_code']
        
        # Get dataset ID
        try:
            dataset = Dataset.objects.using('cdb').get(dataset_name=dataset_code)
            dataset_id = dataset.dataset_id
        except Dataset.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Dataset {dataset_code} does not exist"))
            return
        
        self.stdout.write(f"Preparing to delete dataset {dataset_code} (ID: {dataset_id})")
        
        # Execute DELETE statements in the correct order
        with connections['cdb'].cursor() as cursor:
            with transaction.atomic(using='cdb'):
                # First delete from child tables
                cursor.execute(f'DELETE FROM performance_result WHERE mix_id IN (SELECT mix_id FROM concrete_mix WHERE dataset_id={dataset_id})')
                self.stdout.write(self.style.SUCCESS('Deleted performance results'))
                
                cursor.execute(f'DELETE FROM mix_component WHERE mix_id IN (SELECT mix_id FROM concrete_mix WHERE dataset_id={dataset_id})')
                self.stdout.write(self.style.SUCCESS('Deleted mix components'))
                
                cursor.execute(f'DELETE FROM concrete_mix_reference WHERE mix_id IN (SELECT mix_id FROM concrete_mix WHERE dataset_id={dataset_id})')
                self.stdout.write(self.style.SUCCESS('Deleted mix references'))
                
                cursor.execute(f'DELETE FROM staging_raw WHERE dataset_id={dataset_id}')
                self.stdout.write(self.style.SUCCESS('Deleted staging data'))
                
                # Then delete parent tables
                cursor.execute(f'DELETE FROM concrete_mix WHERE dataset_id={dataset_id}')
                self.stdout.write(self.style.SUCCESS('Deleted concrete mixes'))
                
                cursor.execute(f'DELETE FROM dataset WHERE dataset_id={dataset_id}')
                self.stdout.write(self.style.SUCCESS('Deleted dataset entry'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully purged {dataset_code} dataset and all related data'))
