"""
Schemas package for OCR data validation.

This package contains Pydantic models that define the structure 
and validation rules for extracted data from OCR documents.

As a Python beginner, think of schemas as "templates" that define:
- What fields (data pieces) we expect to extract
- What type each field should be (text, number, date, etc.)
- Which fields are required vs optional
- Validation rules (like "date must be in YYYY-MM-DD format")
"""

from .driver_log_schema import DriverLogEntry, DriverLogData, LocationVisit

# This makes it easy to import from other files like:
# from schemas import DriverLogEntry
__all__ = ["DriverLogEntry", "DriverLogData", "LocationVisit"]
