# cdb_app/management/commands/populate_strength_classes.py

from django.core.management.base import BaseCommand
from cdb_app.models import StrengthClass
from decimal import Decimal


class Command(BaseCommand):
    help = 'Populates the database with standardized concrete strength classes from EN and ASTM standards'

    def handle(self, *args, **options):
        # Clear existing data
        StrengthClass.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Cleared existing strength classes'))

        # Define EN strength classes (European Standard EN 206-1)
        en_classes = [
            # class_code, min_strength (MPa), max_strength (MPa), description
            ('C8/10', 8, 10, 'Low strength concrete, suitable for non-structural applications'),
            ('C12/15', 12, 15, 'Basic concrete for foundation works'),
            ('C16/20', 16, 20, 'Standard concrete for light reinforced structures'),
            ('C20/25', 20, 25, 'Standard concrete for general reinforced structures'),
            ('C25/30', 25, 30, 'Standard concrete for reinforced structural elements'),
            ('C30/37', 30, 37, 'High strength concrete for heavily loaded elements'),
            ('C35/45', 35, 45, 'High strength concrete for critical structural elements'),
            ('C40/50', 40, 50, 'High strength concrete for high-rise buildings'),
            ('C45/55', 45, 55, 'Very high strength concrete for special applications'),
            ('C50/60', 50, 60, 'Very high strength concrete for special applications'),
            ('C55/67', 55, 67, 'Ultra high strength concrete'),
            ('C60/75', 60, 75, 'Ultra high strength concrete'),
            ('C70/85', 70, 85, 'Ultra high strength concrete'),
            ('C80/95', 80, 95, 'Ultra high strength concrete'),
            ('C90/105', 90, 105, 'Ultra high strength concrete'),
            ('C100/115', 100, 115, 'Ultra high strength concrete'),
        ]

        # Define ASTM strength classes (based on ASTM C39/ACI 318)
        # Typical concrete strength classes in psi (convert to MPa for display)
        astm_classes = [
            # class_code, min_strength (psi), max_strength (psi), description
            ('2500', 2500, None, 'Non-structural concrete (17.2 MPa)'),
            ('3000', 3000, None, 'Residential foundations and slabs (20.7 MPa)'),
            ('3500', 3500, None, 'Commercial foundation walls and footings (24.1 MPa)'),
            ('4000', 4000, None, 'Standard commercial structural concrete (27.6 MPa)'),
            ('4500', 4500, None, 'Bridge deck overlays and parking structures (31.0 MPa)'),
            ('5000', 5000, None, 'Heavy industrial floors and water-retaining structures (34.5 MPa)'),
            ('6000', 6000, None, 'High strength concrete for demanding applications (41.4 MPa)'),
            ('8000', 8000, None, 'High-rise buildings and special performance (55.2 MPa)'),
            ('10000', 10000, None, 'Ultra-high performance concrete (68.9 MPa)'),
            ('12000', 12000, None, 'Specialized applications requiring extremely high strength (82.7 MPa)'),
        ]

        # Insert EN classes
        for code, min_strength, max_strength, description in en_classes:
            StrengthClass.objects.create(
                standard=StrengthClass.STANDARD_EN,
                class_code=code,
                min_strength=Decimal(str(min_strength)),
                max_strength=Decimal(str(max_strength)) if max_strength else None,
                description=description
            )

        # Insert ASTM classes
        for code, min_strength, max_strength, description in astm_classes:
            StrengthClass.objects.create(
                standard=StrengthClass.STANDARD_ASTM,
                class_code=code,
                min_strength=Decimal(str(min_strength)),
                max_strength=Decimal(str(max_strength)) if max_strength else None,
                description=description
            )

        self.stdout.write(self.style.SUCCESS(
            f'Successfully added {len(en_classes)} EN and {len(astm_classes)} ASTM strength classes'
        ))
