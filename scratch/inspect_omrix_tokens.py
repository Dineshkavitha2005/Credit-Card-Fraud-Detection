import re
import json

file_path = r"C:\Users\Dinesh A\.gemini\antigravity-ide\brain\e07a1368-010d-442b-9a6d-bd50ae9f26d7\.system_generated\steps\4\content.md"

with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Let's extract all CSS variables and color tokens
css_vars = re.findall(r'--token-[a-f0-9\-]+:\s*([^;]+);', content)
print("Unique CSS tokens:", set(css_vars))

# Let's search for Framer component names or section classes
framer_components = re.findall(r'data-framer-name=[\'"]([^\'"]+)[\'"]', content)
print(f"Total data-framer-name elements: {len(framer_components)}")
unique_components = []
for c in framer_components:
    if c not in unique_components:
        unique_components.append(c)
print("Unique components:", unique_components[:50])

# Let's search for all images in the Framer site
images = re.findall(r'https://framerusercontent\.com/images/[a-zA-Z0-9_\-]+\.(?:png|jpg|jpeg|webp|svg)', content)
print("Images found:", len(set(images)))
for img in sorted(list(set(images))):
    print("IMG:", img)
