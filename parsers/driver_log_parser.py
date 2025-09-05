"""
Driver Log Parser - Extracts structured data from OCR text.

This file contains the logic to take raw OCR text and convert it into
structured DriverLogEntry and DriverLogData objects.

For Python beginners:
- Regular expressions (regex) are patterns that help find specific text
- The parser looks for common patterns like dates, times, names, numbers
- It tries multiple patterns because OCR text can be messy
- The extracted data is validated using our Pydantic schemas
"""

import re
from datetime import date, datetime, time
from typing import List, Optional, Tuple, Dict
from fuzzywuzzy import fuzz, process
from schemas.driver_log_schema import DriverLogEntry, DriverLogData, LocationVisit

# Import configuration
try:
    from config import (
        KNOWN_DRIVERS, DRIVER_NAME_CORRECTIONS,
        KNOWN_VEHICLES, VEHICLE_ID_CORRECTIONS, 
        KNOWN_LOCATIONS, LOCATION_CORRECTIONS,
        get_location_category
    )
except ImportError:
    # Fallback if config not available
    KNOWN_DRIVERS = []
    DRIVER_NAME_CORRECTIONS = {}
    KNOWN_VEHICLES = []
    VEHICLE_ID_CORRECTIONS = {}
    KNOWN_LOCATIONS = []
    LOCATION_CORRECTIONS = {}
    def get_location_category(location): return "Other"


