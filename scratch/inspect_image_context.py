import re

with open("scratch/omrix_raw.html", "r", encoding="utf-8") as f:
    html = f.read()

images = set(re.findall(r'https://framerusercontent\.com/images/[a-zA-Z0-9_\-\.]+', html))

for img in sorted(list(images)):
    pos = html.find(img)
    start = max(0, pos - 200)
    end = min(len(html), pos + 300)
    snippet = html[start:end]
    clean_snippet = re.sub(r'\s+', ' ', snippet)
    print(f"\n--- {img} ---")
    print(clean_snippet[:250])
