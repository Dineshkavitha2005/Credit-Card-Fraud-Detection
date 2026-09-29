import re
import json

with open("scratch/omrix_raw.html", "r", encoding="utf-8") as f:
    html = f.read()

print("HTML size:", len(html))

# Let's find all images in the fresh HTML
images = set(re.findall(r'https://framerusercontent\.com/images/[a-zA-Z0-9_\-\.]+', html))
print(f"Total Framer images ({len(images)}):")
for img in sorted(list(images)):
    print("  ", img)

# Let's inspect sections or headings
headings = re.findall(r'<(h[1-6])[^>]*>(.*?)</\1>', html, re.DOTALL)
print(f"\nHeadings ({len(headings)}):")
for tag, text in headings:
    # strip inner tags
    clean = re.sub(r'<[^>]+>', '', text).strip()
    clean = re.sub(r'\s+', ' ', clean)
    print(f"  {tag}: {clean}")

# Let's look for navigation links
nav_links = re.findall(r'<a[^>]+href=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</a>', html, re.DOTALL)
print(f"\nLinks ({len(nav_links)}):")
for href, text in nav_links:
    clean = re.sub(r'<[^>]+>', '', text).strip()
    clean = re.sub(r'\s+', ' ', clean)
    if clean and len(clean) < 50:
        print(f"  [{clean}] -> {href}")

# Let's search for SVG icons or paths
svgs = re.findall(r'<svg[^>]*>.*?</svg>', html, re.DOTALL)
print(f"\nTotal SVGs: {len(svgs)}")
