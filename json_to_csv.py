"""
JSON to CSV Converter

This script converts OCR results from JSON format to CSV format.
Perfect for importing into databases, analytics tools, or other systems.

For Python beginners:
- CSV files are simple comma-separated text files
- They're lightweight and widely supported
- Great for data analysis in tools like Excel, R, or Python pandas
- Easier to version control than Excel files
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from dotenv import load_dotenv


class JSONToCSVConverter:
    """
    Converts OCR JSON results to CSV format.
    
    This class handles:
    - Reading JSON files from the output folder
    - Converting nested JSON to flat CSV structure
    - Creating clean CSV files
    - Batch processing multiple JSON files
    """
    
    def __init__(self):
        """Initialize the converter with configuration."""
        
        # Load environment variables
        load_dotenv()
        
        self.output_folder = os.getenv('OUTPUT_FOLDER', 'output')
        self.csv_prefix = os.getenv('CSV_FILENAME_PREFIX', 'ocr_results')
        
        # Ensure output folder exists
        Path(self.output_folder).mkdir(exist_ok=True)
        
        print("📄 JSON to CSV Converter initialized")
        print(f"   Output folder: {self.output_folder}")
    
    def find_json_files(self, pattern: str = None) -> List[Path]:
        """Find all JSON files in the output folder."""
        
        output_path = Path(self.output_folder)
        if not output_path.exists():
            return []
        
        # Look for JSON files
        if pattern:
            json_files = list(output_path.glob(f"*{pattern}*.json"))
        else:
            json_files = list(output_path.glob("*.json"))
        
        return sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def load_json_data(self, json_file: Path) -> Dict[str, Any]:
        """Load and validate JSON data from file."""
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'results' not in data:
                raise ValueError("JSON file missing 'results' key")
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ValueError(f"Error reading JSON file: {e}")
    
    def flatten_json_to_dataframe(self, json_data: Dict[str, Any]) -> pd.DataFrame:
        """Convert nested JSON structure to flat DataFrame."""
        
        all_entries = []
        
        # Process each document result
        for result in json_data['results']:
            source_file = result['source_file']
            extraction_date = result['extraction_date']
            ocr_confidence = result.get('ocr_confidence')
            processing_notes = result.get('processing_notes', '')
            
            # Process each entry in the document
            for entry in result['entries']:
                # Create flat dictionary
                flat_entry = {
                    'source_file': source_file,
                    'extraction_date': extraction_date,
                    'ocr_confidence': ocr_confidence,
                    'driver_name': entry.get('driver_name'),
                    'log_date': entry.get('log_date'),
                    'vehicle_id': entry.get('vehicle_id'),
                    'start_time': entry.get('start_time'),
                    'end_time': entry.get('end_time'),
                    'start_location': entry.get('start_location'),
                    'end_location': entry.get('end_location'),
                    'miles_driven': entry.get('miles_driven'),
                    'fuel_used': entry.get('fuel_used'),
                    'notes': entry.get('notes'),
                    'extraction_status': entry.get('extraction_status', 'success'),
                    'error_reason': entry.get('error_reason'),
                    'processing_notes': processing_notes
                }
                
                all_entries.append(flat_entry)
        
        return pd.DataFrame(all_entries)
    
    def create_csv_file(self, df: pd.DataFrame, output_filename: str = None) -> str:
        """Create CSV file from DataFrame."""
        
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{self.csv_prefix}_{timestamp}.csv"
        
        output_path = Path(self.output_folder) / output_filename
        
        # Define column order for better readability
        preferred_columns = [
            'source_file', 'extraction_date', 'ocr_confidence',
            'driver_name', 'log_date', 'vehicle_id',
            'start_time', 'end_time', 'start_location', 'end_location',
            'miles_driven', 'fuel_used', 'notes',
            'extraction_status', 'error_reason', 'processing_notes'
        ]
        
        # Reorder columns (only include existing ones)
        available_columns = [col for col in preferred_columns if col in df.columns]
        remaining_columns = [col for col in df.columns if col not in available_columns]
        final_column_order = available_columns + remaining_columns
        
        df_ordered = df[final_column_order]
        
        # Export to CSV with proper encoding
        df_ordered.to_csv(output_path, index=False, encoding='utf-8')
        
        return str(output_path)
    
    def convert_single_file(self, json_file: Path, csv_filename: str = None) -> str:
        """Convert a single JSON file to CSV."""
        
        print(f"📄 Converting: {json_file.name}")
        
        try:
            # Load JSON data
            json_data = self.load_json_data(json_file)
            print(f"   ✓ Loaded {len(json_data['results'])} document results")
            
            # Convert to DataFrame
            df = self.flatten_json_to_dataframe(json_data)
            print(f"   ✓ Created DataFrame with {len(df)} rows")
            
            # Create CSV file
            if not csv_filename:
                base_name = json_file.stem
                csv_filename = f"{base_name}.csv"
            
            csv_path = self.create_csv_file(df, csv_filename)
            print(f"   ✓ CSV created: {Path(csv_path).name}")
            
            return csv_path
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            raise
    
    def convert_all_json_files(self, pattern: str = None) -> List[str]:
        """Convert all JSON files to CSV."""
        
        json_files = self.find_json_files(pattern)
        
        if not json_files:
            print("❌ No JSON files found in the output folder")
            return []
        
        print(f"📁 Found {len(json_files)} JSON files")
        
        csv_files = []
        
        for i, json_file in enumerate(json_files, 1):
            print(f"\n[{i}/{len(json_files)}] ", end="")
            
            try:
                csv_path = self.convert_single_file(json_file)
                csv_files.append(csv_path)
            except Exception as e:
                print(f"   ❌ Failed to convert {json_file.name}: {e}")
        
        return csv_files
    
    def convert_latest_json(self) -> str:
        """Convert the most recently created JSON file to CSV."""
        
        json_files = self.find_json_files()
        
        if not json_files:
            raise FileNotFoundError("No JSON files found in the output folder")
        
        latest_json = json_files[0]
        print(f"🕒 Converting latest JSON file: {latest_json.name}")
        
        return self.convert_single_file(latest_json)


def main():
    """Main function - handles command line usage."""
    
    print("📄 JSON to CSV Converter")
    print("=" * 40)
    
    try:
        converter = JSONToCSVConverter()
        
        # Check command line arguments
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            
            if arg == "--all":
                csv_files = converter.convert_all_json_files()
                if csv_files:
                    print(f"\n✅ Converted {len(csv_files)} files successfully!")
                    for csv_file in csv_files:
                        print(f"   📄 {Path(csv_file).name}")
                
            elif arg == "--latest":
                csv_file = converter.convert_latest_json()
                print(f"\n✅ Latest file converted: {Path(csv_file).name}")
                
            elif arg.endswith('.json'):
                json_path = Path(converter.output_folder) / arg
                if json_path.exists():
                    csv_file = converter.convert_single_file(json_path)
                    print(f"\n✅ File converted: {Path(csv_file).name}")
                else:
                    print(f"❌ JSON file not found: {arg}")
            else:
                print(f"❌ Unknown argument: {arg}")
                print("Usage: python json_to_csv.py [--all|--latest|filename.json]")
        
        else:
            # Default: convert latest JSON file
            try:
                csv_file = converter.convert_latest_json()
                print(f"\n✅ Latest file converted: {Path(csv_file).name}")
            except FileNotFoundError:
                print("❌ No JSON files found. Run the OCR pipeline first: python main.py")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
