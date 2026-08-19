"""
Generate realistic photo-style receipt images in both JPG and PNG formats
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
from datetime import datetime, timedelta
import random

# Create samples directory
SAMPLES_DIR = "sample_receipts"
os.makedirs(SAMPLES_DIR, exist_ok=True)

def add_paper_texture(img):
    """Add a subtle paper texture to make receipt look more realistic"""
    # Create a noise layer
    noise = Image.new('RGB', img.size)
    pixels = noise.load()

    for i in range(img.size[0]):
        for j in range(img.size[1]):
            # Random slight variation in brightness
            variation = random.randint(-5, 5)
            base = 250 + variation
            pixels[i, j] = (base, base, base)

    # Blend with original
    return Image.blend(img, noise, 0.1)

def add_slight_rotation(img):
    """Add a very slight rotation to simulate a scanned document"""
    angle = random.uniform(-1.5, 1.5)
    return img.rotate(angle, expand=True, fillcolor='white')

def create_realistic_receipt(
    vendor_name,
    amount,
    date,
    items,
    base_filename,
    category="OFFICE_SUPPLIES"
):
    """Create a realistic-looking receipt image that appears scanned/photographed"""

    # Create image (standard receipt size)
    width, height = 600, 900
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    # Try to use a monospace font for more authentic receipt look
    try:
        title_font = ImageFont.truetype("cour.ttf", 32)  # Courier
        header_font = ImageFont.truetype("cour.ttf", 24)
        body_font = ImageFont.truetype("cour.ttf", 20)
        small_font = ImageFont.truetype("cour.ttf", 16)
    except:
        try:
            title_font = ImageFont.truetype("arial.ttf", 32)
            header_font = ImageFont.truetype("arial.ttf", 24)
            body_font = ImageFont.truetype("arial.ttf", 20)
            small_font = ImageFont.truetype("arial.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

    y_position = 30

    # Draw vendor name (centered, bold)
    vendor_bbox = draw.textbbox((0, 0), vendor_name, font=title_font)
    vendor_width = vendor_bbox[2] - vendor_bbox[0]
    draw.text(((width - vendor_width) // 2, y_position), vendor_name,
              fill='black', font=title_font)
    y_position += 50

    # Draw address
    addr1 = "123 Business Street"
    addr1_bbox = draw.textbbox((0, 0), addr1, font=small_font)
    addr1_width = addr1_bbox[2] - addr1_bbox[0]
    draw.text(((width - addr1_width) // 2, y_position), addr1,
              fill='black', font=small_font)
    y_position += 25

    addr2 = "New York, NY 10001"
    addr2_bbox = draw.textbbox((0, 0), addr2, font=small_font)
    addr2_width = addr2_bbox[2] - addr2_bbox[0]
    draw.text(((width - addr2_width) // 2, y_position), addr2,
              fill='black', font=small_font)
    y_position += 25

    phone = "Tel: (555) 123-4567"
    phone_bbox = draw.textbbox((0, 0), phone, font=small_font)
    phone_width = phone_bbox[2] - phone_bbox[0]
    draw.text(((width - phone_width) // 2, y_position), phone,
              fill='black', font=small_font)
    y_position += 40

    # Draw separator
    draw.line([(30, y_position), (width-30, y_position)], fill='black', width=2)
    y_position += 30

    # Draw date and transaction info
    date_text = f"Date: {date}"
    draw.text((50, y_position), date_text, fill='black', font=body_font)
    y_position += 30

    receipt_num = f"Receipt #: {random.randint(10000, 99999)}"
    draw.text((50, y_position), receipt_num, fill='black', font=small_font)
    y_position += 40

    # Draw items
    subtotal = 0
    for item_name, item_price in items:
        # Item name on left
        draw.text((50, y_position), item_name, fill='black', font=body_font)

        # Price on right
        price_text = f"${item_price:.2f}"
        price_bbox = draw.textbbox((0, 0), price_text, font=body_font)
        price_width = price_bbox[2] - price_bbox[0]
        draw.text((width - 70 - price_width, y_position), price_text,
                  fill='black', font=body_font)

        y_position += 28
        subtotal += item_price

    y_position += 15
    draw.line([(30, y_position), (width-30, y_position)], fill='black', width=1)
    y_position += 25

    # Draw totals
    tax = subtotal * 0.08  # 8% tax
    total = subtotal + tax

    # Subtotal
    draw.text((70, y_position), "Subtotal:", fill='black', font=body_font)
    subtotal_text = f"${subtotal:.2f}"
    subtotal_bbox = draw.textbbox((0, 0), subtotal_text, font=body_font)
    subtotal_width = subtotal_bbox[2] - subtotal_bbox[0]
    draw.text((width - 70 - subtotal_width, y_position), subtotal_text,
              fill='black', font=body_font)
    y_position += 30

    # Tax
    draw.text((70, y_position), "Tax (8%):", fill='black', font=body_font)
    tax_text = f"${tax:.2f}"
    tax_bbox = draw.textbbox((0, 0), tax_text, font=body_font)
    tax_width = tax_bbox[2] - tax_bbox[0]
    draw.text((width - 70 - tax_width, y_position), tax_text,
              fill='black', font=body_font)
    y_position += 30

    # Draw bold separator
    draw.line([(30, y_position), (width-30, y_position)], fill='black', width=2)
    y_position += 25

    # Total (bold/larger)
    draw.text((70, y_position), "TOTAL:", fill='black', font=header_font)
    total_text = f"${total:.2f}"
    total_bbox = draw.textbbox((0, 0), total_text, font=header_font)
    total_width = total_bbox[2] - total_bbox[0]
    draw.text((width - 70 - total_width, y_position), total_text,
              fill='black', font=header_font)
    y_position += 50

    # Payment method
    payment = "VISA ****1234"
    draw.text((50, y_position), f"Payment: {payment}", fill='black', font=small_font)
    y_position += 40

    # Draw footer separator
    draw.line([(30, y_position), (width-30, y_position)], fill='black', width=1)
    y_position += 25

    # Thank you message
    thank_you = "Thank you for your business!"
    ty_bbox = draw.textbbox((0, 0), thank_you, font=small_font)
    ty_width = ty_bbox[2] - ty_bbox[0]
    draw.text(((width - ty_width) // 2, y_position), thank_you,
              fill='black', font=small_font)
    y_position += 25

    # Category hint
    cat_text = f"Category: {category}"
    cat_bbox = draw.textbbox((0, 0), cat_text, font=small_font)
    cat_width = cat_bbox[2] - cat_bbox[0]
    draw.text(((width - cat_width) // 2, y_position), cat_text,
              fill='gray', font=small_font)

    # Add paper texture
    img = add_paper_texture(img)

    # Add slight blur for realism (like scanning)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.3))

    # Add slight rotation
    img = add_slight_rotation(img)

    # Save as both PNG and JPG
    png_path = os.path.join(SAMPLES_DIR, f"{base_filename}.png")
    jpg_path = os.path.join(SAMPLES_DIR, f"{base_filename}.jpg")

    img.save(png_path, 'PNG', quality=95)
    img.save(jpg_path, 'JPEG', quality=90)

    print(f"Created: {base_filename}.png and {base_filename}.jpg (${total:.2f})")
    return png_path, jpg_path, total


# Generate realistic receipt samples
print("=== Generating Realistic Receipt Images ===\n")

receipts_created = []

# 1. Office Supplies
_, _, total1 = create_realistic_receipt(
    vendor_name="OFFICE DEPOT",
    amount=150.00,
    date=(datetime.now() - timedelta(days=5)).strftime("%m/%d/%Y"),
    items=[
        ("Printer Paper 5-ream", 45.00),
        ("Pens Box/50", 12.99),
        ("Folders 25-pack", 18.50),
        ("Desk Organizer", 35.99),
        ("Stapler+Staples", 22.50),
        ("Notebook Set", 15.00)
    ],
    base_filename="receipt_office_supplies",
    category="OFFICE_SUPPLIES"
)
receipts_created.append(("Office Supplies", total1))

# 2. Restaurant Meal
_, _, total2 = create_realistic_receipt(
    vendor_name="THE LUNCH SPOT",
    amount=125.00,
    date=datetime.now().strftime("%m/%d/%Y"),
    items=[
        ("Salmon Entree x2", 42.00),
        ("Caesar Salad x2", 24.00),
        ("Coffee x2", 8.00),
        ("Cheesecake", 16.00),
        ("Gratuity 20%", 25.00)
    ],
    base_filename="receipt_business_meal",
    category="MEALS"
)
receipts_created.append(("Business Meal", total2))

# 3. Gas Station
_, _, total3 = create_realistic_receipt(
    vendor_name="SHELL STATION #4521",
    amount=65.00,
    date=(datetime.now() - timedelta(days=2)).strftime("%m/%d/%Y"),
    items=[
        ("Premium Gas 15gal", 60.00),
        ("Car Wash Premium", 12.00)
    ],
    base_filename="receipt_gas",
    category="TRAVEL"
)
receipts_created.append(("Gas/Fuel", total3))

# 4. Hotel
_, _, total4 = create_realistic_receipt(
    vendor_name="MARRIOTT HOTEL",
    amount=350.00,
    date=(datetime.now() - timedelta(days=7)).strftime("%m/%d/%Y"),
    items=[
        ("Room 2-nights @150", 300.00),
        ("Parking Valet", 40.00),
        ("Resort Fee", 25.00)
    ],
    base_filename="receipt_hotel",
    category="TRAVEL"
)
receipts_created.append(("Hotel", total4))

# 5. Electronics
_, _, total5 = create_realistic_receipt(
    vendor_name="BEST BUY #1234",
    amount=450.00,
    date=(datetime.now() - timedelta(days=10)).strftime("%m/%d/%Y"),
    items=[
        ("Wireless Mouse", 45.00),
        ("Keyboard Mech", 89.99),
        ("Monitor Stand", 65.00),
        ("USB-C Hub", 35.00),
        ("Cable Kit", 25.00),
        ("Warranty 2yr", 75.00)
    ],
    base_filename="receipt_electronics",
    category="OTHER"
)
receipts_created.append(("Electronics", total5))

# 6. Restaurant Dinner
_, _, total6 = create_realistic_receipt(
    vendor_name="STEAKHOUSE PRIME",
    amount=280.00,
    date=(datetime.now() - timedelta(days=3)).strftime("%m/%d/%Y"),
    items=[
        ("Ribeye Steak x2", 95.00),
        ("Appetizer Platter", 45.00),
        ("Wine Bottle", 85.00),
        ("Dessert x2", 28.00),
        ("Gratuity 20%", 56.00)
    ],
    base_filename="receipt_client_dinner",
    category="MEALS"
)
receipts_created.append(("Client Dinner", total6))

# 7. Coffee Shop
_, _, total7 = create_realistic_receipt(
    vendor_name="STARBUCKS #5678",
    amount=25.00,
    date=datetime.now().strftime("%m/%d/%Y"),
    items=[
        ("Latte Grande x2", 10.00),
        ("Cappuccino", 5.50),
        ("Muffin x2", 8.00),
        ("Tip", 1.50)
    ],
    base_filename="receipt_coffee",
    category="MEALS"
)
receipts_created.append(("Coffee", total7))

# 8. Parking
_, _, total8 = create_realistic_receipt(
    vendor_name="CITY PARKING LOT",
    amount=45.00,
    date=(datetime.now() - timedelta(days=1)).strftime("%m/%d/%Y"),
    items=[
        ("Parking 8 hours", 40.00),
        ("Processing Fee", 5.00)
    ],
    base_filename="receipt_parking",
    category="TRAVEL"
)
receipts_created.append(("Parking", total8))

# 9. Taxi/Uber
_, _, total9 = create_realistic_receipt(
    vendor_name="UBER TRIP",
    amount=55.00,
    date=(datetime.now() - timedelta(days=4)).strftime("%m/%d/%Y"),
    items=[
        ("Trip to Airport", 45.00),
        ("Tip", 10.00)
    ],
    base_filename="receipt_uber",
    category="TRAVEL"
)
receipts_created.append(("Uber/Taxi", total9))

# 10. Software Subscription
_, _, total10 = create_realistic_receipt(
    vendor_name="ADOBE CREATIVE",
    amount=52.99,
    date=(datetime.now() - timedelta(days=15)).strftime("%m/%d/%Y"),
    items=[
        ("Monthly Subscription", 49.99),
        ("Tax", 3.00)
    ],
    base_filename="receipt_software",
    category="SOFTWARE"
)
receipts_created.append(("Software", total10))

print("\n=== Summary ===")
print(f"Created {len(receipts_created)} realistic receipt sets (PNG + JPG):\n")
for category, total in receipts_created:
    print(f"  {category:20s} ${total:7.2f}")

total_amount = sum(total for _, total in receipts_created)
print(f"\n  {'TOTAL':20s} ${total_amount:7.2f}")
print(f"\nAll receipts saved to: {os.path.abspath(SAMPLES_DIR)}")
print(f"Each receipt available in both PNG and JPG formats")
print(f"Total files created: {len(receipts_created) * 2} ({len(receipts_created)} PNG + {len(receipts_created)} JPG)")
