# Product Icon Design Guide

## Template Provided

We've created an SVG template at `marketplace/product-icon-template.svg` that you can customize.

### Quick Customization Options

1. **Use as-is**: The template is production-ready with:
   - Receipt paper design
   - AI sparkle indicator
   - Approval checkmark
   - Currency symbol
   - Blue gradient background

2. **Customize colors**: Edit the SVG file and change:
   - `#4F46E5` (primary blue) → your brand color
   - `#10B981` (green checkmark) → your accent color
   - `#FCD34D` (gold sparkle) → your highlight color

3. **Export to PNG**:
   ```bash
   # Using Inkscape (free)
   inkscape product-icon-template.svg --export-filename=product-icon.png --export-width=512 --export-height=512

   # Using ImageMagick
   convert -background none product-icon-template.svg -resize 512x512 product-icon.png

   # Or use online tool: https://svgtopng.com
   ```

---

## Requirements (GCP Marketplace)

| Specification | Requirement |
|--------------|-------------|
| **Format** | PNG with transparent background |
| **Size** | 512x512 pixels (square) |
| **File Size** | < 1MB |
| **Resolution** | 72 DPI minimum |
| **Color Space** | RGB |
| **Background** | Transparent or solid color |

---

## Design Principles

### Do ✓
- **Simple**: Clear at small sizes (32x32)
- **Recognizable**: Instantly convey "expense management"
- **Professional**: Match enterprise software standards
- **Distinctive**: Stand out in marketplace listings
- **Scalable**: Works at all sizes

### Don't ✗
- **Too detailed**: Avoid fine lines or small text
- **Busy**: Keep it clean and focused
- **Generic**: Avoid stock icons
- **Low contrast**: Ensure visibility on light/dark backgrounds
- **Copyrighted**: Don't use third-party logos

---

## Icon Concepts (Alternatives)

If you want to create a different design, consider these concepts:

### Concept 1: Receipt + AI (Current Template)
- Central receipt paper
- AI sparkle indicator
- Approval checkmark
- Currency symbol
- **Best for**: Emphasizing AI features

### Concept 2: Simplified Receipt
- Minimalist receipt outline
- Single accent color
- Clean lines
- **Best for**: Modern, minimal aesthetic

### Concept 3: Folder + Dollar
- Document folder
- Dollar sign overlay
- Professional gradient
- **Best for**: Traditional business software look

### Concept 4: Circular Badge
- Circle with receipt icon
- Bold border
- Company initials "AP2"
- **Best for**: Brand recognition

---

## Color Palette Recommendations

### Primary (Choose one set)

**Option 1: Blue (Trust & Stability)**
- Primary: `#4F46E5` (Indigo)
- Accent: `#10B981` (Emerald)
- Highlight: `#FCD34D` (Amber)

**Option 2: Green (Finance & Growth)**
- Primary: `#059669` (Emerald)
- Accent: `#3B82F6` (Blue)
- Highlight: `#F59E0B` (Amber)

**Option 3: Purple (Innovation & Premium)**
- Primary: `#7C3AED` (Purple)
- Accent: `#EC4899` (Pink)
- Highlight: `#14B8A6` (Teal)

---

## Tools for Icon Creation

### Free Tools
1. **Inkscape** (Vector editor)
   - Download: https://inkscape.org
   - Open SVG template → Customize → Export PNG

2. **GIMP** (Raster editor)
   - Download: https://www.gimp.org
   - Create 512x512 canvas → Design → Export PNG

3. **Figma** (Online, free)
   - https://figma.com
   - Import SVG → Edit → Export PNG

### Paid Tools
1. **Adobe Illustrator** (Vector)
2. **Adobe Photoshop** (Raster)
3. **Sketch** (macOS only)

### Online Services
1. **Canva** (canva.com) - Templates available
2. **Logo.com** - AI-generated logos
3. **Fiverr** - Hire designer ($20-50)

---

## Step-by-Step: Export from Template

### Using Inkscape (Recommended, Free)

1. **Install Inkscape**
   ```bash
   # Windows
   # Download from https://inkscape.org/release/

   # macOS
   brew install inkscape

   # Linux
   sudo apt-get install inkscape
   ```

2. **Open Template**
   ```bash
   inkscape marketplace/product-icon-template.svg
   ```

