# Script to check actual database values

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

from cdb_app.models import ConcreteMix

# Check some of the mixes we attempted to update
mix_ids = [13560, 911, 5596, 225, 987]

print("Current database w/b ratio values:")
for mix_id in mix_ids:
    try:
        mix = ConcreteMix.objects.get(mix_id=mix_id)
        print(f"Mix ID: {mix.mix_id}, Mix Code: {mix.mix_code}, w/b ratio: {mix.w_b_ratio}")
    except ConcreteMix.DoesNotExist:
        print(f"Mix ID {mix_id} not found")
