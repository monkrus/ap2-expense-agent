# Google Cloud Marketplace Asset Creation Guide

**Priority**: CRITICAL (BLOCKER)
**Estimated Time**: 10-15 hours
**Deadline**: Must complete before GCP Marketplace submission

---

## Overview

This guide provides step-by-step instructions for creating all required assets for Google Cloud Marketplace listing.

**Required Assets**:
1. 8 Screenshots (1280x800px)
2. Demo Video (2-3 minutes)
3. Product Icon (512x512px)
4. Domain & Support Email
5. Documentation Site

---

## Part 1: Screenshots (Days 1-2, ~6 hours)

### Requirements
- **Count**: 8 screenshots (minimum 3, recommended 8)
- **Resolution**: 1280 x 800 pixels (exact)
- **Format**: PNG or JPG
- **File Size**: < 5MB each
- **Content**: No PII, watermarks, or competitor mentions

### Setup: Prepare Demo Environment

**Step 1**: Create Sample Data

```bash
# Start backend server
cd backend
.venv/Scripts/python.exe -m uvicorn src.api:app --reload

# In another terminal, seed sample data
cd backend
python seed_sample_data.py
```

**Step 2**: Create Test User & Organization

```python
# Use these credentials for screenshots
Company: "Acme Corporation"
Admin User: "sarah.admin@acme.com"
Employees:
  - "john.employee@acme.com" (Employee)
  - "mike.manager@acme.com" (Manager)
```

**Sample Expenses** (populate for screenshots):
```json
[
  {"vendor": "Office Depot", "amount": 45.99, "category": "Office Supplies", "date": "2025-11-15"},
  {"vendor": "Delta Airlines", "amount": 542.50, "category": "Travel", "date": "2025-11-18"},
  {"vendor": "Hilton Hotels", "amount": 289.00, "category": "Lodging", "date": "2025-11-19"},
  {"vendor": "Starbucks", "amount": 12.75, "category": "Meals", "date": "2025-11-20"},
  {"vendor": "Uber", "amount": 35.20, "category": "Transportation", "date": "2025-11-21"},
  {"vendor": "AWS", "amount": 1250.00, "category": "Cloud Services", "date": "2025-11-22"}
]
```

### Screenshot Checklist

#### Screenshot 1: Dashboard Overview ✅
**Filename**: `screenshot-01-dashboard.png`

**What to Show**:
- Clean, populated dashboard with admin view
- Recent expenses list (5-6 items)
- Budget widgets showing usage
- Pending approval queue (2-3 items)
- Statistics cards (Total Expenses, Pending, Approved, Rejected)

**How to Capture**:
1. Login as `sarah.admin@acme.com`
2. Navigate to main dashboard
3. Ensure browser window is 1280px wide
4. Use browser DevTools: F12 → Toggle Device Toolbar → Responsive → 1280x800
5. Take screenshot: Windows Snipping Tool or `Win + Shift + S`

**Tips**:
- Show realistic but anonymized data
- Highlight key metrics in view
- Ensure all UI elements are visible

---

#### Screenshot 2: Submit Expense ✅
**Filename**: `screenshot-02-submit-expense.png`

**What to Show**:
- Expense submission form (filled out)
- Receipt upload area with sample receipt visible
- AI categorization suggestion badge
- Category dropdown expanded
- Date picker visible
- Amount field with currency

**How to Capture**:
1. Click "Submit Expense" button
2. Fill form with:
   - Vendor: "Amazon Web Services"
   - Amount: $1,250.00
   - Category: "Cloud Services" (show AI suggestion)
   - Description: "Monthly cloud hosting and compute resources"
3. Upload a sample invoice/receipt PDF
4. Show AI categorization working (add visual indicator)
5. Capture at 1280x800px

---

#### Screenshot 3: Expense List & Filtering ✅
**Filename**: `screenshot-03-expense-list.png`

**What to Show**:
- Table of 8-10 expenses
- Filter dropdowns visible (Status: All, Category: All, Date Range)
- Search bar with example search term
- Bulk select checkboxes (2-3 selected)
- Export button highlighted
- Pagination showing "Page 1 of 3"
- Sort indicators on column headers

