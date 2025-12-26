"""
Create test receipt images for batch upload testing.
Generates simple receipt-like images with text.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

# Create test receipts directory
TEST_DIR = Path("test_receipts")
TEST_DIR.mkdir(exist_ok=True)

# Receipt data
receipts = [
    {
        "filename": "receipt_starbucks.png",
        "vendor": "Starbucks Coffee",
        "date": "2025-12-20",
        "amount": "$12.45",
        "items": ["Grande Latte - $5.95", "Blueberry Muffin - $3.50", "Tip - $3.00"],
    },
    {
        "filename": "receipt_uber.png",
        "vendor": "Uber Technologies",
        "date": "2025-12-21",
        "amount": "$28.75",
        "items": ["Ride from Airport - $25.00", "Service Fee - $3.75"],
    },
    {
        "filename": "receipt_amazon.png",
        "vendor": "Amazon.com",
        "date": "2025-12-22",
        "amount": "$89.99",
        "items": ["Office Chair - $79.99", "Shipping - $10.00"],
    },
    {
        "filename": "receipt_subway.png",
        "vendor": "Subway Restaurant",
        "date": "2025-12-23",
        "amount": "$9.50",
        "items": ["Footlong Sub - $7.99", "Cookie - $1.51"],
    },
    {
        "filename": "receipt_office_depot.png",
        "vendor": "Office Depot",
        "date": "2025-12-24",
        "amount": "$156.78",
        "items": [
            "Printer Paper (5 reams) - $45.00",
            "Pens (Box) - $12.99",
            "Notebooks (12) - $23.99",
            "Stapler - $14.80",
            "Tax - $11.00"
        ],
    },
    {
        "filename": "receipt_gas_station.png",
        "vendor": "Shell Gas Station",
        "date": "2025-12-25",
        "amount": "$65.00",
        "items": ["Premium Fuel (15 gal) - $65.00"],
    },
]


def create_receipt_image(receipt_data, output_path):
    """Create a simple receipt image with text."""

    # Image settings
    width = 600
    height = 400
    bg_color = (255, 255, 255)
    text_color = (0, 0, 0)

    # Create image
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Try to use a system font, fallback to default
    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_medium = ImageFont.truetype("arial.ttf", 18)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except:
        # Fallback to default font
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw receipt content
    y = 30

    # Vendor name
    draw.text((50, y), receipt_data["vendor"], fill=text_color, font=font_large)
    y += 50

    # Date
    draw.text((50, y), f"Date: {receipt_data['date']}", fill=text_color, font=font_small)
    y += 30

    # Separator line
    draw.line([(50, y), (width-50, y)], fill=text_color, width=1)
    y += 20

    # Items
    for item in receipt_data["items"]:
        draw.text((50, y), item, fill=text_color, font=font_small)
        y += 25

    # Separator line
    y += 10
    draw.line([(50, y), (width-50, y)], fill=text_color, width=2)
    y += 20

    # Total
    draw.text((50, y), f"TOTAL: {receipt_data['amount']}", fill=text_color, font=font_medium)

    # Save image
    img.save(output_path)
    print(f"Created: {output_path}")


# Create all test receipts
print("Creating test receipt images...")
print(f"Output directory: {TEST_DIR.absolute()}\n")

for receipt in receipts:
    output_path = TEST_DIR / receipt["filename"]
    create_receipt_image(receipt, output_path)

print(f"\nCreated {len(receipts)} test receipt images!")
print(f"\nFiles created in: {TEST_DIR.absolute()}")
print("\nYou can now use these files to test batch upload:")
print("1. Go to http://localhost:5173")
print("2. Navigate to receipts/upload page")
print("3. Upload these test receipt images")
print("\nNote: OCR will extract data from these images using Gemini Vision AI")
