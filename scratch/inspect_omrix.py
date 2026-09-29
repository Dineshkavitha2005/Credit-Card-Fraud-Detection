import re
import urllib.request
import json

file_path = r"C:\Users\Dinesh A\.gemini\antigravity-ide\brain\e07a1368-010d-442b-9a6d-bd50ae9f26d7\.system_generated\steps\4\content.md"

with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

print(f"Total HTML content length: {len(content)}")

# Look for framer search index or components
search_idx_match = re.search(r'https://framerusercontent\.com/sites/[^\"]+searchIndex[^\"]+\.json', content)
if search_idx_match:
    search_idx_url = search_idx_match.group(0)
    print(f"Found searchIndex url: {search_idx_url}")
    try:
        req = urllib.request.Request(search_idx_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("Search Index JSON keys:", list(data.keys()) if isinstance(data, dict) else type(data))
            with open("scratch/search_index.json", "w", encoding="utf-8") as out_f:
                json.dump(data, out_f, indent=2)
            print("Wrote scratch/search_index.json")
    except Exception as e:
        print(f"Error fetching searchIndex: {e}")

# Find all script src
scripts = re.findall(r'<script[^>]*src=[\'"]([^\'"]+)[\'"]', content)
print("Found script src tags:", len(scripts))
for s in scripts:
    print(" -", s)
