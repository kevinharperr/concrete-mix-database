# Generated manually
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('concrete_mix_app', '0002_alter_mixcomposition_options'),
    ]

    operations = [
        migrations.RunSQL(
            """
            SELECT setval('mixcomposition_composition_id_seq', 
                  (SELECT COALESCE(MAX(composition_id), 1) FROM mixcomposition), 
                  true);
            """,
            reverse_sql=""
        ),
    ]