class DriverLogParser:
    """
    Parses OCR text to extract driver log information.
    
    This class contains methods to find specific pieces of information
    in the messy OCR text using patterns and rules.
    """
    
    def __init__(self):
        """Initialize the parser with common regex patterns."""
        
        # Date patterns - matches various date formats
        self.date_patterns = [
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',  # MM/DD/YYYY or MM-DD-YYYY
            r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
            r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\b',  # DD Mon YYYY
        ]
        
        # Time patterns - matches various time formats
        self.time_patterns = [
            r'\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?\b',  # 12:30 PM or 12:30
            r'\b(\d{1,2})\.(\d{2})\s*(AM|PM|am|pm)?\b',  # 12.30 PM (sometimes OCR reads : as .)
        ]
        
        # Vehicle ID patterns
        self.vehicle_patterns = [
            r'\b[Vv]ehicle\s*[ID#:]*\s*([A-Z0-9]{3,10})\b',  # Vehicle ID: ABC123
            r'\b[Tt]ruck\s*[#:]*\s*([A-Z0-9]{3,10})\b',      # Truck #: ABC123
            r'\b[Uu]nit\s*[#:]*\s*([A-Z0-9]{3,10})\b',       # Unit #: ABC123
        ]
        
        # Miles/distance patterns
        self.miles_patterns = [
            r'\b(\d+\.?\d*)\s*miles?\b',                      # 123.5 miles
            r'\b[Mm]iles?[:\s]*(\d+\.?\d*)\b',               # Miles: 123.5
            r'\b[Dd]istance[:\s]*(\d+\.?\d*)\b',             # Distance: 123.5
        ]
        
        # Fuel patterns
        self.fuel_patterns = [
            r'\b(\d+\.?\d*)\s*gal(lon)?s?\b',                # 15.5 gallons
            r'\b[Ff]uel[:\s]*(\d+\.?\d*)\b',                 # Fuel: 15.5
            r'\b[Gg]as[:\s]*(\d+\.?\d*)\b',                  # Gas: 15.5
        ]
    
    def parse_document(self, ocr_text: str, source_file: str, ocr_confidence: Optional[float] = None) -> DriverLogData:
        """
        Main method to parse an entire document.
        
        Args:
            ocr_text: Raw text from OCR
            source_file: Name of the original image file
            ocr_confidence: OCR confidence score (0-1)
            
        Returns:
            DriverLogData object with all extracted entries
        """
        
        # Create the main data container
        log_data = DriverLogData(
            source_file=source_file,
            extraction_date=date.today(),
            ocr_confidence=ocr_confidence
        )
        
        # Split text into potential log entries (look for common separators)
        entry_blocks = self._split_into_entries(ocr_text)
        
        processing_notes = []
        
        for i, block in enumerate(entry_blocks):
            try:
                entry = self._parse_single_entry(block)
                if entry:
                    log_data.add_entry(entry)
                    processing_notes.append(f"Successfully parsed entry {i+1}")
                else:
                    processing_notes.append(f"Could not parse entry {i+1} - insufficient data")
            except Exception as e:
                processing_notes.append(f"Error parsing entry {i+1}: {str(e)}")
        
        log_data.processing_notes = "; ".join(processing_notes)
        return log_data
    
    def _split_into_entries(self, text: str) -> List[str]:
        """
        Split OCR text into individual log entry blocks.
        
        This looks for common separators like lines, dates, or driver names
        to identify where one log entry ends and another begins.
        """
        
        # Clean up the text first
        text = re.sub(r'\n+', '\n', text)  # Remove multiple newlines
        text = re.sub(r'\s+', ' ', text)   # Normalize whitespace
        
        # Try to split by dates (assuming each entry has a date)
        date_splits = []
        for pattern in self.date_patterns:
            matches = list(re.finditer(pattern, text))
            if matches:
                # Split the text at each date match
                last_end = 0
                for match in matches:
                    if last_end < match.start():
                        # Add the text before this date as part of previous entry
                        if date_splits:
                            date_splits[-1] += text[last_end:match.start()]
                    # Start new entry with this date
                    date_splits.append(text[match.start():])
                    last_end = match.end()
                break
        
        # If no date-based splitting worked, try splitting by lines
        if not date_splits:
            lines = text.split('\n')
            # Group lines that seem to belong together
            current_entry = []
            entries = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # If line looks like a new entry header, start new entry
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
        
        return date_splits if date_splits else [text]
    
    def _parse_single_entry(self, text: str) -> Optional[DriverLogEntry]:
        """
        Parse a single log entry from a text block.
        
        This method looks for all the different pieces of information
        we want to extract and tries to build a complete DriverLogEntry.
        """
        
        # Extract each field
        driver_name = self._extract_driver_name(text)
        log_date = self._extract_date(text)
        
        # We need at least a driver name or date to consider this a valid entry
        if not driver_name and not log_date:
            return None
        
        # Extract optional fields
        vehicle_id = self._extract_vehicle_id(text)
        start_time, end_time = self._extract_times(text)
        start_location, end_location = self._extract_locations(text)
        miles_driven = self._extract_miles(text)
        fuel_used = self._extract_fuel(text)
        notes = self._extract_notes(text)
        
        # Create and return the entry
        try:
            return DriverLogEntry(
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
        except Exception as e:
            # If validation fails, return None
            print(f"Validation error creating DriverLogEntry: {e}")
            return None
    
    def _extract_driver_name(self, text: str) -> Optional[str]:
        """Extract driver name from text with fuzzy matching."""
        
        # First try exact corrections
        for mistake, correction in DRIVER_NAME_CORRECTIONS.items():
            if mistake.lower() in text.lower():
                print(f"🔧 Corrected '{mistake}' to '{correction}'")
                return correction
        
        # Common patterns for driver names
        name_patterns = [
            r'[Dd]river[:\s]*([A-Za-z\s]{2,30})',           # Driver: John Smith
            r'[Nn]ame[:\s]*([A-Za-z\s]{2,30})',             # Name: John Smith
            r'[Oo]perator[:\s]*([A-Za-z\s]{2,30})',         # Operator: John Smith
            r'[Ll]ab[ou]?r\s+[Nn]ame[:\s]*([A-Za-z\s]{2,30})', # Labour Name: John Smith
        ]
        
        potential_names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                clean_name = match.strip()
                if len(clean_name.split()) >= 1:  # At least one word
                    potential_names.append(clean_name)
        
        # Also look for capitalized words that might be names
        words = text.split()
        for i in range(len(words) - 1):
            word1, word2 = words[i], words[i+1]
            if (word1[0].isupper() and word2[0].isupper() and 
                len(word1) > 2 and len(word2) > 2 and
                word1.isalpha() and word2.isalpha()):
                potential_names.append(f"{word1} {word2}")
        
        if not potential_names:
            return None
        
        # Use fuzzy matching if we have known drivers
        if KNOWN_DRIVERS:
            best_match = None
            best_score = 0
            
            for potential_name in potential_names:
                # Try fuzzy matching against known drivers
                match_result = process.extractOne(potential_name, KNOWN_DRIVERS, scorer=fuzz.ratio)
                if match_result and match_result[1] >= 70:  # 70% similarity threshold
                    if match_result[1] > best_score:
                        best_match = match_result[0]
                        best_score = match_result[1]
                        print(f"🎯 Fuzzy matched '{potential_name}' to '{best_match}' (score: {best_score})")
            
            if best_match:
                return best_match
        
        # If no fuzzy match, return the most reasonable looking name
        for name in potential_names:
            clean_name = re.sub(r'[^A-Za-z\s]', '', name).strip()
            if re.match(r'^[A-Za-z\s]+$', clean_name) and 2 <= len(clean_name) <= 30:
                return clean_name.title()
        
        return None
    
    def _extract_date(self, text: str) -> Optional[date]:
        """Extract date from text."""
        
        for pattern in self.date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if len(match.groups()) == 3:
                        if pattern.startswith(r'\b(\d{4})'):  # YYYY-MM-DD format
                            year, month, day = match.groups()
                        elif pattern.endswith(r'(\d{4})\b'):  # DD Mon YYYY format
                            day, month_name, year = match.groups()
                            month_map = {
                                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                            }
                            month = str(month_map.get(month_name, 1))
                        else:  # MM/DD/YYYY format
                            month, day, year = match.groups()
                        
                        return date(int(year), int(month), int(day))
                except (ValueError, KeyError):
                    continue
        
        return None
    
    def _extract_vehicle_id(self, text: str) -> Optional[str]:
        """Extract vehicle ID from text with corrections and fuzzy matching."""
        
        # First try exact corrections
        for mistake, correction in VEHICLE_ID_CORRECTIONS.items():
            if mistake in text:
                print(f"🔧 Corrected vehicle '{mistake}' to '{correction}'")
                return correction
        
        potential_ids = []
        for pattern in self.vehicle_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            potential_ids.extend(matches)
        
        # Also look for number sequences that could be vehicle IDs
        number_patterns = [
            r'\b(\d{5,6})\b',  # 5-6 digit numbers
            r'\b(\d{3}\d{3})\b',  # 6 digits
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, text)
            potential_ids.extend(matches)
        
        if not potential_ids:
            return None
        
        # Use fuzzy matching against known vehicles if available
        if KNOWN_VEHICLES:
            best_match = None
            best_score = 0
            
            for potential_id in potential_ids:
                clean_id = str(potential_id).strip()
                # Direct match first
                if clean_id in KNOWN_VEHICLES:
                    print(f"🎯 Exact vehicle match: {clean_id}")
                    return clean_id
                    
                # Fuzzy matching
                match_result = process.extractOne(clean_id, KNOWN_VEHICLES, scorer=fuzz.ratio)
                if match_result and match_result[1] >= 85:  # High threshold for vehicle IDs
                    if match_result[1] > best_score:
                        best_match = match_result[0]
                        best_score = match_result[1]
                        print(f"🎯 Fuzzy matched vehicle '{clean_id}' to '{best_match}' (score: {best_score})")
            
            if best_match:
                return best_match
        
        # Return the most reasonable looking ID
        for vehicle_id in potential_ids:
            clean_id = str(vehicle_id).strip()
            if re.match(r'^\d{5,6}$', clean_id):  # 5-6 digits
                return clean_id
        
        return None
    
    def _extract_times(self, text: str) -> Tuple[Optional[datetime.time], Optional[datetime.time]]:
        """Extract start and end times from text."""
        
        times_found = []
        
        for pattern in self.time_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    am_pm = match.group(3) if len(match.groups()) >= 3 else None
                    
                    # Convert to 24-hour format if needed
                    if am_pm and am_pm.upper() == 'PM' and hour != 12:
                        hour += 12
                    elif am_pm and am_pm.upper() == 'AM' and hour == 12:
                        hour = 0
                    
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        times_found.append(time(hour, minute))
                except ValueError:
                    continue
        
        # Return first two times found as start and end
        start_time = times_found[0] if len(times_found) > 0 else None
        end_time = times_found[1] if len(times_found) > 1 else None
        
        return start_time, end_time
    
    def _extract_locations(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract start and end locations from text with corrections and fuzzy matching."""
        
        # First try exact corrections
        for mistake, correction in LOCATION_CORRECTIONS.items():
            if mistake.lower() in text.lower():
                print(f"🔧 Corrected location '{mistake}' to '{correction}'")
                # For now, return as start location - could be enhanced to detect start/end
                return correction, None
        
        location_patterns = [
            r'[Ss]tart[:\s]*([A-Za-z0-9\s,.-]{5,50})',      # Start: Location
            r'[Ff]rom[:\s]*([A-Za-z0-9\s,.-]{5,50})',       # From: Location
            r'[Ee]nd[:\s]*([A-Za-z0-9\s,.-]{5,50})',        # End: Location
            r'[Tt]o[:\s]*([A-Za-z0-9\s,.-]{5,50})',         # To: Location
            r'[Ll]ocation[:\s]*([A-Za-z0-9\s,.-]{5,50})',   # Location: 
        ]
        
        potential_locations = []
        start_location = None
        end_location = None
        
        for pattern in location_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                location = match.group(1).strip()
                # Clean up the location
                location = re.sub(r'[,.-]+$', '', location).strip()
                
                if 'start' in pattern.lower() or 'from' in pattern.lower():
                    potential_locations.append(('start', location))
                elif 'end' in pattern.lower() or 'to' in pattern.lower():
                    potential_locations.append(('end', location))
                else:
                    potential_locations.append(('unknown', location))
        
        # Also look for known locations directly in text
        if KNOWN_LOCATIONS:
            for known_location in KNOWN_LOCATIONS:
                if known_location.lower() in text.lower():
                    potential_locations.append(('unknown', known_location))
                    print(f"🎯 Found known location: {known_location}")
        
        # Use fuzzy matching to improve location recognition
        if KNOWN_LOCATIONS and potential_locations:
            for location_type, location in potential_locations:
                # Try fuzzy matching
                match_result = process.extractOne(location, KNOWN_LOCATIONS, scorer=fuzz.partial_ratio)
                if match_result and match_result[1] >= 70:  # 70% similarity threshold
                    matched_location = match_result[0]
                    category = get_location_category(matched_location)
                    print(f"🎯 Fuzzy matched '{location}' to '{matched_location}' ({category}) (score: {match_result[1]})")
                    
                    if location_type == 'start' or (start_location is None):
                        start_location = matched_location
                    elif location_type == 'end' or (end_location is None):
                        end_location = matched_location
                    else:
                        if start_location is None:
                            start_location = matched_location
                        else:
                            end_location = matched_location
        
        # If no fuzzy matches, use original locations
        if not start_location and not end_location and potential_locations:
            for location_type, location in potential_locations:
                if location_type == 'start' or (start_location is None):
                    start_location = location
                elif location_type == 'end' or (end_location is None):
                    end_location = location
        
        return start_location, end_location
    
    def _extract_miles(self, text: str) -> Optional[float]:
        """Extract miles driven from text."""
        
        for pattern in self.miles_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_fuel(self, text: str) -> Optional[float]:
        """Extract fuel consumption from text."""
        
        for pattern in self.fuel_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_notes(self, text: str) -> Optional[str]:
        """Extract notes/comments from text."""
        
        notes_patterns = [
            r'[Nn]otes?[:\s]*([A-Za-z0-9\s,.-]{10,200})',   # Notes: Some comment
            r'[Cc]omments?[:\s]*([A-Za-z0-9\s,.-]{10,200})', # Comments: Some comment
            r'[Rr]emarks?[:\s]*([A-Za-z0-9\s,.-]{10,200})', # Remarks: Some comment
        ]
        
        for pattern in notes_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _parse_time(self, time_str: str) -> Optional[time]:
        """Parse a time string into a time object."""
        if not time_str:
            return None
            
        time_str = time_str.strip().upper()
        
        # Common time patterns
        patterns = [
            r'(\d{1,2})[:.:](\d{2})\s*(AM|PM)?',
            r'(\d{1,2})\s*(AM|PM)',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, time_str)
            if match:
                try:
                    hour = int(match.group(1))
                    minute = int(match.group(2)) if len(match.groups()) >= 2 and match.group(2) else 0
                    am_pm = match.group(3) if len(match.groups()) >= 3 else None
                    
                    # Convert to 24-hour format
                    if am_pm == 'PM' and hour != 12:
                        hour += 12
                    elif am_pm == 'AM' and hour == 12:
                        hour = 0
                    
                    return time(hour, minute)
                except (ValueError, IndexError):
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
            driver_name = self._extract_driver_name(text)
            log_date = self._extract_date(text)
            vehicle_id = self._extract_vehicle_id(text)
            labor_name = self._extract_labor_name_from_form(text)  # Try to get labor name
            
            if not driver_name:
                driver_name = "Unknown Driver"
            if not log_date:
                log_date = date.today()
            
            # Enhanced pattern to find location-time combinations
            # Look for patterns like: "Location 7:45 AM 9:40 AM" or "7:45 Location 9:40"
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
            # Extract header information
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
    
    def _extract_driver_name_from_form(self, text: str) -> Optional[str]:
        """Extract driver name specifically from form header."""
        # Look for "Driver Name:" pattern
        patterns = [
            r'Driver Name[:\s]*([A-Za-z\s]{2,30})',
            r'Driver[:\s]*([A-Za-z\s]{2,30})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Apply corrections and fuzzy matching
                return self._correct_and_match_driver_name(name)
        
        # Fallback to regular extraction
        return self._extract_driver_name(text)
    
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
        return self._extract_vehicle_id(text)
    
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
        return self._extract_date(text)
    
    def _extract_labor_name_from_form(self, text: str) -> Optional[str]:
        """Extract labor name specifically from form header."""
        # Look for "Labor Name:" pattern
        patterns = [
            r'Labor Name[:\s]*([A-Za-z\s]{2,30})',
            r'Labour Name[:\s]*([A-Za-z\s]{2,30})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
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
            
            # Look for time patterns in the line (indicating a data row)
            time_matches = re.findall(r'\b(\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?)\b', line)
            
            if len(time_matches) >= 2:
                # Likely a table row with arrival and departure times
                arrival_time = time_matches[0]
                departure_time = time_matches[1]
                
                # Extract location (text between times and after second time)
                location_match = re.search(r'\b\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?\s+\b\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?\s+([A-Za-z\s\-]{3,30})', line, re.IGNORECASE)
                location = location_match.group(1).strip() if location_match else ""
                
                # Look for notes/details (numbers, reference codes, or additional text)
                notes_matches = []
                # Look for reference numbers (6-10 digits)
                ref_match = re.search(r'([0-9]{6,10})', line)
                if ref_match:
                    notes_matches.append(ref_match.group(1))
                
                # Look for additional text after the location
                remaining_text = re.sub(r'\b\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?\b', '', line)  # Remove times
                remaining_text = re.sub(r'[A-Za-z\s\-]{3,30}', '', remaining_text, count=1)  # Remove first location
                remaining_text = remaining_text.strip()
                if remaining_text and len(remaining_text) > 2:
                    notes_matches.append(remaining_text)
                
                notes = ' | '.join(notes_matches) if notes_matches else ""
                
                rows.append({
                    'time_arrived': arrival_time,
                    'time_departed': departure_time,
                    'location': location,
                    'notes': notes
                })
            
            elif len(time_matches) == 1:
                # Single time - might be arrival only
                time_val = time_matches[0]
                location_match = re.search(r'\b\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?\s+([A-Za-z\s\-]{3,30})', line, re.IGNORECASE)
                location = location_match.group(1).strip() if location_match else ""
                
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
