"""
Configuration file for OCR Pipeline

This file contains all the customizable settings for improving OCR accuracy.
You can modify these settings without changing the core pipeline code.

For Python beginners:
- This centralizes all configuration in one place
- Easy to modify driver lists, vehicle IDs, and parsing rules
- Helps improve accuracy by providing known values to match against
"""

from typing import List, Dict, Any

# =============================================================================
# DRIVER INFORMATION
# =============================================================================

# List of known drivers - OCR will try to match against these names
# Add your actual driver names here for better accuracy
KNOWN_DRIVERS = [
    # IMPORTANT: Replace these with your actual driver names!
    # The more accurate this list, the better the OCR results
    # Based on OCR analysis - Real drivers and laborers:
    "Delawar",
    "Farhad", 
    "Israfil",
    "Kabir",
    "Masud",        # labour name
    "Moashin",
    "Rubel Hossain",
    "Robel",
    "Sharif",       # labour name
    "Sorwar",
    "Mustafiz",
    "Mobarak"## labour name
]

# Common OCR mistakes for driver names (original -> corrected)
DRIVER_NAME_CORRECTIONS = {
    # Based on OCR analysis from your images:
    
    # Robel/Rubel variations
    "Robel Hoppain": "Robel",
    "Robel Hossain Labor Name": "Rubel Hossain", 
    "Robol Hopsain": "Rubel Hossain",
    "Rubel hossain": "Rubel Hossain",
    "robel": "Robel",
    "rubel": "Rubel Hossain",
    
    # Sonwan/Sorwar variations
    "Son Wan Labor Name": "Sorwar",
    "Sonwan Labour Name": "Sorwar", 
    "Sonwan": "Sorwar",
    "sonwan": "Sorwar",
    
    # Masud variations
    "Masud Instructions": "Masud",
    "masud": "Masud",
    
    # Moashin/Mhashin variations
    "Masti Mhshin": "Moashin",
    "Mha Shin": "Moashin",
    "Mhashin": "Moashin",
    "mhashin": "Moashin",
    "moashin": "Moashin",
    
    # Sharif variations
    "Sharit Instructions": "Sharif",
    "Sharrit Instructions": "Sharif",
    "sharit": "Sharif",
    "sharif": "Sharif",
    
    # Israfil variations
    "Iarofil": "Israfil",
    "ISRAFIL": "Israfil",
    "israfil": "Israfil",
    
    # Kabir variations
    "Krkin": "Kabir",
    "Kabin": "Kabir",
    "kabir": "Kabir",
    
    # Other variations
    "Delawar Time": "Delawar",
    "delawar": "Delawar",
    "Farhad Time": "Farhad", 
    "farhad": "Farhad",
    "Mustafiz Time": "Mustafiz",
    "mustafiz": "Mustafiz",
    "Mobarak Time": "Mobarak",
    "mobarak": "Mobarak",
    
    # Based on form analysis - new corrections
    "Robel Hossain": "Robel Hossain",  # Keep full name
    "MOBARAK": "Mobarak",
    "Labor Name": "",  # Remove this text when found
    "Labour Name": "",  # Remove this text when found
}

# =============================================================================
# VEHICLE INFORMATION  
# =============================================================================

# List of known vehicle IDs - helps identify correct vehicle numbers
KNOWN_VEHICLES = [
    "323194", "90037", "49232", "142136", "49213",
    "323310", "89822", "150263", "42186",
    
    # From form analysis - additional vehicle
    "292104",  # Vehicle from the form image
]

# Common OCR mistakes for vehicle IDs
VEHICLE_ID_CORRECTIONS = {
    # OCR often mistakes numbers for letters and vice versa
    "42I86": "42186",
    "421B6": "42186", 
    "42l86": "42186",
    "9OO37": "90037",
    "90O37": "90037",
    "9003?": "90037",
    "49Z32": "49232",
    "492B2": "49232",
    "49232": "49232",
    "I42136": "142136",
    "14213G": "142136",
    "142I36": "142136",
    "492I3": "49213",
    "49ZI3": "49213",
    "323I94": "323194",
    "32319A": "323194",
    "323310": "323310",
    "32331O": "323310",
    "898ZZ": "89822",
    "89B22": "89822",
    "I50263": "150263",
    "15O263": "150263",
    "150ZG3": "150263",
}

# =============================================================================
# PARSING CONFIGURATION
# =============================================================================

# Confidence thresholds for different types of matches
CONFIDENCE_THRESHOLDS = {
    "driver_name_fuzzy_match": 0.8,  # How similar names need to be (0-1)
    "vehicle_id_fuzzy_match": 0.85,
    "date_confidence": 0.9,
    "time_confidence": 0.8,
}