**How to Capture**:
1. Navigate to Expenses page
2. Apply filter: Status = "Pending"
3. Check 2-3 expenses
4. Show export dropdown menu open
5. Capture full table view

---

#### Screenshot 4: Approval Workflow ✅
**Filename**: `screenshot-04-approval-workflow.png`

**What to Show**:
- Pending approvals queue (manager view)
- Expense details modal/panel open
- Receipt preview visible
- Approve/Reject buttons prominent
- Comments section with 1-2 comments
- Approval history timeline (2-3 steps)
- Amount, category, submitter info

**How to Capture**:
1. Login as manager (`mike.manager@acme.com`)
2. Click on pending expense to open details
3. Show receipt image preview
4. Add a comment: "Please provide itemized receipt"
5. Show approval buttons ready to click
6. Capture modal/panel view

---

#### Screenshot 5: AP2 Payment Flow ✅
**Filename**: `screenshot-05-ap2-protocol.png`

**What to Show**:
- Three-mandate flow visualization:
  1. Intent Mandate (created ✓)
  2. Cart Mandate (pending)
  3. Payment Mandate (not started)
- Cryptographic signature indicators
- Mandate status badges (green checkmark, yellow pending)
- Transaction ID visible
- Payment execution confirmation dialog
- Vendor info, amount, constraints

**How to Capture**:
1. Navigate to AP2 Mandates page
2. Click on active mandate to show flow
3. Show mandate details with signature
4. Highlight cryptographic verification badge
5. Capture flow diagram + details panel

---

#### Screenshot 6: Analytics & Reporting ✅
**Filename**: `screenshot-06-analytics.png`

**What to Show**:
- Dashboard with 3-4 charts:
  - Spending by category (pie chart)
  - Monthly trend (line chart)
  - Top vendors (bar chart)
  - Department breakdown (stacked bar)
- Budget vs actual comparison widget
- Export options visible (CSV, PDF, Excel buttons)
- Date range selector showing "Last 30 Days"
- Key metrics summary cards

**How to Capture**:
1. Navigate to Analytics/Reports page
2. Select date range: Last 30 Days
3. Ensure all charts have data
4. Show export menu open
5. Capture full dashboard view

---

#### Screenshot 7: Organization Management ✅
**Filename**: `screenshot-07-organization.png`

**What to Show**:
- Organization settings panel
- Team members list (5-6 members)
- Role badges (Owner, Admin, Manager, Employee)
- Invite new member button
- Subscription tier badge (e.g., "Professional Plan")
- Member permissions table
- Pending invitations section (1-2 pending)

**How to Capture**:
1. Login as org owner
2. Navigate to Organization Settings
3. Click "Members" tab
4. Show member list with roles
5. Show tier badge in header
6. Capture full settings view

---

#### Screenshot 8: Mobile Responsive ✅
**Filename**: `screenshot-08-mobile.png`

**What to Show**:
- Mobile view of expense submission (375x667)
- Mobile-optimized navigation (hamburger menu)
- Receipt camera capture icon
- Touch-friendly buttons
- Responsive layout stacking

**How to Capture**:
1. Chrome DevTools → Toggle Device Toolbar
2. Select "iPhone 12 Pro" (390x844) or custom 375x667
3. Navigate to Submit Expense page
4. Show hamburger menu open
5. Capture mobile view (resize to 1280x800 for submission)

**Note**: Resize mobile screenshot to 1280x800 in image editor (add white/gray borders)

---

### Screenshot Preparation Best Practices

**Do**:
✅ Use consistent light mode theme
✅ Populate with realistic sample data
✅ Show professional company name (Acme Corporation)
✅ Use clean, uncluttered UI
✅ Highlight key features
✅ Use high-contrast, readable text
✅ Show loaded/success states (not loading spinners)

**Don't**:
❌ Include real personal information
❌ Use company logos without permission
❌ Mention competitors
❌ Show error states or broken UI
❌ Use "Lorem ipsum" placeholder text
❌ Show empty states (populate with data)

---

### Image Editing & Export

