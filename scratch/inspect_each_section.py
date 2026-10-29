import re

with open("scratch/omrix_raw.html", "r", encoding="utf-8") as f:
    html = f.read()

sections = re.findall(r'<section[^>]*>(.*?)</section>', html, re.DOTALL)
print(f"Total sections: {len(sections)}")

for i, sec in enumerate(sections):
    headings = re.findall(r'<(h[1-6])[^>]*>(.*?)</\1>', sec, re.DOTALL)
    clean_headings = []
    for htag, htxt in headings:
        clean = re.sub(r'<[^>]+>', '', htxt).strip()
        clean = re.sub(r'\s+', ' ', clean)
        clean_headings.append(f"{htag}: {clean}")
        
    imgs = list(set(re.findall(r'https://framerusercontent\.com/images/[a-zA-Z0-9_\-\.]+', sec)))
    
    # Text snippet
    txt = re.sub(r'<[^>]+>', ' ', sec)
    txt = re.sub(r'\s+', ' ', txt).strip()
    
    print(f"\n================================ SECTION {i+1} ================================")
    print("Headings:", clean_headings)
    print("Images:", imgs)
    print("Text preview:", txt[:350])
