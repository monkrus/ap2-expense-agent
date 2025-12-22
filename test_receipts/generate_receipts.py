"""
Generate test receipt images for testing OCR limits
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Receipt data
receipts = [
    {"vendor": "Starbucks Coffee", "amount": "12.45", "date": "2024-11-20", "items": ["Latte - $5.25", "Muffin - $4.20", "Tax - $3.00"]},
    {"vendor": "Office Depot", "amount": "87.99", "date": "2024-11-19", "items": ["Printer Paper - $45.00", "Pens (Box) - $12.99", "Stapler - $30.00"]},
    {"vendor": "Uber Ride", "amount": "24.50", "date": "2024-11-18", "items": ["Base Fare - $3.50", "Distance - $15.00", "Time - $6.00"]},
    {"vendor": "Delta Airlines", "amount": "342.00", "date": "2024-11-17", "items": ["Flight NYC-LAX - $299.00", "Seat Selection - $25.00", "Taxes - $18.00"]},
    {"vendor": "Hilton Hotels", "amount": "189.99", "date": "2024-11-16", "items": ["Room (1 night) - $159.00", "Parking - $20.00", "Tax - $10.99"]},
]

def create_receipt(receipt_data, filename):
    # Create image
    width, height = 400, 500
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    # Try to use a basic font, fallback to default
    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_medium = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    y = 20

    # Header
    draw.text((width//2 - 80, y), "RECEIPT", fill='black', font=font_large)
    y += 40

    # Vendor name
    draw.text((20, y), receipt_data["vendor"], fill='black', font=font_large)
    y += 40

    # Date
    draw.text((20, y), f"Date: {receipt_data['date']}", fill='gray', font=font_medium)
    y += 30

    # Separator
    draw.line([(20, y), (width-20, y)], fill='gray', width=1)
    y += 20

    # Items
    for item in receipt_data["items"]:
        draw.text((20, y), item, fill='black', font=font_medium)
        y += 25

    # Separator
    y += 10
    draw.line([(20, y), (width-20, y)], fill='gray', width=1)
    y += 20

    # Total
    draw.text((20, y), f"TOTAL: ${receipt_data['amount']}", fill='black', font=font_large)
    y += 50

    # Footer
    draw.text((width//2 - 60, y), "Thank you!", fill='gray', font=font_medium)

    # Save
    img.save(filename)
    print(f"Created: {filename}")

# Generate receipts
output_dir = os.path.dirname(os.path.abspath(__file__))
for i, receipt in enumerate(receipts, 1):
    filename = os.path.join(output_dir, f"receipt_{i}_{receipt['vendor'].replace(' ', '_').lower()}.png")
    create_receipt(receipt, filename)

print(f"\nCreated 5 test receipts in: {output_dir}")
