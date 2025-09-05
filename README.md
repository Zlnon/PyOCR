# Multi-Document OCR Data Extraction Pipeline

A comprehensive Python pipeline for extracting structured data from driver log documents using Google Cloud Vision API, with data validation and Excel export capabilities.

## 🎯 What This Pipeline Does

This project helps you automatically extract information from driver log images and convert it into structured Excel spreadsheets. Perfect for digitizing paper-based driver logs, delivery receipts, or similar documents.

**Key Features:**
- 📸 **OCR Text Extraction** - Uses Google Cloud Vision API for high-accuracy text recognition
- 🔍 **Smart Data Parsing** - Intelligently finds and extracts specific information (names, dates, times, etc.)
- ✅ **Data Validation** - Ensures extracted data is properly formatted and valid
- 📄 **JSON-First Export** - Outputs structured JSON for maximum flexibility
- 📊 **Multi-Format Conversion** - Easy conversion to Excel, CSV, or other formats
- 🔄 **Batch Processing** - Handles multiple images efficiently
- 🛡️ **Error Handling** - Gracefully handles OCR errors and missing data

## 📁 Project Structure

```
pyocr/
├── main.py                    # Main OCR pipeline (outputs JSON)
├── json_to_excel.py          # Convert JSON to Excel format
├── json_to_csv.py            # Convert JSON to CSV format
├── example_usage.py          # Learning examples and demos
├── requirements.txt           # Python dependencies
├── .env                      # Environment configuration
├── README.md                 # This file
├── parsers/                  # Text parsing modules
│   ├── __init__.py
│   └── driver_log_parser.py  # Driver log parsing logic
├── schemas/                  # Data validation schemas
│   ├── __init__.py
│   └── driver_log_schema.py  # Pydantic data models
├── images/                   # Input images (add your files here)
└── output/                   # Generated JSON, Excel, and CSV files
```

## 🚀 Quick Start Guide

### 1. Prerequisites

- Python 3.8 or higher
- Google Cloud Account with Vision API enabled
- Basic familiarity with command line

### 2. Installation

1. **Clone or download this project**
   ```bash
   # Navigate to the project directory
   cd pyocr
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google Cloud Vision API**
   
   a) Go to [Google Cloud Console](https://console.cloud.google.com/)
   
   b) Create a new project or select existing one
   
   c) Enable the Vision API:
      - Go to "APIs & Services" > "Library"
      - Search for "Vision API"
      - Click "Enable"
   
   d) Create service account credentials:
      - Go to "APIs & Services" > "Credentials"
      - Click "Create Credentials" > "Service Account"
      - Fill in the details and create
      - Click on the created service account
      - Go to "Keys" tab > "Add Key" > "Create New Key"
      - Choose "JSON" format and download the file
   
   e) Save the JSON file in your project directory

4. **Configure environment variables**
   
   Edit the `.env` file and update the path to your credentials:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=path/to/your/google-cloud-credentials.json
   ```

### 3. Usage

1. **Add your images**
   - Place your driver log images in the `images/` folder
   - Supported formats: JPG, PNG, GIF, BMP, TIFF, WebP

2. **Run the OCR pipeline**
   ```bash
   python main.py
   ```
   This creates JSON files in the `output/` folder with all extracted data.

3. **Convert to your preferred format**
   ```bash
   # Convert latest JSON to Excel
   python json_to_excel.py
   
   # Convert latest JSON to CSV  
   python json_to_csv.py
   
   # Convert all JSON files to Excel
   python json_to_excel.py --all
   
   # Convert specific JSON file
   python json_to_excel.py ocr_results_20240315_143022.json
   ```

4. **Check results**
   - JSON files: `ocr_results_YYYYMMDD_HHMMSS.json` (raw structured data)
   - Excel files: `ocr_results_YYYYMMDD_HHMMSS.xlsx` (formatted spreadsheets)
   - CSV files: `ocr_results_YYYYMMDD_HHMMSS.csv` (simple data files)

## 📋 What Data Gets Extracted

The pipeline is designed to extract the following information from driver logs:

| Field | Description | Required |
|-------|-------------|----------|
| Driver Name | Full name of the driver | ✅ |
| Log Date | Date of the log entry | ✅ |
| Vehicle ID | Vehicle/truck identification | ❌ |
| Start Time | Shift start time | ❌ |
| End Time | Shift end time | ❌ |
| Start Location | Starting address/location | ❌ |
| End Location | Ending address/location | ❌ |
| Miles Driven | Total miles/distance | ❌ |
| Fuel Used | Fuel consumption (gallons) | ❌ |
| Notes | Additional comments | ❌ |

## 📄 JSON-First Workflow

### Why JSON First?

The pipeline now exports to JSON before other formats, providing several advantages:

**🔧 Flexibility**
- Convert to any format without re-running OCR
- Preserve exact data types (dates, numbers, booleans)
- Easy to integrate with APIs and databases

**💾 Efficiency** 
- OCR is the slowest step - do it once, convert many times
- Experiment with different Excel layouts without re-processing
- Quick format switching for different use cases

**🔍 Data Integrity**
- JSON preserves the complete data structure
- No loss of precision in numbers or dates
- Maintains metadata about extraction process

