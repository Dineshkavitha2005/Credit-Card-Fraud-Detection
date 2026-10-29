import re

with open("scratch/omrix_raw.html", "r", encoding="utf-8") as f:
    html = f.read()

# Let's extract CSS rules that define borders, backgrounds, buttons, and animations
styles = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
print("Style tags found:", len(styles))

all_css = "\n".join(styles)
with open("scratch/omrix_extracted_styles.css", "w", encoding="utf-8") as out:
    out.write(all_css)

print("Saved scratch/omrix_extracted_styles.css, size:", len(all_css))

# Look for key CSS patterns
border_radii = set(re.findall(r'border-radius:\s*([^;]+);', all_css))
print("Border radii:", list(border_radii)[:15])

box_shadows = set(re.findall(r'box-shadow:\s*([^;]+);', all_css))
print("Box shadows:", list(box_shadows)[:15])

gradients = set(re.findall(r'background(?:-image)?:\s*([^;]*(?:linear-gradient|radial-gradient)[^;]*);', all_css))
print("Gradients found:", len(gradients))
for g in list(gradients)[:10]:
    print("  ->", g[:100])
