"""
Multi-Document OCR Data Extraction Pipeline

This is the main script that orchestrates the entire OCR process:
1. Loads images from the images/ folder
2. Uses Google Cloud Vision API to extract text
3. Parses the text using our custom parser
4. Validates data using Pydantic schemas
5. Exports results to Excel files

For Python beginners:
- This script ties together all the other modules we created
- It uses environment variables for configuration (from .env file)
- It processes multiple images in batches
- It handles errors gracefully and provides detailed logging
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, date, time
from typing import List, Dict, Any
import pandas as pd
from dotenv import load_dotenv

# Google Cloud Vision imports
from google.cloud import vision
from google.cloud.vision_v1 import types

# Our custom modules
from parsers import EnhancedDriverLogParser
from schemas import DriverLogData, LocationVisit


class OCRPipeline:
    """
    Main OCR Pipeline class that handles the entire process.
    
    This class coordinates all the different steps:
    - Image loading and validation
    - OCR text extraction
    - Data parsing and validation
    - Excel export
    """
    
    def __init__(self):
        """Initialize the OCR pipeline with configuration from environment variables."""
        
        # Load environment variables from .env file
        load_dotenv()
        
        # Get configuration from environment
        self.images_folder = os.getenv('IMAGES_FOLDER', 'images')
        self.output_folder = os.getenv('OUTPUT_FOLDER', 'output')
        self.max_batch_size = int(os.getenv('MAX_IMAGES_PER_BATCH', '10'))
        self.json_prefix = os.getenv('JSON_FILENAME_PREFIX', 'ocr_results')
        
        # Validate that Google Cloud credentials are set
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS environment variable not set. "
                "Please set it to the path of your Google Cloud service account JSON file."
            )
        
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Google Cloud credentials file not found: {credentials_path}")
        
        # Initialize Google Cloud Vision client
        try:
            self.vision_client = vision.ImageAnnotatorClient()
            print("✓ Google Cloud Vision client initialized successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google Cloud Vision client: {e}")
        
        # Initialize our parser
        self.parser = EnhancedDriverLogParser()
        
        # Create output directory if it doesn't exist
        Path(self.output_folder).mkdir(exist_ok=True)
        
        print(f"✓ OCR Pipeline initialized")
        print(f"  - Images folder: {self.images_folder}")
        print(f"  - Output folder: {self.output_folder}")
        print(f"  - Max batch size: {self.max_batch_size}")
    
    def get_image_files(self) -> List[Path]:
        """
        Get all supported image files from the images folder.
        
        Returns:
            List of Path objects for valid image files
        """
        
        if not os.path.exists(self.images_folder):
            raise FileNotFoundError(f"Images folder not found: {self.images_folder}")
        
        # Supported image formats
        supported_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        
        image_files = []
        images_path = Path(self.images_folder)
        
        for file_path in images_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                image_files.append(file_path)
        
        return sorted(image_files)  # Sort for consistent processing order
    
    def extract_text_from_image(self, image_path: Path) -> Dict[str, Any]:
        """
        Extract text from a single image using Google Cloud Vision API.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        
        try:
            # Read the image file
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            # Create Vision API image object
            image = vision.Image(content=content)
            
            # Perform text detection
            response = self.vision_client.text_detection(image=image)
            
            # Check for errors
            if response.error.message:
                raise RuntimeError(f"Vision API error: {response.error.message}")
            
            # Extract text and confidence
            texts = response.text_annotations
            if not texts:
                return {
                    'text': '',
                    'confidence': 0.0,
                    'error': 'No text detected in image'
                }
            
            # The first text annotation contains all detected text
            full_text = texts[0].description
            
            # Calculate average confidence from all text annotations
            confidences = []
            for text in texts[1:]:  # Skip the first one (full text)
                if hasattr(text, 'confidence'):
                    confidences.append(text.confidence)
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                'text': full_text,
                'confidence': avg_confidence,
                'error': None
            }
            
        except Exception as e:
            return {
                'text': '',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def process_single_image(self, image_path: Path) -> DriverLogData:
        """
        Process a single image through the complete OCR pipeline.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            DriverLogData object with extracted and parsed data
        """
        
        print(f"Processing: {image_path.name}")
        
        # Step 1: Extract text using OCR
        ocr_result = self.extract_text_from_image(image_path)
        
        if ocr_result['error']:
            print(f"  ⚠️  OCR Error: {ocr_result['error']}")
            # Return empty log data with error info
            return DriverLogData(
                source_file=image_path.name,
                extraction_date=datetime.now().date(),
                processing_notes=f"OCR Error: {ocr_result['error']}"
            )
        
        print(f"  ✓ OCR completed (confidence: {ocr_result['confidence']:.2f})")
        
        # Step 2: Parse the extracted text
        try:
            log_data = self.parser.parse_document(
                ocr_text=ocr_result['text'],
                source_file=image_path.name,
                ocr_confidence=ocr_result['confidence']
            )
            
            print(f"  ✓ Parsing completed ({len(log_data.entries)} entries found)")
            return log_data
            
        except Exception as e:
            print(f"  ⚠️  Parsing Error: {e}")
            return DriverLogData(
                source_file=image_path.name,
                extraction_date=datetime.now().date(),
                processing_notes=f"Parsing Error: {str(e)}"
            )
    
    def process_batch(self, image_files: List[Path]) -> List[DriverLogData]:
        """
        Process a batch of images.
        
        Args:
            image_files: List of image file paths
            
        Returns:
            List of DriverLogData objects
        """
        
        results = []
        
        for i, image_path in enumerate(image_files, 1):
            print(f"\n[{i}/{len(image_files)}] ", end="")
            result = self.process_single_image(image_path)
            results.append(result)
        
        return results
    
    def _is_structured_form(self, ocr_text: str) -> bool:
        """
        Detect if the OCR text appears to be from a structured driver log form.
        
        Args:
            ocr_text: Raw OCR text
            
        Returns:
            True if it looks like a structured form
        """
        form_indicators = [
            "Driver's Daily Time Log",
            "Time Log & Run Sheet", 
            "Time Arrived",
            "Time Departed",
            "Location & Purpose",
            "Daily Movement & Stop Log",
            "Vehicle ID / Plate",
            "Driver Name:",
            "Labor Name:",
            "Time Started Work:",
            "Time Ended Work:"
        ]
        
        # Count how many form indicators we find
        indicator_count = sum(1 for indicator in form_indicators if indicator.lower() in ocr_text.lower())
        
        # If we find 3 or more indicators, it's likely a structured form
        return indicator_count >= 3
    
    def export_location_visits_to_json(self, all_visits: List[LocationVisit], filename: str = None) -> str:
        """
        Export location visits to JSON format - one row per location visit.
        
        Args:
            all_visits: List of LocationVisit objects
            filename: Optional custom filename
            
        Returns:
            Path to the created JSON file
        """
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.json_prefix}_visits_{timestamp}.json"
        
        output_path = Path(self.output_folder) / filename
        
        # Custom JSON encoder to handle dates and times
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (date, datetime)):
                    return obj.isoformat()
                elif isinstance(obj, time):
                    return obj.strftime("%H:%M:%S")
                return super().default(obj)
        
        # Prepare data for JSON export
        export_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_visits": len(all_visits),
                "total_images": len(set(visit.source_image for visit in all_visits)),
                "unique_drivers": len(set(visit.driver_name for visit in all_visits)),
                "unique_locations": len(set(visit.location for visit in all_visits)),
                "pipeline_version": "2.1.0 - Location Visits"
            },
            "visits": []
        }
        
        # Convert each LocationVisit to dictionary
        for visit in all_visits:
            visit_dict = visit.dict()
            
            # Convert date/time objects to strings for JSON serialization
            if visit_dict.get('log_date'):
                visit_dict['log_date'] = visit_dict['log_date'].isoformat()
            if visit_dict.get('arrival_time'):
                visit_dict['arrival_time'] = visit_dict['arrival_time'].strftime("%H:%M:%S")
            if visit_dict.get('departure_time'):
                visit_dict['departure_time'] = visit_dict['departure_time'].strftime("%H:%M:%S")
            
            export_data["visits"].append(visit_dict)
        
        # Write JSON file with proper formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, cls=DateTimeEncoder, indent=2, ensure_ascii=False)
        
        return str(output_path)
    
    def export_to_json(self, all_results: List[DriverLogData], filename: str = None) -> str:
        """
        Export all extracted data to a JSON file.
        
        Args:
            all_results: List of DriverLogData objects
            filename: Optional custom filename
            
        Returns:
            Path to the created JSON file
        """
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.json_prefix}_{timestamp}.json"
        
        output_path = Path(self.output_folder) / filename
        
        # Custom JSON encoder to handle dates and times
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (date, datetime)):
                    return obj.isoformat()
                elif isinstance(obj, time):
                    return obj.strftime("%H:%M:%S")
                return super().default(obj)
        
        # Prepare data for JSON export
        export_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_images_processed": len(all_results),
                "total_entries_extracted": sum(len(result.entries) for result in all_results),
                "pipeline_version": "1.0.0"
            },
            "results": []
        }
        
        # Convert each DriverLogData to dictionary
        for log_data in all_results:
            result_dict = {
                "source_file": log_data.source_file,
                "extraction_date": log_data.extraction_date.isoformat(),
                "ocr_confidence": log_data.ocr_confidence,
                "processing_notes": log_data.processing_notes,
                "entries": []
            }
            
            # Add all entries for this document
            for entry in log_data.entries:
                entry_dict = entry.dict()
                
                # Convert date/time objects to strings for JSON serialization
                if entry_dict.get('log_date'):
                    entry_dict['log_date'] = entry_dict['log_date'].isoformat()
                if entry_dict.get('start_time'):
                    entry_dict['start_time'] = entry_dict['start_time'].strftime("%H:%M:%S")
                if entry_dict.get('end_time'):
                    entry_dict['end_time'] = entry_dict['end_time'].strftime("%H:%M:%S")
                
                result_dict["entries"].append(entry_dict)
            
            # If no entries were found, add a placeholder
            if not result_dict["entries"]:
                result_dict["entries"].append({
                    "driver_name": "No data extracted",
                    "log_date": None,
                    "extraction_status": "failed",
                    "error_reason": log_data.processing_notes or "No parseable data found"
                })
            
            export_data["results"].append(result_dict)
        
        # Write JSON file with proper formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        
        return str(output_path)
    
    def run_pipeline(self) -> None:
        """
        Run the complete OCR pipeline.
        
        This is the main method that orchestrates the entire process.
        """
        
        print("🚀 Starting OCR Pipeline")
        print("=" * 50)
        
        # Step 1: Get all image files
        try:
            image_files = self.get_image_files()
            if not image_files:
                print("❌ No image files found in the images folder!")
                print(f"   Please add image files to: {self.images_folder}")
                return
            
            print(f"📁 Found {len(image_files)} image files")
            
        except Exception as e:
            print(f"❌ Error getting image files: {e}")
            return
        
        # Step 2: Process images in batches and extract location visits
        all_results = []
        all_visits = []
        
        for i in range(0, len(image_files), self.max_batch_size):
            batch = image_files[i:i + self.max_batch_size]
            batch_num = (i // self.max_batch_size) + 1
            total_batches = (len(image_files) + self.max_batch_size - 1) // self.max_batch_size
            
            print(f"\n📦 Processing Batch {batch_num}/{total_batches} ({len(batch)} files)")
            print("-" * 30)
            
            batch_results = self.process_batch(batch)
            all_results.extend(batch_results)
            
            # Extract location visits from each image
            for image_path in batch:
                try:
                    # Get OCR text for this image
                    image_name = Path(image_path).name
                    print(f"📍 Extracting location visits from: {image_name}")
                    
                    # Read and process the image
                    with open(image_path, 'rb') as image_file:
                        content = image_file.read()
                    
                    image = vision.Image(content=content)
                    response = self.vision_client.text_detection(image=image)
                    
                    if response.text_annotations:
                        ocr_text = response.text_annotations[0].description
                        
                        # Check if this looks like a structured form
                        if self._is_structured_form(ocr_text):
                            print(f"  📋 Detected structured form format")
                            visits = self.parser.extract_from_structured_form(ocr_text, image_name)
                        else:
                            print(f"  📄 Using general extraction")
                            visits = self.parser.extract_location_visits(ocr_text, image_name)
                        
                        all_visits.extend(visits)
                        print(f"  ✓ Found {len(visits)} location visits")
                    else:
                        print(f"  ⚠️ No text detected in {image_name}")
                        
                except Exception as e:
                    print(f"  ❌ Error processing {image_name}: {e}")
        
        # Step 3: Export location visits to JSON (new format)
        print(f"\n💾 Exporting location visits to JSON...")
        try:
            visits_json_path = self.export_location_visits_to_json(all_visits)
            print(f"✓ Location visits exported to: {visits_json_path}")
            
        except Exception as e:
            print(f"❌ Error exporting location visits to JSON: {e}")
            return
        
        # Step 4: Also export traditional format for compatibility
        print(f"\n💾 Exporting traditional format to JSON...")
        try:
            json_path = self.export_to_json(all_results)
            print(f"✓ Traditional format exported to: {json_path}")
            
        except Exception as e:
            print(f"❌ Error exporting to JSON: {e}")
            return
        
        # Step 4: Print summary
        print(f"\n📊 Processing Summary")
        print("=" * 50)
        
        total_entries = sum(len(result.entries) for result in all_results)
        successful_files = sum(1 for result in all_results if result.entries)
        unique_drivers = len(set(visit.driver_name for visit in all_visits))
        unique_locations = len(set(visit.location for visit in all_visits))
        
        print(f"Total images processed: {len(image_files)}")
        print(f"Successful extractions: {successful_files}")
        print(f"Total log entries found: {total_entries}")
        print(f"Total location visits found: {len(all_visits)}")
        print(f"Unique drivers identified: {unique_drivers}")
        print(f"Unique locations visited: {unique_locations}")
        print(f"Location visits JSON: {visits_json_path}")
        print(f"Traditional JSON: {json_path}")
        
        if len(all_visits) > 0:
            print("\n🎉 Pipeline completed successfully!")
            print("\n💡 Next steps:")
            print(f"   - View location visits: {visits_json_path}")
            print(f"   - View traditional data: {json_path}")
            print("   - Convert visits to Excel: python json_to_excel.py")
            print("   - Convert to CSV: python json_to_csv.py")
        else:
            print("\n⚠️  Pipeline completed, but no location visits were extracted.")
            print("   Check your images and OCR settings.")


def main():
    """
    Main function - entry point of the script.
    
    For Python beginners:
    - This function runs when you execute the script
    - It handles any unexpected errors gracefully
    - It provides clear feedback about what's happening
    """
    
    try:
        # Create and run the OCR pipeline
        pipeline = OCRPipeline()
        pipeline.run_pipeline()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Pipeline stopped by user (Ctrl+C)")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check that your .env file is configured correctly")
        print("2. Verify your Google Cloud credentials are valid")
        print("3. Ensure the images folder exists and contains valid images")
        print("4. Check that all required packages are installed (pip install -r requirements.txt)")


if __name__ == "__main__":
    main()
