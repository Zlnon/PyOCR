"""
Driver Log Schema - Defines the structure for driver log data extraction.

This file uses Pydantic to create "data models" - think of them as templates
that define exactly what information we expect to extract from driver logs.

For Python beginners:
- Pydantic automatically validates data types (str, int, date, etc.)
- Optional fields can be missing from the OCR text
- Required fields must be found or validation fails
- Custom validators can clean/format data automatically
"""

from datetime import date, time
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class LocationVisit(BaseModel):
    """
    Represents a single location visit with arrival and departure times.
    
    This captures each individual stop/location visit as a separate record.
    """
    
    # Required fields
    driver_name: str = Field(..., description="Full name of the driver")
    log_date: date = Field(..., description="Date of the visit (YYYY-MM-DD)")
    location: str = Field(..., description="Location name")
    
    # Optional timing fields
    arrival_time: Optional[time] = Field(None, description="Time arrived at location")
    departure_time: Optional[time] = Field(None, description="Time departed from location")
    
    # Optional additional fields
    vehicle_id: Optional[str] = Field(None, description="Vehicle identification number")
    labor_name: Optional[str] = Field(None, description="Labor/worker name (from form)")
    location_category: Optional[str] = Field(None, description="Location category (Carrefour, Spar, Lulu, etc.)")
    notes: Optional[str] = Field(None, description="Notes/Details from the form (reference numbers, etc.)")
    
    # Source information
    source_image: str = Field(..., description="Original image filename")
    visit_sequence: Optional[int] = Field(None, description="Order of visit in the day (1st, 2nd, etc.)")
    
    # Custom validators
    @validator('driver_name')
    def clean_driver_name(cls, v):
        """Clean up driver name - remove extra spaces, capitalize properly"""
        if v:
            return ' '.join(word.capitalize() for word in v.split())
        return v
    
    @validator('vehicle_id')
    def clean_vehicle_id(cls, v):
        """Clean up vehicle ID - remove spaces, convert to uppercase"""
        if v:
            return v.replace(' ', '').upper()
        return v


class DriverLogEntry(BaseModel):
    """
    Represents a single driver log entry.
    
    This is like a "row" in a spreadsheet - one record of driver activity.
    Each field represents a "column" of data we want to extract.
    """
    
    # Required fields - these MUST be found in the OCR text
    driver_name: str = Field(..., description="Full name of the driver")
    log_date: date = Field(..., description="Date of the log entry (YYYY-MM-DD)")
    
    # Optional fields - these might not always be present
    vehicle_id: Optional[str] = Field(None, description="Vehicle identification number")
    start_time: Optional[time] = Field(None, description="Shift start time")
    end_time: Optional[time] = Field(None, description="Shift end time")
    start_location: Optional[str] = Field(None, description="Starting location/address")
    end_location: Optional[str] = Field(None, description="Ending location/address")
    labor_name: Optional[str] = Field(None, description="Labor/worker name (from form)")
    notes: Optional[str] = Field(None, description="Additional notes or comments")
    
    # Custom validators to clean/format data
    @validator('driver_name')
    def clean_driver_name(cls, v):
        """Clean up driver name - remove extra spaces, capitalize properly"""
        if v:
            return ' '.join(word.capitalize() for word in v.split())
        return v
    
    @validator('vehicle_id')
    def clean_vehicle_id(cls, v):
        """Clean up vehicle ID - remove spaces, convert to uppercase"""
        if v:
            return v.replace(' ', '').upper()
        return v
    
    @validator('labor_name')
    def clean_labor_name(cls, v):
        """Clean up labor name - remove extra spaces, capitalize properly"""
        if v:
            return ' '.join(word.capitalize() for word in v.split())
        return v


class DriverLogData(BaseModel):
    """
    Represents all driver log data extracted from a single document/image.
    
    This is like a "worksheet" that can contain multiple log entries.
    """
    
    # Metadata about the document
    source_file: str = Field(..., description="Original image filename")
    extraction_date: date = Field(..., description="When the OCR was performed")
    
    # The actual log entries found in the document
    entries: List[DriverLogEntry] = Field(default_factory=list, description="List of driver log entries")
    
    # OCR confidence and processing info
    ocr_confidence: Optional[float] = Field(None, description="Overall OCR confidence score (0-1)")
    processing_notes: Optional[str] = Field(None, description="Notes about the extraction process")
    
    @validator('ocr_confidence')
    def validate_confidence(cls, v):
        """Ensure confidence score is between 0 and 1"""
        if v is not None and (v < 0 or v > 1):
            raise ValueError('OCR confidence must be between 0 and 1')
        return v
    
    def add_entry(self, entry: DriverLogEntry):
        """Helper method to add a new log entry"""
        self.entries.append(entry)
    
    def get_unique_drivers(self) -> List[str]:
        """Get list of unique driver names from all entries"""
        return list(set(entry.driver_name for entry in self.entries))
    
    def get_unique_labor_names(self) -> List[str]:
        """Get list of unique labor names from all entries"""
        return list(set(entry.labor_name for entry in self.entries if entry.labor_name))
