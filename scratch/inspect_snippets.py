import re

with open("scratch/omrix_raw.html", "r", encoding="utf-8") as f:
    html = f.read()

# Let's search for "Build Smarter Workflows" and see surrounding HTML
pos = html.find("Build Smarter Workflows")
print("Hero title snippet:")
print(html[max(0, pos-400):min(len(html), pos+600)])

# Let's search for "SIMPLE PRICING" and see surrounding HTML
pos2 = html.find("SIMPLE PRICING")
print("\nPricing snippet:")
print(html[max(0, pos2-300):min(len(html), pos2+800)])

# Let's search for "COMMON QUESTION" and see surrounding HTML
pos3 = html.find("COMMON QUESTION")
print("\nFAQ snippet:")
print(html[max(0, pos3-300):min(len(html), pos3+800)])