**Tools**:
- **Free**: GIMP, Paint.NET, Photopea (web-based)
- **Paid**: Photoshop, Sketch, Figma

**Steps**:
1. Capture screenshot at 1280x800px
2. Open in image editor
3. Crop/resize to exact 1280x800px
4. Add subtle annotations if needed (arrows, highlights)
5. Export as PNG (recommended) or JPG
6. Verify file size < 5MB
7. Check resolution: Right-click → Properties → Details

**Naming Convention**:
```
screenshot-01-dashboard.png
screenshot-02-submit-expense.png
screenshot-03-expense-list.png
screenshot-04-approval-workflow.png
screenshot-05-ap2-protocol.png
screenshot-06-analytics.png
screenshot-07-organization.png
screenshot-08-mobile.png
```

---

## Part 2: Demo Video (Days 3-4, ~6 hours)

### Requirements
- **Length**: 2-3 minutes (max 5 minutes)
- **Resolution**: 1280 x 720 (720p minimum, 1920x1080 preferred)
- **Format**: MP4 (H.264 codec)
- **File Size**: < 100MB
- **Platform**: YouTube (unlisted or public)
- **Captions**: English subtitles (required)

### Video Script (2:30 duration)

**[0:00-0:15] Introduction**
```
Visual: Title card with AP2 Expense Agent logo
Voiceover: "Introducing AP2 Expense Agent - the first AI-native expense
           management system built on Google's Agent Payments Protocol."
Transition: Fade to problem statement
```

**[0:15-0:45] Problem Statement**
```
Visual: Split screen showing pain points:
  - Left: Paper receipts scattered on desk
  - Center: Employee frustrated with spreadsheet
  - Right: Manager drowning in email approvals

Voiceover: "Traditional expense management is slow, manual, and error-prone.
           Employees waste hours on paperwork. Managers struggle with approvals.
           Finance teams lack real-time visibility."

Transition: Wipe to solution
```

**[0:45-1:15] Key Features (Rapid Demo)**
```
Visual: Quick feature montage (6 seconds each)
1. Submit expense in 30 seconds (form → receipt → submit)
2. AI receipt scanning (upload → auto-extract → categorize)
3. Smart categorization (AI badge animation)
4. One-click approval (manager view → approve button)
5. Real-time dashboards (charts animating)

Voiceover: "AP2 Expense Agent automates the entire process with
           AI-powered intelligence. Submit expenses in seconds.
           Our AI scans receipts and categorizes automatically.
           Managers approve with one click. Real-time insights
           keep everyone aligned."

Transition: Zoom to AP2 protocol section
```

**[1:15-1:45] AP2 Protocol Advantage**
```
Visual: Three-mandate flow animation
  - Intent → Cart → Payment (checkmarks appearing)
  - Cryptographic signature badge glowing
  - Audit trail scrolling (hash values visible)

Voiceover: "Our unique AP2 protocol provides cryptographic proof for
           every transaction. This three-step verification eliminates
           payment disputes and ensures ironclad compliance.
           Every action is recorded in a tamper-proof audit trail."

Transition: Fade to results
```

**[1:45-2:10] Results & Social Proof**
```
Visual: Statistics appearing with animations:
  - "80% Faster Processing" (speedometer)
  - "95% AI Accuracy" (target with bullseye)
  - "$12K Average Annual Savings" (money icon)
  - Customer testimonials (text quotes sliding in)

Voiceover: "Join hundreds of companies saving time and money.
           Our customers see 80% faster expense processing,
           95% AI accuracy, and average savings of $12,000 annually.
           But don't just take our word for it..."

Testimonial Text on Screen:
  "AP2 cut our expense processing time from days to hours." - CFO, TechCorp
  "The AI categorization is incredibly accurate." - Finance Manager, StartupXYZ
```

**[2:10-2:30] Call to Action**
```
Visual:
  - Pricing tiers side-by-side (3 columns)
  - "Deploy in 5 minutes" badge
  - GCP Marketplace logo
  - End card: Logo + URL + "14-day free trial"

Voiceover: "Get started today on Google Cloud Marketplace.
           Choose from flexible pricing plans.  Deploy in just
           5 minutes. Start your 14-day free trial - no credit
           card required. Visit ap2expense.com to learn more."

End Card:
  AP2 Expense Agent logo
  "Available on Google Cloud Marketplace"
  "14-Day Free Trial | No Credit Card Required"
  "ap2expense.com"
```

