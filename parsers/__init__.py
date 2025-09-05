"""
Parsers package for OCR text processing.

This package contains classes that take raw OCR text and convert it 
into structured data using our defined schemas.

As a Python beginner, think of parsers as "translators" that:
- Take messy OCR text as input
- Use patterns and rules to find specific information
- Clean and format the data
- Return structured data that matches our schemas
"""

from .driver_log_parser import DriverLogParser

# This allows easy importing like: from parsers import DriverLogParser
__all__ = ["DriverLogParser"]
