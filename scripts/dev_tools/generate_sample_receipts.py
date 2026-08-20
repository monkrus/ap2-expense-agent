"""
Generate sample receipt images for testing receipt upload functionality
"""
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime, timedelta
import random

# Create samples directory
SAMPLES_DIR = "sample_receipts"
os.makedirs(SAMPLES_DIR, exist_ok=True)

def create_receipt_image(
    vendor_name,
    amount,
    date,
    items,
    filename,
    category="OFFICE_SUPPLIES"
):
    """Create a realistic-looking receipt image"""

    # Create image (standard receipt size: 800x1200 px)
    width, height = 800, 1200
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    # Try to use a decent font, fall back to default if not available
    try:
        title_font = ImageFont.truetype("arial.ttf", 40)
        header_font = ImageFont.truetype("arial.ttf", 28)
        body_font = ImageFont.truetype("arial.ttf", 24)
        small_font = ImageFont.truetype("arial.ttf", 20)
    except:
        # Fallback to default font
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    y_position = 40

    # Draw vendor name (centered)
    draw.text((width//2, y_position), vendor_name, fill='black',
              font=title_font, anchor="mt")
    y_position += 60

    # Draw address
    draw.text((width//2, y_position), "123 Business Street", fill='gray',
              font=small_font, anchor="mt")
    y_position += 30
    draw.text((width//2, y_position), "New York, NY 10001", fill='gray',
              font=small_font, anchor="mt")
    y_position += 30
    draw.text((width//2, y_position), "Tel: (555) 123-4567", fill='gray',
              font=small_font, anchor="mt")
    y_position += 60

    # Draw separator line
    draw.line([(50, y_position), (width-50, y_position)], fill='black', width=2)
    y_position += 40

    # Draw date
    draw.text((80, y_position), f"Date: {date}", fill='black', font=body_font)
    y_position += 50

    # Draw items
    draw.text((80, y_position), "ITEMS:", fill='black', font=header_font)
    y_position += 40

    subtotal = 0
    for item_name, item_price in items:
        draw.text((100, y_position), item_name, fill='black', font=body_font)
        price_text = f"${item_price:.2f}"
        draw.text((width-150, y_position), price_text, fill='black', font=body_font)
        y_position += 35
        subtotal += item_price

    y_position += 20
    draw.line([(50, y_position), (width-50, y_position)], fill='black', width=1)
    y_position += 30

    # Draw totals
    tax = subtotal * 0.08  # 8% tax
    total = subtotal + tax

    draw.text((100, y_position), "Subtotal:", fill='black', font=body_font)
    draw.text((width-150, y_position), f"${subtotal:.2f}", fill='black', font=body_font)
    y_position += 35

    draw.text((100, y_position), "Tax (8%):", fill='black', font=body_font)
    draw.text((width-150, y_position), f"${tax:.2f}", fill='black', font=body_font)
    y_position += 35

    draw.line([(50, y_position), (width-50, y_position)], fill='black', width=2)
    y_position += 30

    draw.text((100, y_position), "TOTAL:", fill='black', font=header_font)
    draw.text((width-150, y_position), f"${total:.2f}", fill='black', font=header_font)
    y_position += 60

    # Draw footer
    draw.line([(50, y_position), (width-50, y_position)], fill='black', width=1)
    y_position += 30
    draw.text((width//2, y_position), "Thank you for your business!",
              fill='gray', font=small_font, anchor="mt")
    y_position += 30
    draw.text((width//2, y_position), f"Category: {category}",
              fill='gray', font=small_font, anchor="mt")

    # Save image
    filepath = os.path.join(SAMPLES_DIR, filename)
    img.save(filepath, 'PNG')
    print(f"Created: {filepath} (${total:.2f})")
    return filepath, total


# Generate sample receipts
print("=== Generating Sample Receipts ===\n")

receipts_created = []

# 1. Office Supplies Receipt
receipt1, total1 = create_receipt_image(
    vendor_name="Office Depot",
    amount=150.00,
    date=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
    items=[
        ("Printer Paper (5 reams)", 45.00),
        ("Pens (Box of 50)", 12.99),
        ("Folders (Pack of 25)", 18.50),
        ("Desk Organizer", 35.99),
        ("Stapler & Staples", 22.50),
        ("Notebook Set", 15.00)
    ],
    filename="office_supplies_receipt.png",
    category="OFFICE_SUPPLIES"
)
receipts_created.append(("Office Depot", total1, "office_supplies_receipt.png"))

# 2. Meal Receipt
receipt2, total2 = create_receipt_image(
    vendor_name="The Business Lunch Cafe",
    amount=125.00,
    date=datetime.now().strftime("%Y-%m-%d"),
    items=[
        ("Grilled Salmon x2", 42.00),
        ("Caesar Salad x2", 24.00),
        ("Coffee x2", 8.00),
        ("Dessert", 16.00),
        ("Tip", 25.00)
    ],
    filename="business_lunch_receipt.png",
    category="MEALS"
)
receipts_created.append(("Business Lunch Cafe", total2, "business_lunch_receipt.png"))

# 3. Travel/Gas Receipt
receipt3, total3 = create_receipt_image(
    vendor_name="Shell Gas Station",
    amount=65.00,
    date=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
    items=[
        ("Premium Gasoline (15 gal)", 60.00),
        ("Car Wash", 12.00)
    ],
    filename="gas_station_receipt.png",
    category="TRAVEL"
)
receipts_created.append(("Shell Gas Station", total3, "gas_station_receipt.png"))

# 4. Hotel Receipt
receipt4, total4 = create_receipt_image(
    vendor_name="Marriott Hotel",
    amount=350.00,
    date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
    items=[
        ("Room (2 nights @ $150)", 300.00),
        ("Parking", 40.00),
        ("Resort Fee", 25.00)
    ],
    filename="hotel_receipt.png",
    category="TRAVEL"
)
receipts_created.append(("Marriott Hotel", total4, "hotel_receipt.png"))

# 5. Equipment/Software Receipt
receipt5, total5 = create_receipt_image(
    vendor_name="Best Buy",
    amount=450.00,
    date=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
    items=[
        ("Wireless Mouse", 45.00),
        ("Keyboard", 89.99),
        ("Monitor Stand", 65.00),
        ("USB Hub", 35.00),
        ("Cable Management Kit", 25.00),
        ("Extended Warranty", 75.00)
    ],
    filename="equipment_receipt.png",
    category="EQUIPMENT"
)
receipts_created.append(("Best Buy", total5, "equipment_receipt.png"))

# 6. Client Entertainment
receipt6, total6 = create_receipt_image(
    vendor_name="Premium Steakhouse",
    amount=280.00,
    date=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
    items=[
        ("Ribeye Steak x2", 95.00),
        ("Appetizers", 45.00),
        ("Wine (Bottle)", 85.00),
        ("Desserts x2", 28.00),
        ("Gratuity (20%)", 56.00)
    ],
    filename="client_dinner_receipt.png",
    category="ENTERTAINMENT"
)
receipts_created.append(("Premium Steakhouse", total6, "client_dinner_receipt.png"))

print("\n=== Summary ===")
print(f"Created {len(receipts_created)} sample receipts in '{SAMPLES_DIR}/' directory:\n")
for vendor, total, filename in receipts_created:
    print(f"  {filename:30s} - {vendor:25s} ${total:7.2f}")

print(f"\n✓ All samples saved to: {os.path.abspath(SAMPLES_DIR)}")
print("\nYou can now upload these receipts when creating expenses in the app!")