---

### Video Production Tools

**Screen Recording** (Free):
- OBS Studio (best, most features)
- Loom (quick & easy)
- Windows Game Bar (`Win + G`)

**Screen Recording** (Paid):
- Camtasia ($299, easy editing)
- ScreenFlow (Mac, $169)

**Video Editing** (Free):
- DaVinci Resolve (professional-grade)
- OpenShot
- Shotcut

**Video Editing** (Paid):
- Adobe Premiere Pro ($20/mo)
- Final Cut Pro (Mac, $299)

**Voiceover**:
- Natural voice (record with good mic)
- AI voice: ElevenLabs ($5/mo), Descript ($12/mo)
- Hire on Fiverr ($20-50)

**Music** (Royalty-Free):
- YouTube Audio Library (free)
- Epidemic Sound ($15/mo)
- Artlist ($16/mo)

---

### Video Production Steps

**Day 3: Script & Recording**

1. **Finalize Script** (1 hour)
   - Review script above
   - Adjust timing to 2:30
   - Create shot list

2. **Record Screen Footage** (2 hours)
   - Set up demo environment
   - Record each scene separately
   - Multiple takes for perfection
   - Record at 1920x1080 (will export to 1280x720)

3. **Record Voiceover** (1 hour)
   - Use good microphone
   - Quiet environment
   - Read script naturally
   - Record in 30-second chunks

**Day 4: Editing & Export**

4. **Video Editing** (3 hours)
   - Import footage into editor
   - Arrange clips according to script
   - Trim and cut for pacing
   - Add transitions (fade, wipe)
   - Sync voiceover to video
   - Add background music (low volume, 10-15%)
   - Add on-screen text for key points
   - Add end card (5 seconds)

5. **Add Captions** (1 hour)
   - Use YouTube auto-captions
   - OR use Descript for automatic transcription
   - Review and fix errors
   - Export SRT file

6. **Export & Upload** (30 minutes)
   - Export: 1280x720 MP4, H.264, 30fps
   - Target bitrate: 5-8 Mbps
   - Verify file size < 100MB
   - Upload to YouTube (unlisted)
   - Add title: "AP2 Expense Agent - AI-Powered Expense Management"
   - Add description with keywords
   - Upload SRT caption file
   - Test playback

---

## Part 3: Product Icon (Day 5, ~2 hours)

### Requirements
- **Resolution**: 512 x 512 pixels
- **Format**: PNG with transparent background
- **File Size**: < 1MB
- **Design**: Simple, recognizable, no text

### Design Options

**Option 1: Professional Designer**
- **Platform**: Fiverr, 99designs
- **Cost**: $50-200
- **Time**: 2-3 days
- **Brief**: "Create a simple, modern icon for expense management software"

**Option 2: DIY Design**

**Tools**:
- Figma (free, web-based)
- Canva Pro ($13/mo)
- Adobe Illustrator ($20/mo)

