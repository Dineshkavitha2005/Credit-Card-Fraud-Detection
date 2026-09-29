"""
Generate Sentinel Brand Assets, Favicons, and Optimized Images.
Produces vector SVG and optimized PNG/WebP files in static/img and app/static/img.
"""

import os
import shutil
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
STATIC_IMG = os.path.join(ROOT_DIR, 'static', 'img')
APP_STATIC_IMG = os.path.join(ROOT_DIR, 'app', 'static', 'img')

os.makedirs(STATIC_IMG, exist_ok=True)
os.makedirs(APP_STATIC_IMG, exist_ok=True)

# 1. Vector SVG Favicon / Logo
SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="shieldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2563EB"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
    <linearGradient id="glowGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#3B82F6" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#1D4ED8" stop-opacity="0.2"/>
    </linearGradient>
  </defs>
  <!-- Background Shield -->
  <path d="M32 4 L56 14 V32 C56 46.5 45.8 56.4 32 60 C18.2 56.4 8 46.5 8 32 V14 Z" 
        fill="url(#shieldGrad)" stroke="#3B82F6" stroke-width="2" stroke-linejoin="round"/>
  <!-- Inner Subtle Shield Contour -->
  <path d="M32 10 L50 18 V31 C50 42.5 42 50.5 32 54 C22 50.5 14 42.5 14 31 V18 Z" 
        fill="url(#glowGrad)" opacity="0.5"/>
  <!-- Verification Checkmark -->
  <path d="M23 32 L29 38 L42 24" 
        fill="none" stroke="#FFFFFF" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

with open(os.path.join(STATIC_IMG, 'favicon.svg'), 'w', encoding='utf-8') as f:
    f.write(SVG_CONTENT)

# 2. Helper to draw Sentinel Shield onto PIL Image
def draw_sentinel_shield(size):
    """Render Sentinel brand shield onto an RGBA image of given square dimension."""
    scale = size / 64.0
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Outer shield points
    outer_pts = [
        (int(32 * scale), int(4 * scale)),
        (int(56 * scale), int(14 * scale)),
        (int(56 * scale), int(32 * scale)),
        (int(46 * scale), int(48 * scale)),
        (int(32 * scale), int(60 * scale)),
        (int(18 * scale), int(48 * scale)),
        (int(8 * scale), int(32 * scale)),
        (int(8 * scale), int(14 * scale)),
    ]
    draw.polygon(outer_pts, fill=(15, 23, 42, 255))
    draw.line(outer_pts + [outer_pts[0]], fill=(37, 99, 235, 255), width=max(1, int(2 * scale)))
    
    # Inner accent shield
    inner_pts = [
        (int(32 * scale), int(10 * scale)),
        (int(50 * scale), int(18 * scale)),
        (int(50 * scale), int(31 * scale)),
        (int(42 * scale), int(44 * scale)),
        (int(32 * scale), int(53 * scale)),
        (int(22 * scale), int(44 * scale)),
        (int(14 * scale), int(31 * scale)),
        (int(14 * scale), int(18 * scale)),
    ]
    draw.polygon(inner_pts, fill=(37, 99, 235, 220))
    
    # Checkmark lines
    c_pts = [
        (int(23 * scale), int(32 * scale)),
        (int(29 * scale), int(38 * scale)),
        (int(41 * scale), int(24 * scale))
    ]
    line_w = max(2, int(5 * scale))
    draw.line([c_pts[0], c_pts[1]], fill=(255, 255, 255, 255), width=line_w)
    draw.line([c_pts[1], c_pts[2]], fill=(255, 255, 255, 255), width=line_w)
    
    return img

# Generate required icon sizes
sizes = {
    'favicon-16x16.png': 16,
    'favicon-32x32.png': 32,
    'apple-touch-icon.png': 180,
    'android-chrome-192x192.png': 192,
    'android-chrome-512x512.png': 512,
    'sentinel-logo.png': 512,
}

for filename, dim in sizes.items():
    icon = draw_sentinel_shield(dim)
    icon.save(os.path.join(STATIC_IMG, filename), format='PNG', optimize=True)

# Generate Open Graph Social Preview Image (1200x630)
og_img = Image.new('RGBA', (1200, 630), (15, 23, 42, 255))
og_draw = ImageDraw.Draw(og_img)

# Background subtle grid / accent lines
for y in range(0, 630, 45):
    og_draw.line([(0, y), (1200, y)], fill=(30, 41, 59, 120), width=1)
for x in range(0, 1200, 60):
    og_draw.line([(x, 0), (x, 630)], fill=(30, 41, 59, 120), width=1)

# Subtle center gradient box
og_draw.rounded_rectangle([(60, 60), (1140, 570)], radius=24, fill=(17, 24, 39, 230), outline=(37, 99, 235, 255), width=2)

# Paste brand shield
shield_og = draw_sentinel_shield(160)
og_img.paste(shield_og, (120, 150), shield_og)

# Add text elements via Pillow basic font or lines
# Title banner: "SENTINEL" and subtitle
try:
    font_lg = ImageFont.truetype("arial.ttf", 64)
    font_sub = ImageFont.truetype("arial.ttf", 32)
    font_sm = ImageFont.truetype("arial.ttf", 22)
