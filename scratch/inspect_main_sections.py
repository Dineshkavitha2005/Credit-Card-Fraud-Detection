import re

with open("scratch/omrix_raw.html", "r", encoding="utf-8") as f:
    html = f.read()

# Let's find sections or top-level containers
sections = re.findall(r'<section[^>]*>.*?</section>', html, re.DOTALL)
print(f"Total <section> tags: {len(sections)}")

# If no <section> tags, find main container divs
main_match = re.search(r'<div id="main"[^>]*>(.*?)</div>\s*<div id="__framer-badge-container', html, re.DOTALL)
if main_match:
    print("Found #main container! Length:", len(main_match.group(1)))
    # Look for top-level direct child divs or elements
    # Framer uses data-framer-name
    named = re.findall(r'data-framer-name=[\'"]([^\'"]+)[\'"]', main_match.group(1))
    print("Named elements in main:", len(named))
    # print unique ordered
    seen = []
    for n in named:
        if n not in seen:
            seen.append(n)
    print("Unique named sections/components:")
    for s in seen[:60]:
        print("  *", s)
else:
    print("No #main container found.")