# Enhanced regex patterns for better extraction
ENHANCED_PATTERNS = {
    # More flexible date patterns
    "dates": [
        r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',
        r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',
        r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\b',
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})\b',
    ],
    
    # More flexible time patterns
    "times": [
        r'\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?\b',
        r'\b(\d{1,2})\.(\d{2})\s*(AM|PM|am|pm)?\b',
        r'\b(\d{1,2})\s*(AM|PM|am|pm)\b',  # Just hour with AM/PM
        r'\b(\d{1,2}):(\d{2})\b',  # 24-hour format
    ],
    
    # Enhanced vehicle patterns
    "vehicles": [
        r'\b[Vv]ehicle\s*[ID#:]*\s*([A-Z0-9]{3,10})\b',
        r'\b[Tt]ruck\s*[#:]*\s*([A-Z0-9]{3,10})\b',
        r'\b[Uu]nit\s*[#:]*\s*([A-Z0-9]{3,10})\b',
        r'\b[Cc]ar\s*[#:]*\s*([A-Z0-9]{3,10})\b',
        r'\b[Vv]an\s*[#:]*\s*([A-Z0-9]{3,10})\b',
        r'\b[Bb]us\s*[#:]*\s*([A-Z0-9]{3,10})\b',
        r'\b([A-Z]{2,4}\d{2,4})\b',  # Pattern like TRK001, VAN123
    ],
}

# =============================================================================
# LOCATION INFORMATION
# =============================================================================

# Known locations organized by category for better extraction
KNOWN_LOCATIONS = [
    # =============================================================================
    # CARREFOUR LOCATIONS
    # =============================================================================
    "Mall of Qatar",
    "Lagoona", 
    "Villago",
    "Landmark",
    "Mirqab",
    "City Center",
    "Dar Alsalam",
    
    # =============================================================================
    # SPAR LOCATIONS  
    # =============================================================================
    "Tawar Mall",
    "03 Mall",
    
    # =============================================================================
    # LULU LOCATIONS
    # =============================================================================
    "Ezdan",
    "Mashaf",
    "Messila", 
    "Pearl",
    "Madinatna (Barwa Family)",
    "Doha Mall",
    "Al Khor",
    "Umm Al Amad",
    "Gharafa",
    "Hilal",
    "Lusail",
    "B-Ring Road",
    "D-Ring Road", 
    "Salwa Road",
    "Barwa City",
    "Bin Mahmoud",
    "Center",
    "Ain Khaled",
    
    # =============================================================================
    # QATAR STAR LOCATIONS
    # =============================================================================
    "NCC",
    "Karwa", 
    "PTI",
    "CK 3",
    "Al Fazaa",
    "Abu Samra",
    "Souq Waqif",
    
    # =============================================================================
    # OTHER LOCATIONS
    # =============================================================================
    "Galaxy",
    "Store",
    "Al Azkyia", 
    "Sanwara",
    "Wakra",
    
    # From form analysis - additional locations
    "Al-Azkyia",     # Alternative spelling
    "Al-Hamma",      # From form
    "Feel Fresh",    # From form
]

# Common OCR mistakes for locations (original -> corrected)
LOCATION_CORRECTIONS = {
    # Carrefour locations
    "Mall ol Qatar": "Mall of Qatar",
    "Mall ot Qatar": "Mall of Qatar", 
    "Mall Qatar": "Mall of Qatar",
    "Lagoona Mall": "Lagoona",
    "lagona": "Lagoona",
    "Villago Mall": "Villago",
    "villago": "Villago",
    "Land Mark": "Landmark",
    "landmark": "Landmark",
    "mirqab": "Mirqab",
    "city center": "City Center",
    "City Centre": "City Center",
    "Dar Al Salam": "Dar Alsalam",
    "dar alsalam": "Dar Alsalam",
    
    # Spar locations
    "Tawar": "Tawar Mall",
    "tawar mall": "Tawar Mall",
    "O3 Mall": "03 Mall",
    "3 Mall": "03 Mall",
    
    # Lulu locations
    "ezdan": "Ezdan",
    "Ezdan Mall": "Ezdan",
    "mashaf": "Mashaf",
    "messila": "Messila",
    "pearl": "Pearl",
    "Pearl Qatar": "Pearl",
    "Madinatna": "Madinatna (Barwa Family)",
    "Barwa Family": "Madinatna (Barwa Family)",
    "doha mall": "Doha Mall",
    "al khor": "Al Khor",
    "alkhor": "Al Khor",
    "umm al amad": "Umm Al Amad",
    "gharafa": "Gharafa",
    "hilal": "Hilal",
    "lusail": "Lusail",
    "B Ring": "B-Ring Road",
    "B-Ring": "B-Ring Road",
    "D Ring": "D-Ring Road", 
    "D-Ring": "D-Ring Road",
    "salwa road": "Salwa Road",
    "Salwa Rd": "Salwa Road",
    "barwa city": "Barwa City",
    "bin mahmoud": "Bin Mahmoud",
    "center": "Center",
    "centre": "Center",
    "ain khaled": "Ain Khaled",
    
    # Qatar Star locations
    "ncc": "NCC",
    "karwa": "Karwa",
    "pti": "PTI",
    "ck3": "CK 3",
    "CK3": "CK 3",
    "al fazaa": "Al Fazaa",
    "abu samra": "Abu Samra",
    "souq waqif": "Souq Waqif",
    "Souk Waqif": "Souq Waqif",
    
    # Other locations
    "galaxy": "Galaxy",
    "store": "Store",
    "al azkyia": "Al Azkyia",
    "sanwara": "Sanwara",
    "wakra": "Wakra",
}

