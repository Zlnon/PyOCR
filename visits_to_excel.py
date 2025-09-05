"""
Location Visits to Excel Converter

This script converts the location visits JSON format to Excel.
Each row represents one location visit with arrival/departure times.
"""

import json
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

def convert_visits_to_excel(json_file_path: str = None):
    """
    Convert location visits JSON to Excel format.
    
    Args:
        json_file_path: Path to the JSON file. If None, finds the latest visits file.
    """
    
    output_folder = Path("output")
    
    # Find the JSON file
    if json_file_path is None:
        # Look for the latest visits JSON file
        visits_files = list(output_folder.glob("*visits*.json"))
        if not visits_files:
            print("❌ No visits JSON files found in output folder!")
            return
        
        json_file_path = max(visits_files, key=lambda x: x.stat().st_mtime)
        print(f"📄 Using latest visits file: {json_file_path.name}")
    else:
        json_file_path = Path(json_file_path)
    
    # Load the JSON data
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return
    
    # Extract visits data
    visits = data.get('visits', [])
    if not visits:
        print("❌ No visits found in JSON file!")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(visits)
    
    # Reorder columns for better readability
    column_order = [
        'source_image', 'driver_name', 'labor_name', 'log_date', 'location', 
        'location_category', 'arrival_time', 'departure_time', 
        'vehicle_id', 'visit_sequence', 'notes'
    ]
    
    # Only include columns that exist
    available_columns = [col for col in column_order if col in df.columns]
    df = df[available_columns]
    
    # Create Excel file path
    excel_file_path = json_file_path.with_suffix('.xlsx')
    
    # Create Excel writer
    with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
        
        # Write main visits sheet
        df.to_excel(writer, sheet_name='Location Visits', index=False)
        
        # Create summary sheet
        summary_data = []
        
        # Add metadata
        metadata = data.get('metadata', {})
        summary_data.extend([
            ['Export Timestamp', metadata.get('export_timestamp', 'N/A')],
            ['Total Visits', metadata.get('total_visits', len(visits))],
            ['Total Images', metadata.get('total_images', len(df['source_image'].unique()))],
            ['Unique Drivers', metadata.get('unique_drivers', len(df['driver_name'].unique()))],
            ['Unique Locations', metadata.get('unique_locations', len(df['location'].unique()))],
            ['Pipeline Version', metadata.get('pipeline_version', 'N/A')],
            ['', ''],  # Empty row
        ])
        
        # Add driver summary
        summary_data.append(['DRIVER SUMMARY', ''])
        driver_counts = df['driver_name'].value_counts()
        for driver, count in driver_counts.items():
            summary_data.append([driver, f"{count} visits"])
        
        summary_data.append(['', ''])  # Empty row
        
        # Add location category summary
        summary_data.append(['LOCATION CATEGORY SUMMARY', ''])
        if 'location_category' in df.columns:
            category_counts = df['location_category'].value_counts()
            for category, count in category_counts.items():
                summary_data.append([category, f"{count} visits"])
        
        summary_data.append(['', ''])  # Empty row
        
        # Add location summary
        summary_data.append(['LOCATION SUMMARY', ''])
        location_counts = df['location'].value_counts()
        for location, count in location_counts.items():
            summary_data.append([location, f"{count} visits"])
        
        # Create summary DataFrame and write to Excel
        summary_df = pd.DataFrame(summary_data, columns=['Metric', 'Value'])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Auto-adjust column widths
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"✅ Excel file created: {excel_file_path}")
    print(f"   📊 {len(visits)} visits across {len(df['source_image'].unique())} images")
    print(f"   👥 {len(df['driver_name'].unique())} unique drivers")
    print(f"   📍 {len(df['location'].unique())} unique locations")
    
    return str(excel_file_path)

def main():
    """Main function to run the converter."""
    
    print("📊 Location Visits to Excel Converter")
    print("=" * 40)
    
    # Check if a specific file was provided
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        convert_visits_to_excel(json_file)
    else:
        convert_visits_to_excel()

if __name__ == "__main__":
    main()
