"""
Enhanced Driver Log Parser with Fuzzy Matching and Known Driver Lists

This enhanced parser improves accuracy by:
- Using fuzzy matching against known driver lists
- Better pattern recognition for dates, times, and vehicle IDs
- Confidence scoring for extracted data
- Data validation and correction

For Python beginners:
- Fuzzy matching finds the closest match from a known list
- Confidence scores help identify reliable vs uncertain data
- Multiple validation steps ensure data quality
"""

import re
from datetime import date, datetime, time
from typing import List, Optional, Tuple, Dict, Any
from fuzzywuzzy import fuzz, process
from schemas.driver_log_schema import DriverLogEntry, DriverLogData, LocationVisit
from config import (
    KNOWN_DRIVERS, KNOWN_VEHICLES, KNOWN_LOCATIONS,
    DRIVER_NAME_CORRECTIONS, VEHICLE_ID_CORRECTIONS, LOCATION_CORRECTIONS,
    CONFIDENCE_THRESHOLDS, ENHANCED_PATTERNS,
    MIN_CONFIDENCE_SCORES, is_reasonable_value, get_location_category
)


class EnhancedDriverLogParser:
    """
    Enhanced parser with fuzzy matching and improved accuracy.
    
    This parser uses machine learning techniques and known data lists
    to significantly improve extraction accuracy.
    """
    
    def __init__(self):
        """Initialize the enhanced parser with improved patterns and configurations."""
        
        # Use enhanced patterns from config
        self.date_patterns = ENHANCED_PATTERNS["dates"]
        self.time_patterns = ENHANCED_PATTERNS["times"]
        self.vehicle_patterns = ENHANCED_PATTERNS["vehicles"]
        
        # Enhanced patterns for better extraction
        self.miles_patterns = [
            r'\b(\d+\.?\d*)\s*miles?\b',
            r'\b[Mm]iles?[:\s]*(\d+\.?\d*)\b',
            r'\b[Dd]istance[:\s]*(\d+\.?\d*)\b',
            r'\b[Kk]m[:\s]*(\d+\.?\d*)\b',  # Kilometers
            r'\b(\d+\.?\d*)\s*[Kk]m\b',
        ]
        
        self.fuel_patterns = [
            r'\b(\d+\.?\d*)\s*gal(lon)?s?\b',
            r'\b[Ff]uel[:\s]*(\d+\.?\d*)\b',
            r'\b[Gg]as[:\s]*(\d+\.?\d*)\b',
            r'\b[Ll]itr?e?s?[:\s]*(\d+\.?\d*)\b',  # Liters
            r'\b(\d+\.?\d*)\s*[Ll]\b',
        ]
        
        print("🔧 Enhanced parser initialized with fuzzy matching")
        print(f"   - Known drivers: {len(KNOWN_DRIVERS)}")
        print(f"   - Known vehicles: {len(KNOWN_VEHICLES)}")
        print(f"   - Known locations: {len(KNOWN_LOCATIONS)}")
    
    def parse_document(self, ocr_text: str, source_file: str, ocr_confidence: Optional[float] = None) -> DriverLogData:
        """
        Enhanced document parsing with fuzzy matching and validation.
        
        Args:
            ocr_text: Raw text from OCR
            source_file: Name of the original image file
            ocr_confidence: OCR confidence score (0-1)
            
        Returns:
            DriverLogData object with enhanced extraction results
        """
        
        # Create the main data container
        log_data = DriverLogData(
            source_file=source_file,
            extraction_date=date.today(),
            ocr_confidence=ocr_confidence
        )
        
        # Preprocess the OCR text for better extraction
        cleaned_text = self._preprocess_ocr_text(ocr_text)
        
        # Split text into potential log entries
        entry_blocks = self._split_into_entries(cleaned_text)
        
        processing_notes = []
        total_confidence = 0
        valid_entries = 0
        
        for i, block in enumerate(entry_blocks):
            try:
                entry, confidence = self._parse_single_entry_with_confidence(block)
                if entry and confidence >= MIN_CONFIDENCE_SCORES["overall_extraction"]:
                    log_data.add_entry(entry)
                    total_confidence += confidence
                    valid_entries += 1
                    processing_notes.append(f"Entry {i+1}: extracted with {confidence:.2f} confidence")
                else:
                    confidence_msg = f"{confidence:.2f}" if confidence else "0.00"
                    processing_notes.append(f"Entry {i+1}: rejected (confidence: {confidence_msg})")
            except Exception as e:
                processing_notes.append(f"Entry {i+1}: error - {str(e)}")
        
        # Calculate average confidence
        if valid_entries > 0:
            avg_confidence = total_confidence / valid_entries
            log_data.ocr_confidence = avg_confidence
        
        log_data.processing_notes = "; ".join(processing_notes)
        return log_data
    
    def _preprocess_ocr_text(self, text: str) -> str:
        """
        Clean and preprocess OCR text for better extraction.
        
        Args:
            text: Raw OCR text
            
        Returns:
            Cleaned text
        """
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        
        # Fix common OCR mistakes
        corrections = {
            'O': '0',  # Letter O to number 0 in contexts
            'l': '1',  # Letter l to number 1 in contexts
            'S': '5',  # Letter S to number 5 in contexts
            'G': '6',  # Letter G to number 6 in contexts
        }
        
        # Apply corrections in numeric contexts
        for mistake, correction in corrections.items():
            # Fix in time contexts (like 1O:30 -> 10:30)
            text = re.sub(f'(\\d){mistake}(\\d)', f'\\1{correction}\\2', text)
            text = re.sub(f'(\\d){mistake}:', f'\\1{correction}:', text)
        
        return text.strip()
    
    def _parse_single_entry_with_confidence(self, text: str) -> Tuple[Optional[DriverLogEntry], float]:
        """
        Parse a single entry with confidence scoring.
        
        Args:
            text: Text block to parse
            
        Returns:
            Tuple of (DriverLogEntry, confidence_score)
        """
        
        confidence_scores = []
        
        # Extract each field with confidence
        driver_name, driver_conf = self._extract_driver_name_fuzzy(text)
        log_date, date_conf = self._extract_date_with_confidence(text)
        vehicle_id, vehicle_conf = self._extract_vehicle_id_fuzzy(text)
        start_time, end_time, time_conf = self._extract_times_with_confidence(text)
        start_location, end_location, location_conf = self._extract_locations_fuzzy(text)
        miles_driven, miles_conf = self._extract_miles_with_confidence(text)
        fuel_used, fuel_conf = self._extract_fuel_with_confidence(text)
        notes = self._extract_notes(text)
        
        # Collect confidence scores
        if driver_conf > 0:
            confidence_scores.append(driver_conf)
        if date_conf > 0:
            confidence_scores.append(date_conf)
        if vehicle_conf > 0:
            confidence_scores.append(vehicle_conf)
        if time_conf > 0:
            confidence_scores.append(time_conf)
        if location_conf > 0:
            confidence_scores.append(location_conf)
        if miles_conf > 0:
            confidence_scores.append(miles_conf)
        if fuel_conf > 0:
            confidence_scores.append(fuel_conf)
        
        # Calculate overall confidence
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # Must have at least a driver name or date to be valid
        if not driver_name and not log_date:
            return None, 0.0
        
        # Validate extracted values
        if not is_reasonable_value("miles_driven", miles_driven):
            miles_driven = None
        if not is_reasonable_value("fuel_used", fuel_used):
            fuel_used = None
        
        try:
            entry = DriverLogEntry(
                driver_name=driver_name or "Unknown Driver",
                log_date=log_date or date.today(),
                vehicle_id=vehicle_id,
                start_time=start_time,
                end_time=end_time,
                start_location=start_location,
                end_location=end_location,
                miles_driven=miles_driven,
                fuel_used=fuel_used,
                notes=notes
            )
            return entry, overall_confidence
        except Exception as e:
            print(f"Validation error: {e}")
            return None, 0.0
    
    def _extract_driver_name_fuzzy(self, text: str) -> Tuple[Optional[str], float]:
        """
        Extract driver name using fuzzy matching against known drivers.
        
        Args:
            text: Text to search in
            
        Returns:
            Tuple of (driver_name, confidence_score)
        """
        
        # First try exact corrections
        for mistake, correction in DRIVER_NAME_CORRECTIONS.items():
            if mistake.lower() in text.lower():
                return correction, 0.95
        
        # Extract potential names using patterns
        name_patterns = [
            r'[Dd]river[:\s]*([A-Za-z\s]{2,30})',
            r'[Nn]ame[:\s]*([A-Za-z\s]{2,30})',
            r'[Oo]perator[:\s]*([A-Za-z\s]{2,30})',
            r'[Ee]mployee[:\s]*([A-Za-z\s]{2,30})',
        ]
        
        potential_names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                clean_name = match.strip()
                if len(clean_name.split()) >= 2:  # At least first and last name
                    potential_names.append(clean_name)
        
        # Also look for capitalized words that might be names
        words = text.split()
        for i in range(len(words) - 1):
            if (words[i][0].isupper() and words[i+1][0].isupper() and 
                len(words[i]) > 2 and len(words[i+1]) > 2):
                potential_names.append(f"{words[i]} {words[i+1]}")
        
        if not potential_names:
            return None, 0.0
        
        # Use fuzzy matching to find the best match
        best_match = None
        best_score = 0
        
        for potential_name in potential_names:
            # Try fuzzy matching against known drivers
            match_result = process.extractOne(potential_name, KNOWN_DRIVERS, scorer=fuzz.ratio)
            if match_result and match_result[1] >= CONFIDENCE_THRESHOLDS["driver_name_fuzzy_match"] * 100:
                if match_result[1] > best_score:
                    best_match = match_result[0]
                    best_score = match_result[1]
        
        if best_match:
            return best_match, best_score / 100.0
        
        # If no good fuzzy match, return the most reasonable looking name
        for name in potential_names:
            if re.match(r'^[A-Za-z\s]+$', name) and 5 <= len(name) <= 30:
                return name.title(), 0.3  # Low confidence for unknown names
        
        return None, 0.0
    
    def _extract_vehicle_id_fuzzy(self, text: str) -> Tuple[Optional[str], float]:
        """
        Extract vehicle ID using fuzzy matching against known vehicles.
        
        Args:
            text: Text to search in
            
        Returns:
            Tuple of (vehicle_id, confidence_score)
        """
        
        # First try exact corrections
        for mistake, correction in VEHICLE_ID_CORRECTIONS.items():
            if mistake in text:
                return correction, 0.95
        
        # Extract potential vehicle IDs
        potential_ids = []
        for pattern in self.vehicle_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            potential_ids.extend(matches)
        
        if not potential_ids:
            return None, 0.0
        
        # Use fuzzy matching against known vehicles
        best_match = None
        best_score = 0
        
        for potential_id in potential_ids:
            clean_id = potential_id.upper().strip()
            match_result = process.extractOne(clean_id, KNOWN_VEHICLES, scorer=fuzz.ratio)
            if match_result and match_result[1] >= CONFIDENCE_THRESHOLDS["vehicle_id_fuzzy_match"] * 100:
                if match_result[1] > best_score:
                    best_match = match_result[0]
                    best_score = match_result[1]
        
        if best_match:
            return best_match, best_score / 100.0
        
        # Return the most reasonable looking ID even if not in known list
        for vehicle_id in potential_ids:
            clean_id = vehicle_id.upper().strip()
            if re.match(r'^[A-Z0-9]{3,10}$', clean_id):
                return clean_id, 0.4  # Low confidence for unknown vehicles
        
        return None, 0.0
    
    def _extract_date_with_confidence(self, text: str) -> Tuple[Optional[date], float]:
        """Extract date with confidence scoring."""
        
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if pattern.startswith(r'\b(\d{4})'):  # YYYY-MM-DD format
                            year, month, day = groups
                        elif 'Jan|Feb|Mar' in pattern:  # Month name formats
                            if groups[2].isdigit():  # DD Mon YYYY
                                day, month_name, year = groups
                            else:  # Mon DD, YYYY
                                month_name, day, year = groups
                            month_map = {
                                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                            }
                            month = str(month_map.get(month_name, 1))
                        else:  # MM/DD/YYYY format
                            month, day, year = groups
                        
                        extracted_date = date(int(year), int(month), int(day))
                        
                        # Higher confidence for recent dates
                        today = date.today()
                        days_diff = abs((today - extracted_date).days)
                        if days_diff <= 30:
                            confidence = 0.9
                        elif days_diff <= 365:
                            confidence = 0.7
                        else:
                            confidence = 0.5
                        
                        return extracted_date, confidence
                        
                except (ValueError, KeyError):
                    continue
        
        return None, 0.0
    
    def _extract_times_with_confidence(self, text: str) -> Tuple[Optional[time], Optional[time], float]:
        """Extract start and end times with confidence scoring."""
        
        times_found = []
        
        for pattern in self.time_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    groups = match.groups()
                    if len(groups) >= 2:
                        hour = int(groups[0])
                        minute = int(groups[1]) if groups[1] else 0
                        am_pm = groups[2] if len(groups) > 2 else None
                        
                        # Convert to 24-hour format
                        if am_pm and am_pm.upper() == 'PM' and hour != 12:
                            hour += 12
                        elif am_pm and am_pm.upper() == 'AM' and hour == 12:
                            hour = 0
                        
                        if 0 <= hour <= 23 and 0 <= minute <= 59:
                            times_found.append(time(hour, minute))
                except (ValueError, IndexError):
                    continue
        
        # Return first two times as start and end
        start_time = times_found[0] if len(times_found) > 0 else None
        end_time = times_found[1] if len(times_found) > 1 else None
        
        # Confidence based on how many times were found and their reasonableness
        if len(times_found) >= 2:
            confidence = 0.8
        elif len(times_found) == 1:
            confidence = 0.6
        else:
            confidence = 0.0
        
        return start_time, end_time, confidence
    
    def _extract_locations_fuzzy(self, text: str) -> Tuple[Optional[str], Optional[str], float]:
        """Extract locations using fuzzy matching against known locations."""
        
        location_patterns = [
            r'[Ss]tart[:\s]*([A-Za-z0-9\s,.-]{5,50})',
            r'[Ff]rom[:\s]*([A-Za-z0-9\s,.-]{5,50})',
            r'[Ee]nd[:\s]*([A-Za-z0-9\s,.-]{5,50})',
            r'[Tt]o[:\s]*([A-Za-z0-9\s,.-]{5,50})',
        ]
        
        potential_locations = []
        for pattern in location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            potential_locations.extend(matches)
        
        if not potential_locations:
            return None, None, 0.0
        
        # Use fuzzy matching against known locations
        start_location = None
        end_location = None
        confidence_scores = []
        
        for location in potential_locations[:2]:  # Take first two locations
            clean_location = location.strip()
            if KNOWN_LOCATIONS:
                match_result = process.extractOne(clean_location, KNOWN_LOCATIONS, scorer=fuzz.partial_ratio)
                if match_result and match_result[1] >= 70:  # 70% similarity
                    if start_location is None:
                        start_location = match_result[0]
                    else:
                        end_location = match_result[0]
                    confidence_scores.append(match_result[1] / 100.0)
                else:
                    # Use original location even if not in known list
                    if start_location is None:
                        start_location = clean_location
                    else:
                        end_location = clean_location
                    confidence_scores.append(0.3)
            else:
                # No known locations to match against
                if start_location is None:
                    start_location = clean_location
                else:
                    end_location = clean_location
                confidence_scores.append(0.5)
        
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        return start_location, end_location, overall_confidence
    
    def _extract_miles_with_confidence(self, text: str) -> Tuple[Optional[float], float]:
        """Extract miles with confidence scoring and validation."""
        
        for pattern in self.miles_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    miles = float(match.group(1))
                    if 0 <= miles <= 1000:  # Reasonable daily miles
                        confidence = 0.8 if miles <= 500 else 0.6
                        return miles, confidence
                except ValueError:
                    continue
        
        return None, 0.0
    
    def _extract_fuel_with_confidence(self, text: str) -> Tuple[Optional[float], float]:
        """Extract fuel consumption with confidence scoring and validation."""
        
        for pattern in self.fuel_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    fuel = float(match.group(1))
                    if 0 <= fuel <= 100:  # Reasonable daily fuel consumption
                        confidence = 0.8 if fuel <= 50 else 0.6
                        return fuel, confidence
                except ValueError:
                    continue
        
        return None, 0.0
    
    def _split_into_entries(self, text: str) -> List[str]:
        """Split text into potential log entries (same as original parser)."""
        
        # Clean up the text first
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Try to split by dates
        date_splits = []
        for pattern in self.date_patterns:
            matches = list(re.finditer(pattern, text))
            if matches:
                last_end = 0
                for match in matches:
                    if last_end < match.start():
                        if date_splits:
                            date_splits[-1] += text[last_end:match.start()]
                    date_splits.append(text[match.start():])
                    last_end = match.end()
                break
        
        if date_splits:
            return date_splits
        
        # Fallback to line-based splitting
        lines = text.split('\n')
        entries = []
        current_entry = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Start new entry on date or driver patterns
            if (any(re.search(pattern, line) for pattern in self.date_patterns) or
                re.search(r'\b[Dd]river\b', line) or
                re.search(r'\b[Nn]ame\b', line)):
                
                if current_entry:
                    entries.append(' '.join(current_entry))
                    current_entry = []
            
            current_entry.append(line)
        
        if current_entry:
            entries.append(' '.join(current_entry))
        
        return entries if entries else [text]
    
    def _extract_notes(self, text: str) -> Optional[str]:
        """Extract notes/comments from text (same as original parser)."""
        
        notes_patterns = [
            r'[Nn]otes?[:\s]*([A-Za-z0-9\s,.-]{10,200})',
            r'[Cc]omments?[:\s]*([A-Za-z0-9\s,.-]{10,200})',
            r'[Rr]emarks?[:\s]*([A-Za-z0-9\s,.-]{10,200})',
        ]
        
        for pattern in notes_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_location_visits(self, text: str, source_file: str = "unknown") -> List[LocationVisit]:
        """
        Extract individual location visits from OCR text.
        Each location visit becomes a separate record.
        
        Args:
            text: Raw OCR text from the image
            source_file: Name of the source image file
            
        Returns:
            List of LocationVisit objects
        """
        visits = []
        
        try:
            # Extract basic information that applies to all visits
            driver_name, _ = self._extract_driver_name_fuzzy(text)
            log_date, _ = self._extract_date_with_confidence(text)
            vehicle_id, _ = self._extract_vehicle_id_fuzzy(text)
            labor_name = self._extract_labor_name_from_form(text)
            
            if not driver_name:
                driver_name = "Unknown Driver"
            if not log_date:
                log_date = date.today()
            
            # Enhanced pattern to find location-time combinations
            location_time_patterns = [
                # Pattern: Location Time Time (e.g., "Al Khor 7:45 AM 9:40 AM")
                r'([A-Za-z\s]{3,25})\s+(\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?)\s+(\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?)',
                
                # Pattern: Time Location Time (e.g., "7:45 Al Khor 9:40")
                r'(\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?)\s+([A-Za-z\s]{3,25})\s+(\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?)',
                
                # Pattern: Location Time (single time)
                r'([A-Za-z\s]{3,25})\s+(\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?)',
            ]
            
            # Add pattern for known locations
            if KNOWN_LOCATIONS:
                known_locations_pattern = r'((?:' + '|'.join(re.escape(loc) for loc in KNOWN_LOCATIONS) + r'))\s*(\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?)\s*(\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?)?'
                location_time_patterns.append(known_locations_pattern)
            
            visit_sequence = 1
            
            # Try each pattern
            for pattern in location_time_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    groups = match.groups()
                    location = None
                    arrival_time = None
                    departure_time = None
                    
                    # Parse based on pattern structure
                    if len(groups) >= 3 and groups[2]:
                        if re.match(r'\d', groups[0]):  # First group is time
                            arrival_time = self._parse_time(groups[0])
                            location = groups[1].strip()
                            departure_time = self._parse_time(groups[2])
                        else:  # First group is location
                            location = groups[0].strip()
                            arrival_time = self._parse_time(groups[1])
                            departure_time = self._parse_time(groups[2])
                    elif len(groups) >= 2:
                        if re.match(r'\d', groups[0]):  # First group is time
                            arrival_time = self._parse_time(groups[0])
                            location = groups[1].strip()
                        else:  # First group is location
                            location = groups[0].strip()
                            arrival_time = self._parse_time(groups[1])
                    
                    # Clean and validate location
                    if location and len(location.strip()) > 2:
                        location = location.strip()
                        
                        # Apply location corrections
                        for mistake, correction in LOCATION_CORRECTIONS.items():
                            if mistake.lower() in location.lower():
                                location = correction
                                print(f"🔧 Corrected location '{mistake}' to '{correction}'")
                                break
                        
                        # Try fuzzy matching against known locations
                        if KNOWN_LOCATIONS:
                            match_result = process.extractOne(location, KNOWN_LOCATIONS, scorer=fuzz.partial_ratio)
                            if match_result and match_result[1] >= 70:
                                matched_location = match_result[0]
                                if matched_location != location:
                                    print(f"🎯 Fuzzy matched location '{location}' to '{matched_location}' (score: {match_result[1]})")
                                    location = matched_location
                        
                        # Get location category
                        location_category = get_location_category(location)
                        
                        # Create location visit
                        visit = LocationVisit(
                            driver_name=driver_name,
                            log_date=log_date,
                            location=location,
                            arrival_time=arrival_time,
                            departure_time=departure_time,
                            vehicle_id=vehicle_id,
                            labor_name=labor_name,
                            location_category=location_category,
                            source_image=source_file,
                            visit_sequence=visit_sequence,
                            notes=f"Extracted from {source_file}"
                        )
                        
                        visits.append(visit)
                        visit_sequence += 1
                        
                        print(f"📍 Found visit: {driver_name} -> {location} ({location_category}) {arrival_time or 'N/A'}-{departure_time or 'N/A'}")
            
            # If no structured visits found, try to extract locations and times separately
            if not visits:
                locations = self._extract_all_locations_from_text(text)
                times = self._extract_all_times_from_text(text)
                
                # Pair locations with times if we have them
                for i, location in enumerate(locations):
                    arrival_time = times[i*2] if i*2 < len(times) else None
                    departure_time = times[i*2+1] if i*2+1 < len(times) else None
                    
                    location_category = get_location_category(location)
                    
                    visit = LocationVisit(
                        driver_name=driver_name,
                        log_date=log_date,
                        location=location,
                        arrival_time=arrival_time,
                        departure_time=departure_time,
                        vehicle_id=vehicle_id,
                        labor_name=labor_name,
                        location_category=location_category,
                        source_image=source_file,
                        visit_sequence=i+1,
                        notes=f"Extracted from {source_file} (fallback method)"
                    )
                    
                    visits.append(visit)
                    print(f"📍 Found visit (fallback): {driver_name} -> {location} ({location_category})")
                    
        except Exception as e:
            print(f"❌ Error extracting location visits: {str(e)}")
            
        return visits

    def extract_from_structured_form(self, text: str, source_file: str = "unknown") -> List[LocationVisit]:
        """
        Enhanced extraction specifically for the structured driver log forms.
        Handles the table format with Time Arrived | Time Departed | Location & Purpose columns.
        
        Args:
            text: Raw OCR text from the structured form
            source_file: Name of the source image file
            
        Returns:
            List of LocationVisit objects
        """
        visits = []
        
        try:
            # Extract header information using enhanced methods
            driver_name = self._extract_driver_name_from_form(text)
            vehicle_id = self._extract_vehicle_from_form(text)
            log_date = self._extract_date_from_form(text)
            labor_name = self._extract_labor_name_from_form(text)
            
            if not driver_name:
                driver_name = "Unknown Driver"
            if not log_date:
                log_date = date.today()
            
            # Look for table data - more structured approach
            table_rows = self._extract_table_rows(text)
            
            visit_sequence = 1
            for row in table_rows:
                arrival_time = self._parse_time(row.get('time_arrived'))
                departure_time = self._parse_time(row.get('time_departed'))
                location = row.get('location')
                notes = row.get('notes', '')
                
                if location and location.strip():
                    # Clean and correct location
                    location = self._clean_location(location)
                    location_category = get_location_category(location)
                    
                    visit = LocationVisit(
                        driver_name=driver_name,
                        log_date=log_date,
                        location=location,
                        arrival_time=arrival_time,
                        departure_time=departure_time,
                        vehicle_id=vehicle_id,
                        labor_name=labor_name,
                        location_category=location_category,
                        source_image=source_file,
                        visit_sequence=visit_sequence,
                        notes=notes
                    )
                    
                    visits.append(visit)
                    visit_sequence += 1
                    print(f"📋 Form visit: {driver_name} -> {location} ({location_category}) {arrival_time or 'N/A'}-{departure_time or 'N/A'}")
            
        except Exception as e:
            print(f"❌ Error extracting from structured form: {str(e)}")
            # Fallback to regular extraction
            return self.extract_location_visits(text, source_file)
            
        return visits if visits else self.extract_location_visits(text, source_file)

    def _parse_time(self, time_str: str) -> Optional[time]:
        """Parse a time string into a time object with better AM/PM handling."""
        if not time_str:
            return None
            
        time_str = time_str.strip().upper()
        
        # Enhanced time patterns with better AM/PM detection
        patterns = [
            r'(\d{1,2})[:.:](\d{2})\s*(AM|PM)',      # 12:30 AM/PM
            r'(\d{1,2})\s*(AM|PM)',                  # 12 AM/PM
            r'(\d{1,2})[:.:](\d{2})',                # 12:30 (24-hour assumed)
        ]
        
        for pattern in patterns:
            match = re.match(pattern, time_str)
            if match:
                try:
                    hour = int(match.group(1))
                    minute = int(match.group(2)) if len(match.groups()) >= 2 and match.group(2) and match.group(2).isdigit() else 0
                    am_pm = match.group(3) if len(match.groups()) >= 3 and match.group(3) else None
                    
                    # Convert to 24-hour format
                    if am_pm == 'PM' and hour != 12:
                        hour += 12
                    elif am_pm == 'AM' and hour == 12:
                        hour = 0
                    elif not am_pm and hour <= 12:
                        # If no AM/PM specified and hour is 1-12, try to guess based on context
                        # For now, assume times 1-7 are PM (13:00-19:00), 8-12 are AM
                        if 1 <= hour <= 7:
                            hour += 12
                    
                    # Validate hour and minute
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        return time(hour, minute)
                except (ValueError, IndexError, TypeError):
                    continue
        
        return None

    def _extract_all_locations_from_text(self, text: str) -> List[str]:
        """Extract all possible locations from text."""
        locations = []
        
        # Look for known locations in text
        for location in KNOWN_LOCATIONS:
            if location.lower() in text.lower():
                locations.append(location)
        
        # Look for correctable locations
        for mistake, correction in LOCATION_CORRECTIONS.items():
            if mistake.lower() in text.lower():
                locations.append(correction)
        
        return list(set(locations))  # Remove duplicates

    def _extract_all_times_from_text(self, text: str) -> List[time]:
        """Extract all possible times from text."""
        times = []
        
        # Time patterns
        time_patterns = [
            r'\b(\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm))\b',
            r'\b(\d{1,2}\s*(?:AM|PM|am|pm))\b',
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                parsed_time = self._parse_time(match)
                if parsed_time:
                    times.append(parsed_time)
        
        return times

    def _extract_driver_name_from_form(self, text: str) -> Optional[str]:
        """Extract driver name specifically from form header."""
        # Look for "Driver Name:" pattern - more specific patterns first
        patterns = [
            r'Driver Name[:\s]*([A-Za-z\s]{2,25})(?:\s*Time|\s*Labor|\s*Vehicle|\s*Date|\s*Instructions|$)',
            r'Driver[:\s]*([A-Za-z\s]{2,25})(?:\s*Time|\s*Labor|\s*Vehicle|\s*Date|\s*Instructions|$)',
            r'Name[:\s]*([A-Za-z\s]{2,25})(?:\s*Time|\s*Labor|\s*Vehicle|\s*Date|\s*Instructions|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up common form text that gets mixed in
                name = re.sub(r'\b(Time Started|Time Ended|Labor|Labour|Instructions|Vehicle|Date|Work)\b.*', '', name, flags=re.IGNORECASE).strip()
                
                if len(name) >= 3 and not re.search(r'\b(Time|Started|Ended|Work|Labor|Labour|Instructions|Vehicle|Date)\b', name, re.IGNORECASE):
                    # Apply corrections and fuzzy matching
                    return self._correct_and_match_driver_name(name)
        
        # Fallback to regular extraction
        driver_name, _ = self._extract_driver_name_fuzzy(text)
        return driver_name

    def _extract_vehicle_from_form(self, text: str) -> Optional[str]:
        """Extract vehicle ID specifically from form header."""
        # Look for "Vehicle ID / Plate:" pattern
        patterns = [
            r'Vehicle ID[/\s]*Plate[:\s]*([0-9]{5,6})',
            r'Vehicle[:\s]*([0-9]{5,6})',
            r'Plate[:\s]*([0-9]{5,6})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                vehicle = match.group(1).strip()
                # Check if it's in our known vehicles
                if vehicle in KNOWN_VEHICLES:
                    return vehicle
                # Apply corrections
                for mistake, correction in VEHICLE_ID_CORRECTIONS.items():
                    if mistake == vehicle:
                        return correction
                return vehicle
        
        # Fallback to regular extraction
        vehicle_id, _ = self._extract_vehicle_id_fuzzy(text)
        return vehicle_id

    def _extract_date_from_form(self, text: str) -> Optional[date]:
        """Extract date specifically from form header."""
        # Look for "Date:" pattern
        date_patterns = [
            r'Date[:\s]*(\d{2}[-/]\d{2}[-/]\d{2,4})',
            r'Date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                return self._parse_date(date_str)
        
        # Fallback to regular extraction
        log_date, _ = self._extract_date_with_confidence(text)
        return log_date

    def _extract_labor_name_from_form(self, text: str) -> Optional[str]:
        """Extract labor name specifically from form header."""
        # Look for "Labor Name:" pattern - more specific patterns to avoid form text
        patterns = [
            r'Labor Name[:\s]*([A-Za-z\s]{2,25})(?:\s*Time|\s*Driver|\s*Vehicle|\s*Date|\s*Instructions|$)',
            r'Labour Name[:\s]*([A-Za-z\s]{2,25})(?:\s*Time|\s*Driver|\s*Vehicle|\s*Date|\s*Instructions|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up common form text that gets mixed in
                name = re.sub(r'\b(Time Started|Time Ended|Driver|Vehicle|Date|Work|Instructions)\b.*', '', name, flags=re.IGNORECASE).strip()
                
                if len(name) >= 3 and not re.search(r'\b(Time|Started|Ended|Work|Driver|Vehicle|Date|Instructions)\b', name, re.IGNORECASE):
                    # Apply corrections and fuzzy matching
                    return self._correct_and_match_driver_name(name)
        
        return None

    def _extract_table_rows(self, text: str) -> List[Dict[str, str]]:
        """Extract rows from the movement log table."""
        rows = []
        
        # Split text into lines and look for table-like patterns
        lines = text.split('\n')
        
        for line in lines:
            # Skip header lines and empty lines
            if any(header in line.lower() for header in ['time arrived', 'time departed', 'location', 'instructions']):
                continue
            if not line.strip():
                continue
            
            # Enhanced time patterns to catch more variations
            time_patterns = [
                r'\b(\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm))\b',  # With AM/PM
                r'\b(\d{1,2}[:.]\d{2})\b',  # Without AM/PM
                r'\b(\d{1,2}\s*(?:AM|PM|am|pm))\b',  # Just hour with AM/PM
            ]
            
            all_times = []
            for pattern in time_patterns:
                times = re.findall(pattern, line, re.IGNORECASE)
                all_times.extend(times)
            
            # Remove duplicates while preserving order
            time_matches = []
            seen = set()
            for time_str in all_times:
                if time_str not in seen:
                    time_matches.append(time_str)
                    seen.add(time_str)
            
            if len(time_matches) >= 2:
                # Likely a table row with arrival and departure times
                arrival_time = time_matches[0]
                departure_time = time_matches[1]
                
                # Enhanced location extraction - look for text between or after times
                location_patterns = [
                    # Location between two times
                    r'\b\d{1,2}[:.]\d{2}(?:\s*(?:AM|PM|am|pm))?\s+([A-Za-z\s\-]{3,30})\s+\b\d{1,2}[:.]\d{2}',
                    # Location after two times
                    r'\b\d{1,2}[:.]\d{2}(?:\s*(?:AM|PM|am|pm))?\s+\b\d{1,2}[:.]\d{2}(?:\s*(?:AM|PM|am|pm))?\s+([A-Za-z\s\-]{3,30})',
                    # Location before times
                    r'([A-Za-z\s\-]{3,30})\s+\b\d{1,2}[:.]\d{2}(?:\s*(?:AM|PM|am|pm))?\s+\b\d{1,2}[:.]\d{2}',
                ]
                
                location = ""
                for loc_pattern in location_patterns:
                    location_match = re.search(loc_pattern, line, re.IGNORECASE)
                    if location_match:
                        location = location_match.group(1).strip()
                        break
                
                # Look for notes/details
                notes_matches = []
                # Look for reference numbers (6-10 digits)
                ref_match = re.search(r'([0-9]{6,10})', line)
                if ref_match:
                    notes_matches.append(ref_match.group(1))
                
                notes = ' | '.join(notes_matches) if notes_matches else ""
                
                rows.append({
                    'time_arrived': arrival_time,
                    'time_departed': departure_time,
                    'location': location,
                    'notes': notes
                })
            
            elif len(time_matches) == 1:
                # Single time - might be arrival only, but look harder for departure time
                time_val = time_matches[0]
                
                # Look for location near the time
                location_patterns = [
                    r'\b\d{1,2}[:.]\d{2}(?:\s*(?:AM|PM|am|pm))?\s+([A-Za-z\s\-]{3,30})',
                    r'([A-Za-z\s\-]{3,30})\s+\b\d{1,2}[:.]\d{2}(?:\s*(?:AM|PM|am|pm))?',
                ]
                
                location = ""
                for loc_pattern in location_patterns:
                    location_match = re.search(loc_pattern, line, re.IGNORECASE)
                    if location_match:
                        location = location_match.group(1).strip()
                        break
                
                if location:
                    rows.append({
                        'time_arrived': time_val,
                        'time_departed': None,
                        'location': location,
                        'notes': ""
                    })
        
        return rows

    def _clean_location(self, location: str) -> str:
        """Clean and correct location names."""
        if not location:
            return location
            
        location = location.strip()
        
        # Apply direct corrections
        for mistake, correction in LOCATION_CORRECTIONS.items():
            if mistake.lower() in location.lower():
                print(f"🔧 Corrected location '{mistake}' to '{correction}'")
                return correction
        
        # Apply fuzzy matching
        if KNOWN_LOCATIONS:
            match_result = process.extractOne(location, KNOWN_LOCATIONS, scorer=fuzz.partial_ratio)
            if match_result and match_result[1] >= 70:
                if match_result[0] != location:
                    print(f"🎯 Fuzzy matched location '{location}' to '{match_result[0]}' (score: {match_result[1]})")
                return match_result[0]
        
        return location

    def _correct_and_match_driver_name(self, name: str) -> str:
        """Apply corrections and fuzzy matching to driver names."""
        if not name:
            return name
            
        # Apply direct corrections
        for mistake, correction in DRIVER_NAME_CORRECTIONS.items():
            if mistake.lower() in name.lower():
                if correction:  # Don't return empty corrections
                    print(f"🔧 Corrected driver '{mistake}' to '{correction}'")
                    return correction
        
        # Apply fuzzy matching
        if KNOWN_DRIVERS:
            match_result = process.extractOne(name, KNOWN_DRIVERS, scorer=fuzz.ratio)
            if match_result and match_result[1] >= 70:
                if match_result[0] != name:
                    print(f"🎯 Fuzzy matched driver '{name}' to '{match_result[0]}' (score: {match_result[1]})")
                return match_result[0]
        
        return name.title()  # Capitalize properly as fallback

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string into a date object."""
        if not date_str:
            return None
        
        # Common date patterns
        patterns = [
            r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})',  # MM/DD/YY or MM/DD/YYYY
            r'(\d{2,4})[-/](\d{1,2})[-/](\d{1,2})',  # YYYY/MM/DD
        ]
        
        for pattern in patterns:
            match = re.match(pattern, date_str.strip())
            if match:
                try:
                    part1, part2, part3 = match.groups()
                    
                    # Try different interpretations
                    if len(part1) == 4:  # YYYY/MM/DD
                        year, month, day = int(part1), int(part2), int(part3)
                    else:  # MM/DD/YY or MM/DD/YYYY
                        month, day, year = int(part1), int(part2), int(part3)
                        if year < 100:  # Two-digit year
                            year += 2000
                    
                    return date(year, month, day)
                except (ValueError, TypeError):
                    continue
        
        return None
