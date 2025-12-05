"""
Coaching Power Index Data Converter

This script converts an Excel file containing Coaching Power Index data to JSON format.

Usage:
    python convert_coaching_data.py <path_to_excel_file>

Example:
    python convert_coaching_data.py ~/Downloads/coaching_power_index.xlsx
"""

import sys
import json
from pathlib import Path

def convert_excel_to_json(excel_path):
    """Convert Excel file to JSON format for the Coaching Power Index."""
    try:
        import pandas as pd
    except ImportError:
        print("Error: pandas library not installed.")
        print("Install it with: pip install pandas openpyxl")
        sys.exit(1)
    
    # Read the Excel file
    print(f"Reading Excel file: {excel_path}")
    df = pd.read_excel(excel_path)
    
    # Display column names for verification
    print(f"\nFound {len(df)} rows and {len(df.columns)} columns")
    print("\nColumn names:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")
    
    # Convert to dictionary format
    coaches_data = []
    for idx, row in df.iterrows():
        coach_entry = {}
        for col in df.columns:
            value = row[col]
            # Handle NaN values
            if pd.isna(value):
                coach_entry[col] = None
            elif isinstance(value, (int, float)):
                # Keep numbers as numbers
                coach_entry[col] = value
            else:
                # Convert to string
                coach_entry[col] = str(value)
        coaches_data.append(coach_entry)
    
    # Create the final JSON structure
    output_data = {
        "last_updated": "2024-12-04",
        "season": "2024",
        "total_coaches": len(coaches_data),
        "coaches": coaches_data
    }
    
    # Save to JSON file
    output_path = Path("data/coaching_power_index.json")
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Successfully converted {len(coaches_data)} coaches to JSON")
    print(f"📁 Output saved to: {output_path.absolute()}")
    
    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_coaching_data.py <path_to_excel_file>")
        print("\nExample:")
        print("  python convert_coaching_data.py ~/Downloads/coaching_power_index.xlsx")
        print("  python convert_coaching_data.py ~/Downloads/coaching_power_index.csv")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    
    if not Path(excel_file).exists():
        print(f"Error: File not found: {excel_file}")
        sys.exit(1)
    
    convert_excel_to_json(excel_file)
