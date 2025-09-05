"""
Example Usage Script - Simple demonstration of the OCR pipeline

This script shows you how to use individual components of the pipeline
for testing and learning purposes.

For Python beginners:
- Run this script to test individual parts before using the full pipeline
- Modify the sample text to see how the parser works
- Use this to understand how the different components interact
"""

from datetime import date
from parsers import DriverLogParser
from schemas import DriverLogEntry, DriverLogData


def test_parser_with_sample_text():
    """
    Test the parser with sample OCR text.
    
    This shows you how the parser extracts information from messy OCR text.
    """
    
    print("🧪 Testing Parser with Sample Text")
    print("=" * 40)
    
    # Sample OCR text (simulating what Google Vision API might return)
    sample_ocr_text = """
    DRIVER LOG SHEET
    
    Driver Name: John Smith
    Date: 03/15/2024
    Vehicle ID: TRK001
    
    Start Time: 8:00 AM
    End Time: 5:30 PM
    
    Start Location: 123 Main St, Chicago IL
    End Location: 456 Oak Ave, Milwaukee WI
    
    Miles Driven: 245.5
    Fuel Used: 18.2 gallons
    
    Notes: Delivered to customer, no issues
    """
    
    # Create parser and process the text
    parser = DriverLogParser()
    result = parser.parse_document(
        ocr_text=sample_ocr_text,
        source_file="sample_log.jpg",
        ocr_confidence=0.95
    )
    
    # Display results
    print(f"Source File: {result.source_file}")
    print(f"Extraction Date: {result.extraction_date}")
    print(f"OCR Confidence: {result.ocr_confidence}")
    print(f"Entries Found: {len(result.entries)}")
    print(f"Processing Notes: {result.processing_notes}")
    
    if result.entries:
        print(f"\n📋 Extracted Entry Details:")
        entry = result.entries[0]
        print(f"  Driver: {entry.driver_name}")
        print(f"  Date: {entry.log_date}")
        print(f"  Vehicle: {entry.vehicle_id}")
        print(f"  Start Time: {entry.start_time}")
        print(f"  End Time: {entry.end_time}")
        print(f"  Start Location: {entry.start_location}")
        print(f"  End Location: {entry.end_location}")
        print(f"  Miles: {entry.miles_driven}")
        print(f"  Fuel: {entry.fuel_used} gallons")
        print(f"  Notes: {entry.notes}")
    
    print(f"\n✅ Parser test completed!")
    return result


def test_schema_validation():
    """
    Test the Pydantic schema validation.
    
    This shows you how data validation works and what happens with invalid data.
    """
    
    print(f"\n🔍 Testing Schema Validation")
    print("=" * 40)
    
    # Test valid data
    print("Testing valid data...")
    try:
        valid_entry = DriverLogEntry(
            driver_name="jane doe",  # Will be auto-capitalized
            log_date=date(2024, 3, 15),
            vehicle_id="abc 123",    # Will be cleaned up
            miles_driven=150.5,
            fuel_used=12.3
        )
        print(f"✅ Valid entry created:")
        print(f"  Cleaned driver name: {valid_entry.driver_name}")
        print(f"  Cleaned vehicle ID: {valid_entry.vehicle_id}")
    except Exception as e:
        print(f"❌ Validation error: {e}")
    
    # Test invalid data
    print(f"\nTesting invalid data...")
    try:
        invalid_entry = DriverLogEntry(
            driver_name="John Smith",
            log_date=date(2024, 3, 15),
            miles_driven=-50.0  # Negative miles should fail validation
        )
        print(f"❌ This should not have passed validation!")
    except Exception as e:
        print(f"✅ Validation correctly caught error: {e}")
    
    print(f"\n✅ Schema validation test completed!")


def demonstrate_json_export():
    """
    Show how to create and export data to JSON format.
    
    This demonstrates the new JSON-first workflow.
    """
    
    print(f"\n📊 Demonstrating JSON Export")
    print("=" * 40)
    
    # Create sample data
    log_data = DriverLogData(
        source_file="demo_log.jpg",
        extraction_date=date.today(),
        ocr_confidence=0.92
    )
    
    # Add sample entries
    entries_data = [
        {
            "driver_name": "John Smith",
            "log_date": date(2024, 3, 15),
            "vehicle_id": "TRK001",
            "miles_driven": 245.5,
            "fuel_used": 18.2
        },
        {
            "driver_name": "Jane Doe", 
            "log_date": date(2024, 3, 15),
            "vehicle_id": "TRK002",
            "miles_driven": 189.3,
            "fuel_used": 14.7
        }
    ]
    
    for entry_data in entries_data:
        entry = DriverLogEntry(**entry_data)
        log_data.add_entry(entry)
    
    # Display summary
    print(f"Created log data with {len(log_data.entries)} entries")
    print(f"Total miles: {log_data.get_total_miles()}")
    print(f"Total fuel: {log_data.get_total_fuel()} gallons")
    
    # Show how to export to JSON format (like the main pipeline does)
    try:
        import json
        
        # Create JSON structure like the main pipeline
        from datetime import datetime
        json_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_images_processed": 1,
                "total_entries_extracted": len(log_data.entries),
                "pipeline_version": "1.0.0"
            },
            "results": [{
                "source_file": log_data.source_file,
                "extraction_date": log_data.extraction_date.isoformat(),
                "ocr_confidence": log_data.ocr_confidence,
                "processing_notes": log_data.processing_notes,
                "entries": []
            }]
        }
        
        # Add entries with proper date/time formatting
        for entry in log_data.entries:
            entry_dict = entry.dict()
            # Convert dates/times to strings for JSON
            if entry_dict.get('log_date'):
                entry_dict['log_date'] = entry_dict['log_date'].isoformat()
            json_data["results"][0]["entries"].append(entry_dict)
        
        # Show JSON structure
        print(f"\n📄 JSON structure created:")
        print(f"   Metadata: {len(json_data['metadata'])} fields")
        print(f"   Results: {len(json_data['results'])} documents")
        print(f"   Entries: {len(json_data['results'][0]['entries'])} log entries")
        
        # Show sample JSON (first few lines)
        json_sample = json.dumps(json_data, indent=2)[:300] + "..."
        print(f"\n📋 Sample JSON output:\n{json_sample}")
        
    except ImportError:
        print("📦 JSON module should be built-in to Python")
    
    print(f"\n💡 JSON Benefits:")
    print("   ✓ Preserves data types (dates, numbers, booleans)")
    print("   ✓ Easy to convert to Excel, CSV, or database")
    print("   ✓ API-friendly format")
    print("   ✓ Version control friendly")
    print("   ✓ Can be processed without re-running OCR")
    
    print(f"\n✅ JSON export demonstration completed!")


def main():
    """
    Run all the example demonstrations.
    """
    
    print("🎯 OCR Pipeline Component Examples")
    print("=" * 50)
    print("This script demonstrates how the individual components work.")
    print("Run the full pipeline with: python main.py")
    print()
    
    try:
        # Test each component
        test_parser_with_sample_text()
        test_schema_validation()
        demonstrate_json_export()
        
        print(f"\n🎉 All examples completed successfully!")
        print(f"\nNext steps:")
        print(f"1. Add your images to the 'images/' folder")
        print(f"2. Configure your Google Cloud credentials in .env")
        print(f"3. Run the full pipeline: python main.py")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")


if __name__ == "__main__":
    main()