3. **Customize** (Optional)
   - Select elements with mouse
   - Change colors in "Fill and Stroke" panel
   - Adjust positions with arrow keys

4. **Export to PNG**
   - File → Export PNG Image
   - Export area: Page
   - Width: 512 px
   - Height: 512 px
   - Filename: `product-icon.png`
   - Click "Export"

### Using Command Line

```bash
# Inkscape (recommended for best quality)
inkscape marketplace/product-icon-template.svg \
  --export-type=png \
  --export-filename=marketplace/product-icon.png \
  --export-width=512 \
  --export-height=512

# ImageMagick (if installed)
convert -density 300 \
  -background transparent \
  marketplace/product-icon-template.svg \
  -resize 512x512 \
  marketplace/product-icon.png

# Using online tool
# Upload to: https://cloudconvert.com/svg-to-png
# Set output size: 512x512
```

---

## Quality Checklist

Before uploading to GCP Marketplace:

- [ ] **Size**: Exactly 512x512 pixels
- [ ] **Format**: PNG with transparency
- [ ] **File size**: < 1MB (optimize if needed)
- [ ] **Clarity**: Icon is clear at 32x32 preview
- [ ] **Contrast**: Visible on both light and dark backgrounds
- [ ] **Consistency**: Matches brand colors
- [ ] **No artifacts**: Clean edges, no pixelation
- [ ] **Professional**: Looks polished and modern

---

## Optimization (Reduce File Size)

If your PNG is too large (>1MB):

### Online Tools
- **TinyPNG**: https://tinypng.com (drag and drop)
- **Compressor.io**: https://compressor.io

### Command Line
```bash
# Using optipng (lossless)
optipng -o7 marketplace/product-icon.png

# Using pngquant (lossy but smaller)
pngquant --quality=80-95 marketplace/product-icon.png
```

---

## Testing Your Icon

1. **Preview at different sizes**:
   ```bash
   # Create test versions
   convert marketplace/product-icon.png -resize 32x32 icon-32.png
   convert marketplace/product-icon.png -resize 64x64 icon-64.png
   convert marketplace/product-icon.png -resize 128x128 icon-128.png
   ```

2. **Test on backgrounds**:
   - White background
   - Dark gray background (#1F2937)
   - Light gray background (#F3F4F6)

3. **Check in marketplace context**:
   - View in a grid with other app icons
   - Does it stand out?
   - Is it recognizable?

---

## Alternative: Hire a Designer

If you want a custom professional icon:

### Freelance Platforms
- **Fiverr**: $20-100 (2-5 days)
  - Search: "app icon design 512x512"
  - Choose designer with good reviews

- **Upwork**: $50-200 (3-7 days)
  - Post job: "GCP Marketplace Product Icon Design"
  - Provide requirements from this guide

- **99designs**: $299+ (contest, multiple options)
  - Launch icon design contest
  - Get 30-50 designs to choose from

### Design Brief Template

```
Project: Product Icon for GCP Marketplace

Requirements:
- Size: 512x512 px PNG
- Style: Modern, professional, tech-focused
- Concept: Expense management with AI
- Colors: Blue (#4F46E5), Green (#10B981), Gold (#FCD34D)
- Elements: Receipt/document, AI indicator, currency symbol
- Must be: Simple, scalable, recognizable at small sizes
- Inspiration: Notion, Slack, Asana app icons

Deliverables:
- PNG (512x512)
- Source file (AI/PSD/SVG)
- Variations (light/dark background)

Budget: $50
Timeline: 3 days
```

---

## Next Steps

1. **Use template as-is**:
   ```bash
   # Export the provided template
   inkscape marketplace/product-icon-template.svg --export-filename=marketplace/product-icon.png --export-width=512

   # Or use online converter: https://svgtopng.com
   ```

2. **Customize template**:
   - Open in Inkscape/Figma
   - Change colors to match your brand
   - Export as PNG

3. **Hire designer** (if preferred):
   - Post on Fiverr with design brief
   - Review within 3-5 days
   - Request revisions if needed

4. **Upload to marketplace**:
   - Go to Partner Portal
   - Upload product-icon.png
   - Preview in listing

---

**Time Estimate**:
- Use template as-is: 10 minutes
- Customize template: 30-60 minutes
- Hire designer: 3-5 days
- Total: 1 hour or less (DIY)

**Recommendation**: Start with the template. You can always update the icon later after launch!
