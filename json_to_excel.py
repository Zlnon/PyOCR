"""
JSON to Excel Converter

This script converts OCR results from JSON format to Excel format.
Perfect for when you want to analyze data in spreadsheet software.

For Python beginners:
- This script reads the JSON files created by main.py
- Converts the data into a pandas DataFrame
- Exports to Excel with proper formatting
- Handles multiple JSON files at once
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from dotenv import load_dotenv


class JSONToExcelConverter:
    """
    Converts OCR JSON results to Excel format.
    
    This class handles:
    - Reading JSON files from the output folder
    - Converting nested JSON to flat DataFrame structure
    - Creating formatted Excel files
    - Batch processing multiple JSON files
    """
    
    def __init__(self):
        """Initialize the converter with configuration."""
        
        # Load environment variables
        load_dotenv()
        
        self.output_folder = os.getenv('OUTPUT_FOLDER', 'output')
        self.excel_prefix = os.getenv('EXCEL_FILENAME_PREFIX', 'ocr_results')
        
        # Ensure output folder exists
        Path(self.output_folder).mkdir(exist_ok=True)
        
        print("📊 JSON to Excel Converter initialized")
        print(f"   Output folder: {self.output_folder}")
    
    def find_json_files(self, pattern: str = None) -> List[Path]:
        """
        Find all JSON files in the output folder.
        
        Args:
            pattern: Optional filename pattern to match
            
        Returns:
            List of JSON file paths
        """
        
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
        """
        Load and validate JSON data from file.
        
        Args:
            json_file: Path to JSON file
            
        Returns:
            Loaded JSON data dictionary
        """
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate JSON structure
            if 'results' not in data:
                raise ValueError("JSON file missing 'results' key")
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ValueError(f"Error reading JSON file: {e}")
    
    def flatten_json_to_dataframe(self, json_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Convert nested JSON structure to flat DataFrame.
        
        Args:
            json_data: Loaded JSON data
            
        Returns:
            Pandas DataFrame with flattened data
        """
        
        all_entries = []
        
        # Process each document result
        for result in json_data['results']:
            source_file = result['source_file']
            extraction_date = result['extraction_date']
            ocr_confidence = result.get('ocr_confidence')
            processing_notes = result.get('processing_notes', '')
            
            # Process each entry in the document
            for entry in result['entries']:
                # Create flat dictionary combining document and entry data
                flat_entry = {
                    # Document metadata
                    'source_file': source_file,
                    'extraction_date': extraction_date,
                    'ocr_confidence': ocr_confidence,
                    'processing_notes': processing_notes,
                    
                    # Entry data
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
                    
                    # Error handling fields
                    'extraction_status': entry.get('extraction_status', 'success'),
                    'error_reason': entry.get('error_reason')
                }
                
                all_entries.append(flat_entry)
        
        # Create DataFrame
        df = pd.DataFrame(all_entries)
        
        # Convert date columns to proper datetime types
        if 'extraction_date' in df.columns:
            df['extraction_date'] = pd.to_datetime(df['extraction_date']).dt.date
        
        if 'log_date' in df.columns:
            df['log_date'] = pd.to_datetime(df['log_date'], errors='coerce').dt.date
        
        return df
    
    def create_excel_file(self, df: pd.DataFrame, output_filename: str = None) -> str:
        """
        Create formatted Excel file from DataFrame.
        
        Args:
            df: DataFrame to export
            output_filename: Optional custom filename
            
        Returns:
            Path to created Excel file
        """
        
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{self.excel_prefix}_{timestamp}.xlsx"
        
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
        
        # Create Excel file with formatting
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Write main data sheet
            df_ordered.to_excel(writer, sheet_name='OCR Results', index=False)
            
            # Create summary sheet
            summary_data = {
                'Metric': [
                    'Total Records',
                    'Successful Extractions', 
                    'Failed Extractions',
                    'Unique Drivers',
                    'Unique Vehicles',
                    'Total Miles',
                    'Total Fuel (gallons)',
                    'Average OCR Confidence'
                ],
                'Value': [
                    len(df_ordered),
                    len(df_ordered[df_ordered['extraction_status'] != 'failed']),
                    len(df_ordered[df_ordered['extraction_status'] == 'failed']),
                    df_ordered['driver_name'].nunique() if 'driver_name' in df_ordered else 0,
                    df_ordered['vehicle_id'].nunique() if 'vehicle_id' in df_ordered else 0,
                    df_ordered['miles_driven'].sum() if 'miles_driven' in df_ordered else 0,
                    df_ordered['fuel_used'].sum() if 'fuel_used' in df_ordered else 0,
                    df_ordered['ocr_confidence'].mean() if 'ocr_confidence' in df_ordered else 0
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Format the main sheet
            workbook = writer.book
            main_sheet = writer.sheets['OCR Results']
            
            # Auto-adjust column widths
            for column in main_sheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        cell_length = len(str(cell.value))
                        if cell_length > max_length:
                            max_length = cell_length
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                main_sheet.column_dimensions[column_letter].width = adjusted_width
            
            # Format summary sheet
            summary_sheet = writer.sheets['Summary']
            summary_sheet.column_dimensions['A'].width = 25
            summary_sheet.column_dimensions['B'].width = 20
        
        return str(output_path)
    
    def convert_single_file(self, json_file: Path, excel_filename: str = None) -> str:
        """
        Convert a single JSON file to Excel.
        
        Args:
            json_file: Path to JSON file
            excel_filename: Optional custom Excel filename
            
        Returns:
            Path to created Excel file
        """
        
        print(f"📄 Converting: {json_file.name}")
        
        try:
            # Load JSON data
            json_data = self.load_json_data(json_file)
            print(f"   ✓ Loaded {len(json_data['results'])} document results")
            
            # Convert to DataFrame
            df = self.flatten_json_to_dataframe(json_data)
            print(f"   ✓ Created DataFrame with {len(df)} rows")
            
            # Create Excel file
            if not excel_filename:
                # Generate filename based on JSON filename
                base_name = json_file.stem
                excel_filename = f"{base_name}.xlsx"
            
            excel_path = self.create_excel_file(df, excel_filename)
            print(f"   ✓ Excel created: {Path(excel_path).name}")
            
            return excel_path
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            raise
    
    def convert_all_json_files(self, pattern: str = None) -> List[str]:
        """
        Convert all JSON files in the output folder to Excel.
        
        Args:
            pattern: Optional filename pattern to match
            
        Returns:
            List of created Excel file paths
        """
        
        json_files = self.find_json_files(pattern)
        
        if not json_files:
            print("❌ No JSON files found in the output folder")
            return []
        
        print(f"📁 Found {len(json_files)} JSON files")
        
        excel_files = []
        
        for i, json_file in enumerate(json_files, 1):
            print(f"\n[{i}/{len(json_files)}] ", end="")
            
            try:
                excel_path = self.convert_single_file(json_file)
                excel_files.append(excel_path)
            except Exception as e:
                print(f"   ❌ Failed to convert {json_file.name}: {e}")
        
        return excel_files
    
    def convert_latest_json(self) -> str:
        """
        Convert the most recently created JSON file to Excel.
        
        Returns:
            Path to created Excel file
        """
        
        json_files = self.find_json_files()
        
        if not json_files:
            raise FileNotFoundError("No JSON files found in the output folder")
        
        latest_json = json_files[0]  # Files are sorted by modification time, newest first
        print(f"🕒 Converting latest JSON file: {latest_json.name}")
        
        return self.convert_single_file(latest_json)


def main():
    """
    Main function - handles command line usage.
    """
    
    print("📊 JSON to Excel Converter")
    print("=" * 40)
    
    try:
        converter = JSONToExcelConverter()
        
        # Check command line arguments
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            
            if arg == "--all":
                # Convert all JSON files
                excel_files = converter.convert_all_json_files()
                if excel_files:
                    print(f"\n✅ Converted {len(excel_files)} files successfully!")
                    for excel_file in excel_files:
                        print(f"   📄 {Path(excel_file).name}")
                
            elif arg == "--latest":
                # Convert latest JSON file
                excel_file = converter.convert_latest_json()
                print(f"\n✅ Latest file converted: {Path(excel_file).name}")
                
            elif arg.endswith('.json'):
                # Convert specific JSON file
                json_path = Path(converter.output_folder) / arg
                if json_path.exists():
                    excel_file = converter.convert_single_file(json_path)
                    print(f"\n✅ File converted: {Path(excel_file).name}")
                else:
                    print(f"❌ JSON file not found: {arg}")
            else:
                print(f"❌ Unknown argument: {arg}")
                print("Usage: python json_to_excel.py [--all|--latest|filename.json]")
        
        else:
            # Default: convert latest JSON file
            try:
                excel_file = converter.convert_latest_json()
                print(f"\n✅ Latest file converted: {Path(excel_file).name}")
            except FileNotFoundError:
                print("❌ No JSON files found. Run the OCR pipeline first: python main.py")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