**🚀 Workflow Benefits**
- Process images overnight, analyze data in the morning
- Share raw JSON with developers, Excel with business users
- Version control friendly (text-based format)

### JSON Structure

```json
{
  "metadata": {
    "export_timestamp": "2024-03-15T14:30:22.123456",
    "total_images_processed": 5,
    "total_entries_extracted": 12,
    "pipeline_version": "1.0.0"
  },
  "results": [
    {
      "source_file": "driver_log_001.jpg",
      "extraction_date": "2024-03-15",
      "ocr_confidence": 0.95,
      "processing_notes": "Successfully parsed entry 1",
      "entries": [
        {
          "driver_name": "John Smith",
          "log_date": "2024-03-14",
          "vehicle_id": "TRK001",
          "miles_driven": 245.5,
          "fuel_used": 18.2
        }
      ]
    }
  ]
}
```

## 🔧 Customization

### Adding New Document Types

To extract data from different document types:

1. **Create a new schema** in `schemas/`:
   ```python
   # schemas/invoice_schema.py
   from pydantic import BaseModel
   
   class InvoiceEntry(BaseModel):
       invoice_number: str
       amount: float
       # Add your fields here
   ```

2. **Create a new parser** in `parsers/`:
   ```python
   # parsers/invoice_parser.py
   class InvoiceParser:
       def parse_document(self, text, source_file):
           # Add your parsing logic here
   ```

3. **Update the main pipeline** to use your new parser

### Modifying Extraction Patterns

The parser uses regular expressions to find information. You can modify these patterns in `parsers/driver_log_parser.py`:

```python
# Example: Add new date format
self.date_patterns = [
    r'\\b(\\d{1,2})[/-](\\d{1,2})[/-](\\d{4})\\b',  # MM/DD/YYYY
    r'\\b(\\d{2})\\.(\\d{2})\\.(\\d{4})\\b',          # DD.MM.YYYY (European)
    # Add your pattern here
]
```

## 🔍 Understanding the Code (For Python Beginners)

### Key Concepts

1. **Modules and Packages**
   - `parsers/` and `schemas/` are Python packages
   - Each `.py` file is a module containing related functions and classes
   - `__init__.py` files make directories into packages

2. **Classes and Objects**
   - `DriverLogParser` is a class that contains methods for parsing text
   - `DriverLogEntry` is a Pydantic model that defines data structure
   - `OCRPipeline` orchestrates the entire process

3. **Environment Variables**
   - The `.env` file stores configuration without hardcoding values
   - `python-dotenv` loads these variables into your program

4. **Error Handling**
   - `try/except` blocks catch and handle errors gracefully
   - The pipeline continues processing even if some images fail

### File Breakdown

- **`main.py`** - The main script that runs everything
- **`schemas/driver_log_schema.py`** - Defines what data we want to extract
- **`parsers/driver_log_parser.py`** - Contains logic to find data in OCR text
- **`requirements.txt`** - Lists all Python packages needed
- **`.env`** - Configuration file for API keys and settings

## 🐛 Troubleshooting

### Common Issues

1. **"No module named 'google.cloud'"**
   ```bash
   pip install google-cloud-vision
   ```

2. **"GOOGLE_APPLICATION_CREDENTIALS not set"**
   - Check that your `.env` file has the correct path to your JSON credentials
   - Make sure the JSON file exists at that location

3. **"No text detected in image"**
   - Check image quality and resolution
   - Ensure text is clearly visible and not too small
   - Try different image formats

4. **"No image files found"**
   - Make sure images are in the `images/` folder
   - Check that files have supported extensions (.jpg, .png, etc.)

5. **Low OCR accuracy**
   - Use higher resolution images
   - Ensure good lighting and contrast
   - Avoid blurry or skewed images
   - Consider image preprocessing (rotation, contrast adjustment)

### Getting Help

1. Check the console output for detailed error messages
2. Look at the `processing_notes` column in the Excel output
3. Verify your Google Cloud setup and credentials
4. Test with a single, high-quality image first

## 📊 Example Output

The Excel file will contain columns like:

| source_file | driver_name | log_date | vehicle_id | start_time | miles_driven | ... |
|-------------|-------------|----------|------------|------------|--------------|-----|
| log1.jpg | John Smith | 2024-01-15 | TRK001 | 08:00:00 | 245.5 | ... |
| log2.jpg | Jane Doe | 2024-01-15 | TRK002 | 09:30:00 | 189.2 | ... |

## 🔒 Security Notes

- Keep your Google Cloud credentials secure
- Don't commit the `.env` file to version control
- Use Google Cloud IAM to limit API permissions
- Consider encrypting sensitive data in production

## 📈 Performance Tips

- Process images in smaller batches for better memory usage
- Use higher quality images for better OCR accuracy
- Consider image preprocessing for challenging documents
- Monitor Google Cloud API usage and costs

## 🤝 Contributing

Feel free to extend this pipeline for your specific needs:
- Add new document types
- Improve parsing accuracy
- Add new export formats
- Enhance error handling

## 📄 License

This project is provided as-is for educational and practical use. Modify and distribute as needed.

---

**Happy OCR processing! 🎉**

For questions or improvements, feel free to modify the code to suit your specific document types and requirements.
