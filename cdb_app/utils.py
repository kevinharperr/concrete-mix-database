# cdb_app/utils.py

from decimal import Decimal
import re

# Define EN and ASTM strength classes for use without requiring DB schema changes
# These can be used until the database migrations are resolved
EN_STRENGTH_CLASSES = [
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

ASTM_STRENGTH_CLASSES = [
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

# Constants for strength units
MPA_TO_PSI = Decimal('145.038')  # Conversion factor from MPa to psi
PSI_TO_MPA = Decimal('0.00689476')  # Conversion factor from psi to MPa

def classify_strength_by_reported_class(reported_class):
    """
    Attempts to match a reported strength class to standard EN or ASTM classes.
    
    Args:
        reported_class: String representing a strength class (e.g., 'C25/30', '4000')
        
    Returns:
        Tuple of (standard, class_code, min_strength, max_strength, description) or None if no match
    """
    if not reported_class:
        return None
    
    # Check if it's an EN class format (e.g., C25/30)
    en_pattern = re.compile(r'C(\d+)/(\d+)', re.IGNORECASE)
    en_match = en_pattern.match(reported_class)
    
    if en_match:
        for class_code, min_strength, max_strength, description in EN_STRENGTH_CLASSES:
            if class_code.lower() == reported_class.lower() or class_code.lower() == 'c' + reported_class.lower():
                return ('EN', class_code, min_strength, max_strength, description)
    
    # Check if it's an ASTM class (just a number, typically in psi)
    astm_pattern = re.compile(r'(\d+)', re.IGNORECASE)
    astm_match = astm_pattern.match(reported_class)
    
    if astm_match and not '/' in reported_class:  # Ensure it's not an EN class with the C missing
        psi_value = int(astm_match.group(1))
        for class_code, min_strength, max_strength, description in ASTM_STRENGTH_CLASSES:
            if int(class_code) == psi_value:
                return ('ASTM', class_code, min_strength, max_strength, description)
    
    return None

def classify_strength_by_test_result(strength_value_mpa):
    """
    Determines the strength class based on a 28-day compressive strength test result.
    
    Args:
        strength_value_mpa: Compressive strength in MPa
        
    Returns:
        Dict with EN and ASTM classifications if applicable
    """
    if not strength_value_mpa:
        return None
    
    try:
        strength_mpa = Decimal(str(strength_value_mpa))
        strength_psi = strength_mpa * MPA_TO_PSI
        
        classifications = {
            'EN': None,
            'ASTM': None
        }
        
        # Find EN class
        for class_code, min_strength, max_strength, description in EN_STRENGTH_CLASSES:
            if min_strength <= strength_mpa and (max_strength is None or strength_mpa <= max_strength):
                classifications['EN'] = (class_code, min_strength, max_strength, description)
                break
        
        # Find ASTM class
        for class_code, min_strength, max_strength, description in ASTM_STRENGTH_CLASSES:
            if min_strength <= strength_psi and (max_strength is None or strength_psi <= max_strength):
                classifications['ASTM'] = (class_code, min_strength, max_strength, description)
                break
        
        return classifications
    except (ValueError, TypeError):
        return None
