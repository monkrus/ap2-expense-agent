# AP2 Expense Agent - Demo Video Script

**Duration**: 3 minutes
**Format**: Screen recording with voiceover
**Resolution**: 1920x1080 (Full HD)
**FPS**: 30fps minimum

---

## Video Structure

### Opening Scene (0:00 - 0:15)
**Visual**: Show product logo and name
**Narration**:
> "Introducing AP2 Expense Agent - the AI-powered expense management platform built for the modern workplace. Let's see how it transforms expense tracking from a tedious task into a seamless experience."

### Scene 1: Employee Experience - Submitting an Expense (0:15 - 0:45)
**Visual**: Login as john.employee@acme.com, navigate to "Create Expense"
**Actions**:
1. Click "New Expense" button
2. Fill in form:
   - Vendor: "Starbucks"
   - Amount: $12.75
   - Category: "Meals" (auto-suggested)
   - Description: "Client meeting coffee"
3. Upload receipt (drag and drop a sample receipt image)
4. Show AI categorization working (badge appears: "AI Categorized")
5. Click "Submit"

**Narration**:
> "Employees can submit expenses in seconds. Simply enter the vendor, amount, and upload a receipt. Our AI automatically categorizes the expense and extracts key information from the receipt. One click and it's submitted for approval."

### Scene 2: AI-Powered Receipt Scanning (0:45 - 1:05)
**Visual**: Focus on receipt upload with AI features
**Actions**:
1. Show receipt being uploaded
2. Highlight AI extracted data appearing in form fields
3. Show confidence score indicator
4. Demonstrate category suggestion

**Narration**:
> "The AI-powered OCR scanner automatically reads receipts, extracting vendor names, amounts, and dates. It even suggests the right expense category based on purchase history and patterns."

### Scene 3: Manager Approval Workflow (1:05 - 1:30)
**Visual**: Logout, login as mike.manager@acme.com
**Actions**:
1. Navigate to "Approvals" page
2. Show list of pending expenses (should have 2-3 from demo data)
3. Click on expense to view details
4. Show receipt preview
5. Click "Approve" button
6. Show bulk approve checkbox
7. Select multiple expenses
8. Click "Approve Selected" (2 expenses)

**Narration**:
> "Managers can review and approve expenses with a single click. View receipt images, check against budgets, and approve multiple expenses at once. The approval workflow is fast, transparent, and trackable."

### Scene 4: Budget Tracking & Analytics (1:30 - 1:50)
**Visual**: Navigate to "Reports" page
**Actions**:
1. Show budget overview cards
   - Travel: $1,166/$5,000 (23% used)
   - Software: $349/$3,000 (12% used)
   - Office Supplies: $46/$500 (9% used)
2. Display spending by category pie chart
3. Show monthly trend line chart
4. Highlight export button (PDF/Excel)

**Narration**:
> "Track spending against budgets in real-time. Beautiful dashboards show spending trends, category breakdowns, and budget utilization. Export reports for accounting with one click."

### Scene 5: Organization Management (1:50 - 2:10)
**Visual**: Login as sarah.admin@acme.com, navigate to "Organizations"
**Actions**:
1. Show organization overview
   - Acme Corporation
   - 3 members
   - Professional tier
2. Click "Settings"
3. Show approval policies configuration
4. Demonstrate member management
5. Show tier upgrade option

**Narration**:
> "Admins have complete control. Manage organization members, configure approval workflows, and set spending policies. Multi-tenant architecture supports multiple organizations with isolated data."

### Scene 6: AP2 Payment Verification (2:10 - 2:30)
**Visual**: Show expense with AP2 mandate
**Actions**:
1. Navigate to expense with "Paid via AP2" badge
2. Click to view payment details
3. Show cryptographic signature
4. Display mandate verification status
5. Highlight tamper-proof audit trail

**Narration**:
> "AP2 protocol integration provides cryptographically verified payments. Every transaction is signed and verified, creating an immutable audit trail. Say goodbye to payment disputes and fraud."

### Scene 7: Mobile Experience (2:30 - 2:45)
**Visual**: Switch to mobile device simulator (iPhone)
**Actions**:
1. Show mobile dashboard
2. Submit expense on mobile
3. Snap receipt photo with camera
4. Quick approval on mobile

**Narration**:
> "Fully responsive design works perfectly on mobile devices. Submit expenses on the go, snap receipt photos, and approve from anywhere."

### Closing Scene (2:45 - 3:00)
**Visual**: Return to dashboard overview, show key features list
**Actions**:
1. Fade through key screens
2. Display feature highlights:
   - ✓ AI-Powered Receipt Scanning
   - ✓ One-Click Approvals
   - ✓ Real-Time Budget Tracking
   - ✓ Cryptographic Payment Verification
   - ✓ Multi-Tenant Organizations
   - ✓ Mobile Responsive
