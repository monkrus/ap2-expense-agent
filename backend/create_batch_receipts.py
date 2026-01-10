"""
Generate sample receipt images for batch upload testing
"""
from PIL import Image, ImageDraw, ImageFont
import random
from datetime import datetime, timedelta

def create_receipt(filename, store_name, items, total, date, category="General"):
    """Create a realistic-looking receipt image"""

    # Create image
    width, height = 600, 800
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    # Try to use a system font, fallback to default
    try:
        title_font = ImageFont.truetype("arial.ttf", 32)
        header_font = ImageFont.truetype("arial.ttf", 24)
        normal_font = ImageFont.truetype("arial.ttf", 18)
        small_font = ImageFont.truetype("arial.ttf", 14)
    except:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        normal_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    y = 40

    # Store name
    draw.text((300, y), store_name, fill='black', font=title_font, anchor="mm")
    y += 50

    # Category badge
    draw.rectangle([220, y, 380, y+30], fill='#4F46E5')
    draw.text((300, y+15), category.upper(), fill='white', font=small_font, anchor="mm")
    y += 50

    # Date and time
    draw.text((300, y), date.strftime("%B %d, %Y  %I:%M %p"), fill='black', font=normal_font, anchor="mm")
    y += 40

    # Separator line
    draw.line([(50, y), (550, y)], fill='black', width=2)
    y += 30

    # Items
    for item, price in items:
        draw.text((60, y), item, fill='black', font=normal_font)
        draw.text((540, y), f"${price:.2f}", fill='black', font=normal_font, anchor="rm")
        y += 35

    # Separator line
    y += 10
    draw.line([(50, y), (550, y)], fill='black', width=2)
    y += 30

    # Subtotal
    subtotal = sum(price for _, price in items)
    draw.text((60, y), "Subtotal", fill='black', font=normal_font)
    draw.text((540, y), f"${subtotal:.2f}", fill='black', font=normal_font, anchor="rm")
    y += 35

    # Tax
    tax = subtotal * 0.08
    draw.text((60, y), "Tax (8%)", fill='black', font=normal_font)
    draw.text((540, y), f"${tax:.2f}", fill='black', font=normal_font, anchor="rm")
    y += 35

    # Total
    draw.rectangle([50, y, 550, y+45], outline='black', width=3)
    draw.text((70, y+22), "TOTAL", fill='black', font=header_font)
    draw.text((530, y+22), f"${total:.2f}", fill='black', font=header_font, anchor="rm")
    y += 70

    # Payment method
    draw.text((300, y), "Payment: Credit Card ****1234", fill='gray', font=small_font, anchor="mm")
    y += 30

    # Thank you message
    draw.text((300, y), "Thank you for your business!", fill='gray', font=small_font, anchor="mm")
    y += 40

    # Store info
    draw.text((300, y), "123 Business St, City, ST 12345", fill='gray', font=small_font, anchor="mm")
    y += 25
    draw.text((300, y), "Tel: (555) 123-4567", fill='gray', font=small_font, anchor="mm")

    # Save
    img.save(filename)
    print(f"Created: {filename}")

# Generate receipts for different scenarios
receipts = [
    {
        "filename": "sample_receipts/batch_test_1_office_supplies.jpg",
        "store_name": "Office Depot",
        "items": [
            ("Printer Paper (5 reams)", 45.00),
            ("Pens (Box of 12)", 8.99),
            ("Notebooks (Pack of 5)", 12.50),
            ("Stapler", 15.99),
        ],
        "total": 88.84,
        "date": datetime.now() - timedelta(days=2),
        "category": "Office Supplies"
    },
    {
        "filename": "sample_receipts/batch_test_2_client_lunch.jpg",
        "store_name": "The Steakhouse",
        "items": [
            ("Grilled Salmon x2", 56.00),
            ("Caesar Salad x2", 24.00),
            ("House Wine", 28.00),
            ("Dessert x2", 18.00),
        ],
        "total": 136.08,
        "date": datetime.now() - timedelta(days=5),
        "category": "Meals & Entertainment"
    },
    {
        "filename": "sample_receipts/batch_test_3_taxi.jpg",
        "store_name": "Yellow Cab Co.",
        "items": [
            ("Airport to Hotel", 45.00),
            ("Toll Fee", 3.50),
        ],
        "total": 52.38,
        "date": datetime.now() - timedelta(days=7),
        "category": "Transportation"
    },
    {
        "filename": "sample_receipts/batch_test_4_hotel.jpg",
        "store_name": "Grand Hotel",
        "items": [
            ("Room Rate (2 nights)", 340.00),
            ("Room Service", 45.00),
            ("WiFi Premium", 15.00),
        ],
        "total": 432.00,
        "date": datetime.now() - timedelta(days=8),
        "category": "Lodging"
    },
    {
        "filename": "sample_receipts/batch_test_5_gas.jpg",
        "store_name": "Shell Gas Station",
        "items": [
            ("Regular Gasoline 15.2 gal", 54.72),
            ("Car Wash", 12.00),
        ],
        "total": 72.06,
        "date": datetime.now() - timedelta(days=1),
        "category": "Fuel"
    },
    {
        "filename": "sample_receipts/batch_test_6_software.jpg",
        "store_name": "TechStore Online",
        "items": [
            ("Adobe Creative Cloud (1yr)", 599.88),
            ("Slack Pro Plan (1mo)", 12.50),
        ],
        "total": 661.05,
        "date": datetime.now() - timedelta(days=3),
        "category": "Software"
    },
]

# Create sample_receipts directory if it doesn't exist
import os
os.makedirs("sample_receipts", exist_ok=True)

# Generate all receipts
for receipt in receipts:
    create_receipt(**receipt)

print("\n✅ Successfully created 6 batch test receipts!")
print("📁 Location: backend/sample_receipts/")
print("\nFiles created:")
for receipt in receipts:
    print(f"  - {receipt['filename']}")
