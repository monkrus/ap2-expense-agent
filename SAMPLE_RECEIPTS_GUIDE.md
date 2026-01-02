# Sample Receipts - Quick Start Guide

## ✅ What Was Created

I've generated **6 sample receipt images** with realistic formatting for testing the expense receipt upload functionality.

### Sample Receipts Available

| Receipt File | Vendor | Amount | Category | Description |
|--------------|--------|--------|----------|-------------|
| `office_supplies_receipt.png` | Office Depot | $161.98 | Office Supplies | Printer paper, pens, folders, organizer |
| `business_lunch_receipt.png` | Business Lunch Cafe | $124.20 | Meals | Client lunch meeting |
| `gas_station_receipt.png` | Shell Gas Station | $77.76 | Travel | Gas for client visit |
| `hotel_receipt.png` | Marriott Hotel | $394.20 | Travel | Conference accommodation (2 nights) |
| `equipment_receipt.png` | Best Buy | $361.79 | Other | Computer accessories |
| `client_dinner_receipt.png` | Premium Steakhouse | $333.72 | Meals | Client entertainment |

**Total Sample Expenses**: $1,453.65

---

## 📁 File Locations

```
ap2-expense-agent/
├── sample_receipts/           # Receipt images
│   ├── office_supplies_receipt.png
│   ├── business_lunch_receipt.png
│   ├── gas_station_receipt.png
│   ├── hotel_receipt.png
│   ├── equipment_receipt.png
│   ├── client_dinner_receipt.png
│   └── README.md              # Detailed usage instructions
│
├── generate_sample_receipts.py    # Script to regenerate receipts
└── test_receipt_upload.py          # Script to upload receipts via API
```

---

## 🚀 How to Use

### Option 1: Manual Upload (via Web UI)

1. **Login** to the app at http://localhost:5173
   - Use: `employee1` / `TestPass123!`

2. **Navigate** to "My Expenses" or "Submit Expense"

3. **Create an Expense**
   - Fill in vendor, amount, category, description
   - Click "Upload Receipt" or "Attach File"

4. **Select** one of the sample receipt images from `sample_receipts/` folder

5. **Submit** the expense

### Option 2: Automated Upload (via Script)

```bash
# Make sure backend is running
cd backend && .venv/Scripts/python.exe -m uvicorn src.api:app --reload

# Run the upload script (in a new terminal)
python test_receipt_upload.py
```

This will:
- Create 6 expenses with realistic data
- Upload the corresponding receipt images
- Display success/failure status

### Option 3: Regenerate Receipts

If you want to create new sample receipts:

```bash
python generate_sample_receipts.py
```

This creates fresh receipt images with:
- Current/recent dates
- Realistic vendor names
- Proper formatting (header, items, totals, tax)
- Clear text for OCR processing

---

## ✨ Receipt Features

Each receipt image includes:

✓ **Vendor Name** - Clear header text
✓ **Business Address** - Realistic address format
✓ **Contact Info** - Phone number
✓ **Transaction Date** - Recent dates (within last 10 days)
✓ **Itemized List** - Individual items with prices
✓ **Subtotal** - Pre-tax amount
✓ **Tax** - 8% sales tax calculation
✓ **Total** - Final amount (matches expense amount)
✓ **Category Hint** - Suggested category at bottom

**Format**: 800x1200px PNG images (standard receipt size)

---

## 🧪 Testing Scenarios

### 1. Basic Upload Test
- Create expense manually
- Upload receipt image
- Verify receipt appears in expense details

### 2. OCR Extraction Test
- Upload receipt with OCR enabled
- Check if vendor, amount, date are extracted
- Verify accuracy of extracted data

### 3. Multi-Receipt Test
- Create one expense
- Upload multiple receipt images
- Verify all receipts are linked to expense

### 4. Tier Limit Test
Test OCR scan limits:
- **Free**: 30 OCR scans/month
- **Starter**: 50 OCR scans/month
- **Professional**: 200 OCR scans/month

### 5. Approval Workflow Test
- Employee uploads expense with receipt
- Admin reviews receipt before approving
- Verify receipt is visible during approval

---

## 📊 Sample Data Created

When you run `test_receipt_upload.py`, it creates:

| Expense # | Vendor | Status | Amount | Date | Receipt |
|-----------|--------|--------|--------|------|---------|
| 1 | Office Depot | PENDING | $161.98 | 2026-01-01 | ✓ |
| 2 | Business Lunch Cafe | PENDING | $124.20 | 2026-01-01 | ✓ |
| 3 | Shell Gas Station | PENDING | $77.76 | 2025-12-30 | ✓ |
| 4 | Marriott Hotel | PENDING | $394.20 | 2025-12-25 | ✓ |
| 5 | Best Buy | PENDING | $361.79 | 2025-12-22 | ✓ |
| 6 | Premium Steakhouse | PENDING | $333.72 | 2025-12-29 | ✓ |

All expenses are created as PENDING and ready for admin approval.

---

## 🔍 Viewing Uploaded Receipts

### As Employee:
1. Login: `employee1` / `TestPass123!`
2. Go to "My Expenses" tab
3. Click on any expense
4. See "Receipts" section with attached images
5. Click to download/view receipt

### As Admin:
1. Login: `adminfree` / `password123`
2. Go to "Pending Approvals" tab
3. Click on expense to review
4. View attached receipts before approving/rejecting

---

## 🛠️ Troubleshooting

### Receipt Upload Fails

**Check:**
- File size < 10MB
- File format is PNG, JPG, or PDF
- User is logged in and has valid session
- Organization ID is set correctly

### OCR Not Working

**Possible causes:**
- OCR service not configured
- Tier limit exceeded (check usage)
- Image quality too low
- Backend OCR service not running

### Receipts Not Showing

**Try:**
- Refresh the page (Ctrl+Shift+R)
- Check browser console for errors
- Verify backend is running
- Check file was actually uploaded (check backend logs)

---

## 📝 Valid Expense Categories

When creating expenses, use these categories:

- `TRAVEL` - Transportation, gas, parking, hotels
- `MEALS` - Business meals, client lunches, food
- `SOFTWARE` - Software licenses, subscriptions, tools
- `OFFICE_SUPPLIES` - Office equipment, supplies, furniture
- `OTHER` - Everything else (equipment, entertainment, etc.)

---

## 🎯 Next Steps

1. **Test the uploads** using the web UI or script
2. **Review receipts** as admin before approving expenses
3. **Check OCR extraction** if enabled
4. **Test tier limits** by uploading 30+ receipts on Free tier
5. **Create custom receipts** by modifying `generate_sample_receipts.py`

---

## 📧 Support

For issues or questions:
- Check `sample_receipts/README.md` for detailed documentation
- Review backend logs for upload errors
- Use Chrome DevTools to inspect network requests
- Check database for uploaded receipt records

**Sample receipts are ready to use! Start testing the receipt upload feature now.** 🚀