except Exception:
    font_lg = ImageFont.load_default()
    font_sub = ImageFont.load_default()
    font_sm = ImageFont.load_default()

og_draw.text((320, 160), "SENTINEL", fill=(255, 255, 255), font=font_lg)
og_draw.text((320, 245), "Financial Fraud Detection & Surveillance", fill=(59, 130, 246), font=font_sub)
og_draw.text((320, 300), "Sub-10ms Transaction Risk Scoring | Dynamic Heuristics | Machine Learning", fill=(156, 163, 175), font=font_sm)

# Pill badges
badges = ["PCI-DSS Sensitive Vault", "AES-128 Encryption", "Scikit-Learn ML Inference", "Audit-Ready Logs"]
bx = 120
by = 460
for b in badges:
    og_draw.rounded_rectangle([(bx, by), (bx + 220, by + 42)], radius=8, fill=(30, 41, 59, 255), outline=(59, 130, 246, 180), width=1)
    og_draw.text((bx + 14, by + 10), b, fill=(241, 245, 249), font=font_sm)
    bx += 240

og_img.save(os.path.join(STATIC_IMG, 'sentinel-og.png'), format='PNG', optimize=True)
og_img.save(os.path.join(STATIC_IMG, 'sentinel-og.webp'), format='WEBP', quality=90)

# Generate dashboard-preview.webp / png (800x480) for landing page visual
dash_img = Image.new('RGBA', (800, 480), (15, 23, 42, 255))
dash_draw = ImageDraw.Draw(dash_img)

# Outer card border
dash_draw.rounded_rectangle([(0, 0), (799, 479)], radius=16, fill=(15, 23, 42, 255), outline=(37, 99, 235, 180), width=2)
# Topbar header
dash_draw.rectangle([(0, 0), (800, 52)], fill=(30, 41, 59, 255))
dash_draw.ellipse([(20, 20), (32, 32)], fill=(239, 68, 68, 255))
dash_draw.ellipse([(40, 20), (52, 32)], fill=(245, 158, 11, 255))
dash_draw.ellipse([(60, 20), (72, 32)], fill=(16, 185, 129, 255))
dash_draw.text((100, 16), "Sentinel Live Surveillance Console — Real-Time Transaction Stream", fill=(203, 213, 225), font=font_sm)

# Metric cards
dash_draw.rounded_rectangle([(30, 80), (250, 170)], radius=10, fill=(30, 41, 59, 200), outline=(59, 130, 246, 100))
dash_draw.text((46, 95), "ML INFERENCE LATENCY", fill=(148, 163, 184), font=font_sm)
dash_draw.text((46, 125), "6.2 ms", fill=(59, 130, 246), font=font_sub)

dash_draw.rounded_rectangle([(280, 80), (510, 170)], radius=10, fill=(30, 41, 59, 200), outline=(16, 185, 129, 100))
dash_draw.text((296, 95), "DETECTION ACCURACY", fill=(148, 163, 184), font=font_sm)
dash_draw.text((296, 125), "99.42%", fill=(16, 185, 129), font=font_sub)

dash_draw.rounded_rectangle([(540, 80), (770, 170)], radius=10, fill=(30, 41, 59, 200), outline=(244, 63, 94, 100))
dash_draw.text((556, 95), "FRAUD INTERCEPTED", fill=(148, 163, 184), font=font_sm)
dash_draw.text((556, 125), "$142,850", fill=(244, 63, 94), font=font_sub)

# Simulated table
table_top = 200
dash_draw.rectangle([(30, table_top), (770, table_top + 36)], fill=(30, 41, 59, 255))
dash_draw.text((46, table_top + 8), "TXN ID          CARD NUMBER      AMOUNT    RISK SCORE  STATUS", fill=(148, 163, 184), font=font_sm)

rows = [
    ("TXN-90214   **** **** **** 4821   $1,240.00   0.8872 (HIGH)   [ DECLINED ]", (244, 63, 94)),
    ("TXN-90215   **** **** **** 1092     $42.50   0.0120 (LOW)    [ APPROVED ]", (16, 185, 129)),
    ("TXN-90216   **** **** **** 7731    $680.00   0.4510 (MED)    [ MANUAL REVIEW ]", (245, 158, 11)),
    ("TXN-90217   **** **** **** 3319     $19.99   0.0045 (LOW)    [ APPROVED ]", (16, 185, 129)),
    ("TXN-90218   **** **** **** 9104   $3,450.00   0.9410 (HIGH)   [ DECLINED ]", (244, 63, 94)),
]
ry = table_top + 46
for row_text, color in rows:
    dash_draw.rectangle([(30, ry), (770, ry + 36)], fill=(17, 24, 39, 150))
    dash_draw.text((46, ry + 8), row_text, fill=color, font=font_sm)
    ry += 42

dash_img.save(os.path.join(STATIC_IMG, 'dashboard-preview.png'), format='PNG', optimize=True)
dash_img.save(os.path.join(STATIC_IMG, 'dashboard-preview.webp'), format='WEBP', quality=85)

# Sync all files to app/static/img
for fname in os.listdir(STATIC_IMG):
    s_path = os.path.join(STATIC_IMG, fname)
    if os.path.isfile(s_path):
        shutil.copy2(s_path, os.path.join(APP_STATIC_IMG, fname))

print("Asset generation complete!")
