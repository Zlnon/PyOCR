"""
Driver Setup Tool

This tool helps you easily add your actual driver names to the configuration.
Run this script to interactively add driver names to improve OCR accuracy.

Usage: python setup_drivers.py
"""

import os
from config import KNOWN_DRIVERS

def setup_drivers():
    """Interactive tool to add driver names to the configuration."""
    
    print("🚗 Driver Setup Tool")
    print("=" * 50)
    print("This tool helps you add your actual driver names for better OCR accuracy.")
    print(f"Currently configured drivers: {len(KNOWN_DRIVERS)}")
    print()
    
    # Show current drivers
    if KNOWN_DRIVERS:
        print("Current drivers:")
        for i, driver in enumerate(KNOWN_DRIVERS, 1):
            print(f"  {i:2d}. {driver}")
        print()
    
    # Ask if user wants to add more drivers
    add_more = input("Do you want to add more drivers? (y/n): ").lower().strip()
    
    if add_more != 'y':
        print("No changes made.")
        return
    
    new_drivers = []
    print("\nEnter driver names (press Enter with empty name to finish):")
    
    while True:
        name = input("Driver name: ").strip()
        if not name:
            break
        
        # Basic validation
        if len(name) < 2:
            print("Name too short, please enter a full name.")
            continue
        
        if name in KNOWN_DRIVERS or name in new_drivers:
            print("Driver already exists!")
            continue
        
        new_drivers.append(name)
        print(f"✓ Added: {name}")
    
    if not new_drivers:
        print("No new drivers added.")
        return
    
    # Generate the updated config
    print(f"\n✅ Ready to add {len(new_drivers)} new drivers:")
    for driver in new_drivers:
        print(f"  - {driver}")
    
    confirm = input("\nAdd these drivers to config.py? (y/n): ").lower().strip()
    
    if confirm == 'y':
        update_config_file(new_drivers)
        print("✅ Drivers added successfully!")
        print("Run the OCR pipeline again to see improved results.")
    else:
        print("Changes cancelled.")

def update_config_file(new_drivers):
    """Update the config.py file with new drivers."""
    
    # Read current config file
    with open('config.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the KNOWN_DRIVERS section and add new drivers
    drivers_list = '",\n    "'.join(new_drivers)
    insertion_point = '    # Add your actual drivers here:'
    
    if insertion_point in content:
        # Add after the comment
        replacement = f'{insertion_point}\n    "{drivers_list}",\n'
        content = content.replace(insertion_point, replacement)
    else:
        # Add before the closing bracket
        insertion_point = '    # etc...\n]'
        if insertion_point in content:
            replacement = f'    # etc...\n    "{drivers_list}",\n]'
            content = content.replace(insertion_point, replacement)
    
    # Write updated config
    with open('config.py', 'w', encoding='utf-8') as f:
        f.write(content)

def show_sample_names_from_results():
    """Show sample names extracted from previous OCR results to help user identify real names."""
    
    import json
    from pathlib import Path
    
    output_dir = Path('output')
    json_files = list(output_dir.glob('*.json'))
    
    if not json_files:
        print("No previous OCR results found.")
        return
    
    # Get the most recent results
    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
    
    print(f"\n📋 Sample names from latest OCR results ({latest_file.name}):")
    print("-" * 60)
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        names_found = set()
        for result in data.get('results', []):
            for entry in result.get('entries', []):
                name = entry.get('driver_name')
                if name and name != "Unknown Driver":
                    names_found.add(name)
        
        if names_found:
            for i, name in enumerate(sorted(names_found), 1):
                print(f"  {i:2d}. {name}")
            
            print(f"\n💡 Tip: Look at these extracted names and identify which ones are:")
            print("   ✓ Correct real driver names (add these to your list)")
            print("   ❌ OCR mistakes that should be corrected")
            print("   ❓ Unknown names that need clarification")
        else:
            print("No driver names found in results.")
            
    except Exception as e:
        print(f"Error reading results: {e}")

def main():
    """Main function."""
    
    print("Choose an option:")
    print("1. Add new drivers interactively")
    print("2. Show names from latest OCR results")
    print("3. Both")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice in ['2', '3']:
        show_sample_names_from_results()
    
    if choice in ['1', '3']:
        print("\n" + "="*50)
        setup_drivers()

if __name__ == "__main__":
    main()
