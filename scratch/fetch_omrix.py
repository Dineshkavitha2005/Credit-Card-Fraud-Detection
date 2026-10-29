import urllib.request
import re
import json

url = "https://omrix.framer.ai/"
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8')
    print("Fetched fresh HTML, length:", len(html))
    
    # Save to scratch
    with open("scratch/omrix_raw.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    # Find all module scripts and chunk scripts
    scripts = re.findall(r'<script[^>]+src=[\'"]([^\'"]+)[\'"]', html)
    print("Scripts found in live HTML:", len(scripts))
    for s in scripts:
        print(" ->", s)
        
    # Also find modulepreload links
    preloads = re.findall(r'<link[^>]+rel=[\'"]modulepreload[\'"][^>]+href=[\'"]([^\'"]+)[\'"]', html)
    print("Preloads found:", len(preloads))
    for p in preloads:
        print(" =>", p)
except Exception as e:
    print("Error:", e)