**Design Elements**:
- Color scheme: Blue (#4F46E5) + Green (#10B981) [from branding]
- Icon concept ideas:
  1. Receipt with checkmark
  2. Dollar sign with shield (security)
  3. Wallet with AI chip symbol
  4. Cloud with expense graph
  5. Stylized "AP2" monogram

**DIY Steps**:
1. Open Figma or Canva
2. Create 512x512px artboard
3. Design simple icon (minimal detail)
4. Use 2-3 colors max
5. Ensure recognizable at small sizes (128px, 64px)
6. Export as PNG with transparency
7. Test at various sizes

---

## Part 4: Domain & Support Email (Day 5, ~2 hours)

### Domain Registration

**Recommended Domain**: `ap2expense.com`

**Registrars**:
- Google Domains (now Squarespace, $12/year)
- Namecheap ($10/year)
- GoDaddy ($12/year)

**Steps**:
1. Check availability: https://domains.google.com/registrar/search?searchTerm=ap2expense.com
2. Purchase domain ($10-15/year)
3. Configure DNS:
   - A record: → your Cloud Run IP
   - CNAME: docs → docs.ap2expense.com
   - CNAME: api → api.ap2expense.com
4. Set up SSL certificate (auto with Cloud Run)

---

### Support Email Configuration

**Option 1: Google Workspace** (Recommended)
- Cost: $6/user/month
- Professional email: support@ap2expense.com
- Includes Gmail, Calendar, Drive

**Steps**:
1. Sign up: https://workspace.google.com
2. Verify domain ownership
3. Create user: support@ap2expense.com
4. Set up email forwarding to team inbox

**Option 2: Email Forwarding** (Free)
- Use registrar's email forwarding
- Forward support@ap2expense.com → your Gmail
- Reply-to address: support@ap2expense.com

---

## Part 5: Documentation Site (Day 5, ~3 hours)

### Quick Deploy with GitHub Pages

**Option 1: MkDocs** (Recommended)

**Setup**:
```bash
# Install MkDocs
pip install mkdocs mkdocs-material

# Create docs site
mkdir docs-site
cd docs-site
mkdocs new .

# Configure
Edit mkdocs.yml:
  site_name: AP2 Expense Agent Documentation
  site_url: https://docs.ap2expense.com
  theme:
    name: material
    palette:
      primary: indigo
```

**Content Structure**:
```
docs/
├── index.md (Getting Started)
├── quickstart.md
├── user-guide.md (copy from docs/USER_GETTING_STARTED.md)
├── admin-guide.md (copy from docs/ADMIN_CUSTOMIZATION_GUIDE.md)
├── api-reference.md (link to /api/docs)
├── troubleshooting.md (copy from docs/TROUBLESHOOTING.md)
└── faq.md
```

**Deploy**:
```bash
# Build site
mkdocs build

# Deploy to GitHub Pages
mkdocs gh-deploy

# Configure custom domain
# In GitHub repo settings → Pages → Custom domain → docs.ap2expense.com
```

**Alternative**: Use existing docs from `/docs` folder, deploy to Netlify (free, 5 minutes).

---

## Checklist: Final Verification

Before submitting to GCP Partner Portal:

- [ ] All 8 screenshots created (1280x800px, <5MB each)
- [ ] Screenshots named correctly (screenshot-01 through screenshot-08)
- [ ] Demo video recorded and uploaded to YouTube
- [ ] Video is 2-3 minutes, 720p+, with captions
- [ ] Product icon created (512x512px PNG)
- [ ] Icon tested at multiple sizes (512, 256, 128, 64px)
- [ ] Domain `ap2expense.com` registered and DNS configured
- [ ] Support email `support@ap2expense.com` configured
- [ ] Documentation site deployed at docs.ap2expense.com
- [ ] All links working (docs, support, pricing, ToS, Privacy)
- [ ] Screenshots reviewed for PII/sensitive data (none present)
- [ ] Video reviewed for quality and accuracy
- [ ] Team approval obtained for all marketing materials

---

## Timeline Summary

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1 | Screenshots 1-4 | 3h | 4 screenshots |
| 2 | Screenshots 5-8 | 3h | 4 screenshots |
| 3 | Video script & recording | 4h | Raw footage + voiceover |
| 4 | Video editing & upload | 4h | Final video on YouTube |
| 5 | Icon, domain, docs | 4h | Icon + domain + docs site |

**Total**: 18 hours (add buffer for revisions)

---

## Resources

**Sample Expenses**: Use `backend/seed_sample_data.py`
**Existing Screenshots**: Check `marketplace/screenshots/` (if any)
**Branding**: Colors from Tailwind config (`frontend/tailwind.config.js`)
**Support**: GCP Marketplace Partner Support (marketplace-support@google.com)

---

## Next Steps

After completing all assets:
1. Create Google Partner Portal account
2. Upload all assets to Partner Portal
3. Fill out product listing form
4. Submit for GCP review (expect 1-2 weeks)
5. Address any feedback from GCP
6. Schedule launch date

**Questions?** Contact GCP Marketplace support or internal team lead.

---

*Last Updated: December 4, 2025*