3. Show "Start Free Trial" button
4. Display company logo and marketplace link

**Narration**:
> "AP2 Expense Agent - modern expense management for modern teams. Start your free 14-day trial on Google Cloud Marketplace today. No credit card required."

---

## Recording Setup

### Software
**Recommended**:
- **Screen Recording**: OBS Studio (free, open source)
- **Video Editing**: DaVinci Resolve (free) or Adobe Premiere Pro
- **Voiceover**: Audacity (free) or Adobe Audition

**Settings**:
- Resolution: 1920x1080
- Frame rate: 30fps
- Audio: 48kHz, stereo

### Browser Setup
1. Use Chrome in Incognito mode (clean, no extensions)
2. Set zoom to 100%
3. Hide bookmarks bar
4. Use clean desktop background
5. Close unnecessary applications

### Preparation Checklist
- [ ] Demo data seeded (`python backend/seed_screenshot_data.py`)
- [ ] Backend running (`cd backend && uvicorn src.api:app --reload`)
- [ ] Frontend running (`cd frontend && npm run dev`)
- [ ] Test all user logins work
- [ ] Prepare sample receipt images (5-6 high-quality receipts)
- [ ] Practice narration script
- [ ] Test screen recording software
- [ ] Check audio levels

---

## Recording Tips

### Visual
1. **Smooth Movements**: Move cursor slowly and deliberately
2. **Pauses**: Pause 2 seconds after each click to let viewers see result
3. **Highlight Key Elements**: Use cursor to point at important features
4. **Clean UI**: Hide dev tools, close extra tabs
5. **Loading States**: If something loads, wait for it to complete

### Audio
1. **Clear Voice**: Speak clearly and at moderate pace
2. **Enthusiasm**: Sound excited but professional
3. **No Ums/Ahs**: Practice until smooth
4. **Background Noise**: Record in quiet environment
5. **Consistent Volume**: Normalize audio in post-production

### Pacing
- Total video: 2:45 - 3:00 (strict)
- Each scene: 20-30 seconds max
- Quick transitions (0.5-1 second fades)
- Don't rush, but stay focused

---

## Post-Production

### Editing
1. **Trim Dead Space**: Remove any pauses or mistakes
2. **Add Transitions**: Smooth fade between scenes
3. **Highlight Cursor**: Add cursor highlight/ring effect
4. **Zoom Effects**: Zoom in on important details
5. **Text Overlays**: Add feature names or callouts

### Background Music
- **Volume**: Keep low (20-30% of voice)
- **Style**: Upbeat, corporate, tech-friendly
- **Sources**: YouTube Audio Library, Epidemic Sound
- **Avoid**: Distracting lyrics, loud drums

### Export Settings
- **Format**: MP4 (H.264)
- **Resolution**: 1920x1080
- **Frame Rate**: 30fps
- **Bitrate**: 10-15 Mbps
- **Audio**: AAC, 192 kbps, 48kHz

---

## YouTube Upload

### Video Details
**Title**: AP2 Expense Agent - AI-Powered Expense Management Demo

**Description**:
```
AP2 Expense Agent is the modern expense management platform for growing teams.

✨ Key Features:
• AI-powered receipt scanning and categorization
• One-click approval workflows
• Real-time budget tracking and analytics
• Cryptographically verified payments via AP2 protocol
• Multi-tenant organization management
• Fully responsive mobile experience

🚀 Get Started:
Available on Google Cloud Marketplace
Free 14-day trial - No credit card required

🔗 Learn More:
Website: https://ap2expense.com
Documentation: https://docs.ap2expense.com
Support: support@ap2expense.com

#ExpenseManagement #AI #CloudSoftware #GCP #BusinessSoftware
```

**Tags**: expense management, AI, OCR, receipt scanning, budget tracking, cloud software, SaaS, Google Cloud, business automation

**Thumbnail**: Create eye-catching thumbnail with product logo and "Watch Demo" text

**Privacy**: Unlisted (for marketplace submission)
**Category**: Science & Technology
**Language**: English

---

## Checklist Before Publishing

- [ ] Video is 3 minutes or less
- [ ] Audio is clear and professional
- [ ] All features demonstrated work correctly
- [ ] No personal/sensitive information visible
- [ ] Branding is consistent
- [ ] Call-to-action is clear
- [ ] YouTube description complete
- [ ] Video set to "Unlisted"
- [ ] Video URL copied for marketplace submission

---

**Production Time Estimate**:
- Recording: 1-2 hours (multiple takes)
- Editing: 2-3 hours
- Review & refinement: 1 hour
- **Total**: 4-6 hours

**Tip**: Record in short segments (30 seconds each) rather than one long take. Easier to edit and fix mistakes!
