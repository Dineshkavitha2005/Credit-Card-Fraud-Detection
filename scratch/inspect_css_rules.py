import re

with open("scratch/omrix_extracted_styles.css", "r", encoding="utf-8") as f:
    css = f.read()

# Let's search for key classes or properties
def find_rules(pattern):
    return re.findall(rf'([^{{]+)\{{([^}}]*{pattern}[^}}]*)}}', css)

print("--- Button rules ---")
btn_rules = find_rules('cursor:pointer')
print(f"Total cursor:pointer rules: {len(btn_rules)}")
for sel, body in btn_rules[:5]:
    print(f"Selector: {sel.strip()[:60]}\nBody: {body.strip()[:100]}\n")

print("--- Bento or Grid rules ---")
grid_rules = find_rules('display:grid')
print(f"Total grid rules: {len(grid_rules)}")

print("--- Backdrop blur rules ---")
blur_rules = find_rules('backdrop-filter')
print(f"Total blur rules: {len(blur_rules)}")
for sel, body in blur_rules[:5]:
    print(f"Selector: {sel.strip()[:60]}\nBody: {body.strip()[:100]}\n")
