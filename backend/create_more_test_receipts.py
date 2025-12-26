"""
Create additional test receipt batches for comprehensive testing.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Create additional test directories
BATCH1_DIR = Path("test_receipts_batch1_small")  # 3 receipts - under daily limit
BATCH2_DIR = Path("test_receipts_batch2_limit")  # Exactly 3 receipts - at daily limit
BATCH3_DIR = Path("test_receipts_batch3_large")  # 5 receipts - test larger batch
BATCH4_DIR = Path("test_receipts_batch4_edge")   # Edge cases (low amounts, weird formats)

BATCH1_DIR.mkdir(exist_ok=True)
BATCH2_DIR.mkdir(exist_ok=True)
BATCH3_DIR.mkdir(exist_ok=True)
BATCH4_DIR.mkdir(exist_ok=True)

# Batch 1: Small batch (3 receipts)
batch1_receipts = [
    {
        "filename": "hotel_receipt.png",
        "vendor": "Hilton Hotels",
        "date": "2025-12-15",
        "amount": "$345.00",
        "items": ["Room (2 nights) - $300.00", "Resort Fee - $45.00"],
    },
    {
        "filename": "restaurant_dinner.png",
        "vendor": "The Capital Grille",
        "date": "2025-12-16",
        "amount": "$125.50",
        "items": ["Dinner for 2 - $98.00", "Wine - $22.00", "Tax & Tip - $5.50"],
    },
    {
        "filename": "taxi_receipt.png",
        "vendor": "Yellow Cab Company",
        "date": "2025-12-17",
        "amount": "$35.00",
        "items": ["Ride to Airport - $28.00", "Tip - $7.00"],
    },
]

# Batch 2: Exactly at daily limit (3 receipts - Free tier limit)
batch2_receipts = [
    {
        "filename": "lunch_receipt1.png",
        "vendor": "Chipotle Mexican Grill",
        "date": "2025-12-18",
        "amount": "$14.25",
        "items": ["Burrito Bowl - $10.95", "Guacamole - $2.80", "Drink - $0.50"],
    },
    {
        "filename": "lunch_receipt2.png",
        "vendor": "Panera Bread",
        "date": "2025-12-19",
        "amount": "$18.75",
        "items": ["You Pick 2 - $12.99", "Coffee - $3.49", "Cookie - $2.27"],
    },
    {
        "filename": "lunch_receipt3.png",
        "vendor": "Five Guys",
        "date": "2025-12-20",
        "amount": "$22.00",
        "items": ["Cheeseburger - $9.99", "Fries - $5.99", "Shake - $6.02"],
    },
]

# Batch 3: Larger batch (5 receipts)
batch3_receipts = [
    {
        "filename": "office_supplies1.png",
        "vendor": "Staples",
        "date": "2025-12-10",
        "amount": "$67.89",
        "items": ["Printer Ink - $45.99", "Paper - $18.90", "Tax - $3.00"],
    },
    {
        "filename": "office_supplies2.png",
        "vendor": "Best Buy",
        "date": "2025-12-11",
        "amount": "$299.99",
        "items": ["Wireless Mouse - $49.99", "Keyboard - $129.99", "Monitor Cable - $19.99", "Extended Warranty - $100.02"],
    },
    {
        "filename": "software_subscription.png",
        "vendor": "Adobe Creative Cloud",
        "date": "2025-12-12",
        "amount": "$54.99",
        "items": ["Monthly Subscription - $54.99"],
    },
    {
        "filename": "internet_bill.png",
        "vendor": "Comcast Xfinity",
        "date": "2025-12-13",
        "amount": "$89.99",
        "items": ["Internet Service - $79.99", "Equipment Rental - $10.00"],
    },
    {
        "filename": "phone_bill.png",
        "vendor": "Verizon Wireless",
        "date": "2025-12-14",
        "amount": "$125.00",
        "items": ["3 Lines - $100.00", "Insurance - $15.00", "Tax - $10.00"],
    },
]

# Batch 4: Edge cases
batch4_receipts = [
    {
        "filename": "small_amount.png",
        "vendor": "7-Eleven",
        "date": "2025-12-05",
        "amount": "$2.50",
        "items": ["Coffee - $1.99", "Tax - $0.51"],
    },
    {
        "filename": "no_tax.png",
        "vendor": "Farmer's Market",
        "date": "2025-12-06",
        "amount": "$15.00",
        "items": ["Fresh Vegetables - $15.00"],
    },
    {
        "filename": "international.png",
        "vendor": "Tokyo Sushi Bar",
        "date": "2025-12-07",
        "amount": "$42.50",
        "items": ["Sushi Platter - $38.00", "Miso Soup - $3.50", "Tax - $1.00"],
    },
]


def create_receipt_image(receipt_data, output_path):
    """Create a simple receipt image with text."""
    width = 600
    height = 400
    bg_color = (255, 255, 255)
    text_color = (0, 0, 0)

    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_medium = ImageFont.truetype("arial.ttf", 18)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    y = 30
    draw.text((50, y), receipt_data["vendor"], fill=text_color, font=font_large)
    y += 50
    draw.text((50, y), f"Date: {receipt_data['date']}", fill=text_color, font=font_small)
    y += 30
    draw.line([(50, y), (width-50, y)], fill=text_color, width=1)
    y += 20

    for item in receipt_data["items"]:
        draw.text((50, y), item, fill=text_color, font=font_small)
        y += 25

    y += 10
    draw.line([(50, y), (width-50, y)], fill=text_color, width=2)
    y += 20
    draw.text((50, y), f"TOTAL: {receipt_data['amount']}", fill=text_color, font=font_medium)

    img.save(output_path)


# Create all batches
print("Creating test receipt batches...\n")

print("BATCH 1: Small batch (3 receipts)")
print(f"Directory: {BATCH1_DIR.absolute()}")
for receipt in batch1_receipts:
    output_path = BATCH1_DIR / receipt["filename"]
    create_receipt_image(receipt, output_path)
    print(f"  - {receipt['filename']}")

print(f"\nBATCH 2: Daily limit test (3 receipts - Free tier daily limit)")
print(f"Directory: {BATCH2_DIR.absolute()}")
for receipt in batch2_receipts:
    output_path = BATCH2_DIR / receipt["filename"]
    create_receipt_image(receipt, output_path)
    print(f"  - {receipt['filename']}")

print(f"\nBATCH 3: Larger batch (5 receipts)")
print(f"Directory: {BATCH3_DIR.absolute()}")
for receipt in batch3_receipts:
    output_path = BATCH3_DIR / receipt["filename"]
    create_receipt_image(receipt, output_path)
    print(f"  - {receipt['filename']}")

print(f"\nBATCH 4: Edge cases (3 receipts)")
print(f"Directory: {BATCH4_DIR.absolute()}")
for receipt in batch4_receipts:
    output_path = BATCH4_DIR / receipt["filename"]
    create_receipt_image(receipt, output_path)
    print(f"  - {receipt['filename']}")

print("\n" + "="*60)
print("SUMMARY:")
print("="*60)
print(f"Batch 1 (Small): {len(batch1_receipts)} receipts - {BATCH1_DIR.absolute()}")
print(f"Batch 2 (Limit): {len(batch2_receipts)} receipts - {BATCH2_DIR.absolute()}")
print(f"Batch 3 (Large): {len(batch3_receipts)} receipts - {BATCH3_DIR.absolute()}")
print(f"Batch 4 (Edge):  {len(batch4_receipts)} receipts - {BATCH4_DIR.absolute()}")
print(f"\nTotal: {len(batch1_receipts) + len(batch2_receipts) + len(batch3_receipts) + len(batch4_receipts)} test receipts created!")
print("\nTesting scenarios:")
print("  - Batch 1: Normal small upload")
print("  - Batch 2: Test Free tier daily limit (3 OCR scans/day)")
print("  - Batch 3: Test larger batch (will exceed Free tier daily limit)")
print("  - Batch 4: Edge cases (small amounts, no tax, international)")