# =============================================================================
# DATA QUALITY SETTINGS
# =============================================================================

# Minimum confidence scores to accept extracted data
MIN_CONFIDENCE_SCORES = {
    "overall_extraction": 0.3,  # Minimum confidence to consider extraction valid
    "driver_name": 0.5,
    "date": 0.7,
    "time": 0.6,
    "vehicle_id": 0.6,
}

# Maximum reasonable values for validation
MAX_VALUES = {
    "miles_driven": 1000,  # Maximum miles per day
    "fuel_used": 100,      # Maximum gallons per day
    "hours_worked": 24,    # Maximum hours per day
}

# =============================================================================
# OCR PREPROCESSING SETTINGS
# =============================================================================

# Image preprocessing options (for future enhancement)
IMAGE_PREPROCESSING = {
    "enhance_contrast": True,
    "denoise": True,
    "rotate_correction": True,
    "resize_for_ocr": True,
}

# =============================================================================
# EXPORT SETTINGS
# =============================================================================

# Default export settings
EXPORT_SETTINGS = {
    "include_confidence_scores": True,
    "include_processing_notes": True,
    "group_by_driver": False,
    "sort_by_date": True,
}

# Excel formatting options
EXCEL_FORMATTING = {
    "highlight_low_confidence": True,
    "confidence_threshold_for_highlight": 0.7,
    "add_summary_charts": False,  # Future feature
    "freeze_header_row": True,
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_driver_variations(driver_name: str) -> List[str]:
    """
    Generate common variations of a driver name for fuzzy matching.
    
    Args:
        driver_name: The original driver name
        
    Returns:
        List of possible variations
    """
    variations = [driver_name]
    
    # Add variations without middle names, initials, etc.
    parts = driver_name.split()
    if len(parts) >= 2:
        variations.append(f"{parts[0]} {parts[-1]}")  # First and last name only
        variations.append(f"{parts[0][0]}. {parts[-1]}")  # First initial + last name
        variations.append(f"{parts[0]} {parts[-1][0]}.")  # First name + last initial
    
    return variations

def get_location_category(location: str) -> str:
    """
    Get the category (company) for a given location.
    
    Args:
        location: The location name
        
    Returns:
        The category/company name
    """
    # Carrefour locations
    carrefour_locations = [
        "Mall of Qatar", "Lagoona", "Villago", "Landmark", 
        "Mirqab", "City Center", "Dar Alsalam"
    ]
    
    # Spar locations  
    spar_locations = ["Tawar Mall", "03 Mall"]
    
    # Lulu locations
    lulu_locations = [
        "Ezdan", "Mashaf", "Messila", "Pearl", "Madinatna (Barwa Family)",
        "Doha Mall", "Al Khor", "Umm Al Amad", "Gharafa", "Hilal", "Lusail",
        "B-Ring Road", "D-Ring Road", "Salwa Road", "Barwa City", 
        "Bin Mahmoud", "Center", "Ain Khaled"
    ]
    
    # Qatar Star locations
    qatar_star_locations = [
        "NCC", "Karwa", "PTI", "CK 3", "Al Fazaa", "Abu Samra", "Souq Waqif"
    ]
    
    if location in carrefour_locations:
        return "Carrefour"
    elif location in spar_locations:
        return "Spar" 
    elif location in lulu_locations:
        return "Lulu"
    elif location in qatar_star_locations:
        return "Qatar Star"
    else:
        return "Other"

def is_reasonable_value(field_name: str, value: Any) -> bool:
    """
    Check if an extracted value is reasonable.
    
    Args:
        field_name: Name of the field being checked
        value: The value to validate
        
    Returns:
        True if the value seems reasonable
    """
    if value is None:
        return True
    
    if field_name == "miles_driven":
        return 0 <= float(value) <= MAX_VALUES["miles_driven"]
    elif field_name == "fuel_used":
        return 0 <= float(value) <= MAX_VALUES["fuel_used"]
    
    return True
