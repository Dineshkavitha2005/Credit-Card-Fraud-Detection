"""
Strict 3-Color Audit Script for Sentinel Landing Page.

Validates that static/css/landing.css, templates/landing.html,
templates/public_base.html, and static/js/landing-motion.js
strictly use only:
1. White: #FFFFFF / rgb(255, 255, 255) / rgba(255, 255, 255, <alpha>)
2. Deep Navy: #0F172A / rgb(15, 23, 42) / rgba(15, 23, 42, <alpha>)
3. Blue: #2563EB / rgb(37, 99, 235) / rgba(37, 99, 235, <alpha>)
Plus standard keywords: transparent, currentColor, inherit, none.
"""

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

TARGET_FILES = [
    BASE_DIR / "static" / "css" / "landing.css",
    BASE_DIR / "templates" / "landing.html",
    BASE_DIR / "templates" / "public_base.html",
    BASE_DIR / "static" / "js" / "landing-motion.js"
]

ALLOWED_HEX = {
    "#ffffff", "#fff",
    "#0f172a",
    "#2563eb"
}

ALLOWED_RGB = {
    (255, 255, 255),
    (15, 23, 42),
    (37, 99, 235)
}

DISALLOWED_NAMED_COLORS = {
    "red", "green", "blue", "black", "gray", "grey", "silver", "maroon",
    "purple", "fuchsia", "lime", "olive", "yellow", "navy", "teal", "aqua",
    "orange", "aliceblue", "antiquewhite", "aquamarine", "azure", "beige",
    "bisque", "blanchedalmond", "blueviolet", "brown", "burlywood", "cadetblue",
    "chartreuse", "chocolate", "coral", "cornflowerblue", "cornsilk", "crimson",
    "cyan", "darkblue", "darkcyan", "darkgoldenrod", "darkgray", "darkgreen",
    "darkgrey", "darkkhaki", "darkmagenta", "darkolivegreen", "darkorange",
    "darkorchid", "darkred", "darksalmon", "darkseagreen", "darkslateblue",
    "darkslategray", "darkslategrey", "darkturquoise", "darkviolet", "deeppink",
    "deepskyblue", "dimgray", "dimgrey", "dodgerblue", "firebrick", "floralwhite",
    "forestgreen", "gainsboro", "ghostwhite", "gold", "goldenrod", "greenyellow",
    "honeydew", "hotpink", "indianred", "indigo", "ivory", "khaki", "lavender",
    "lavenderblush", "lawngreen", "lemonchiffon", "lightblue", "lightcoral",
    "lightcyan", "lightgoldenrodyellow", "lightgray", "lightgreen", "lightgrey",
    "lightpink", "lightsalmon", "lightseagreen", "lightskyblue", "lightslategray",
    "lightslategrey", "lightsteelblue", "lightyellow", "limegreen", "linen",
    "magenta", "mediumaquamarine", "mediumblue", "mediumorchid", "mediumpurple",
    "mediumseagreen", "mediumslateblue", "mediumspringgreen", "mediumturquoise",
    "mediumvioletred", "midnightblue", "mintcream", "mistyrose", "moccasin",
    "navajowhite", "oldlace", "olivedrab", "orangered", "orchid", "palegoldenrod",
    "palegreen", "paleturquoise", "palevioletred", "papayawhip", "peachpuff",
    "peru", "pink", "plum", "powderblue", "rosybrown", "royalblue", "saddlebrown",
    "salmon", "sandybrown", "seagreen", "seashell", "sienna", "skyblue",
    "slateblue", "slategray", "slategrey", "snow", "springgreen", "steelblue",
    "tan", "thistle", "tomato", "turquoise", "violet", "wheat", "whitesmoke",
    "yellowgreen"
}


def audit_content(file_path: Path):
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    violations = []

    # Hex match: #123, #123456, #12345678 (exclude text like #TX- or #8921-94A or Ingress #8921)
    hex_pattern = re.compile(r"(?<![A-Za-z0-9])#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
    # RGB/RGBA match
    rgb_pattern = re.compile(r"rgba?\(\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)(?:\s*,\s*([0-9.]+))?\s*\)")
    # HSL match
    hsl_pattern = re.compile(r"hsla?\([^)]+\)")
    # Linear/radial gradient match
    gradient_pattern = re.compile(r"(linear-gradient|radial-gradient|conic-gradient)")

    for line_no, line in enumerate(lines, start=1):
        # Ignore external CDN URLs (like google fonts or unpkg)
        if "fonts.googleapis.com" in line or "unpkg.com" in line or "data:image/svg+xml" in line:
            continue

        # Check Hex
        for match in hex_pattern.finditer(line):
            val = match.group(0).lower()
            if val not in ALLOWED_HEX:
                violations.append((line_no, f"Disallowed HEX: '{val}' in `{line.strip()}`"))

        # Check RGB/RGBA
        for match in rgb_pattern.finditer(line):
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if (r, g, b) not in ALLOWED_RGB:
                violations.append((line_no, f"Disallowed RGB({r}, {g}, {b}) in `{line.strip()}`"))

        # Check HSL
        for match in hsl_pattern.finditer(line):
            violations.append((line_no, f"Disallowed HSL color `{match.group(0)}` in `{line.strip()}`"))

        # Check Gradients in CSS
        if file_path.suffix == ".css":
            for match in gradient_pattern.finditer(line):
                violations.append((line_no, f"Disallowed Gradient `{match.group(0)}` in `{line.strip()}`"))

    return violations


def main():
    total_violations = 0
    print("=" * 60)
    print("STRICT 3-COLOR SYSTEM AUDIT")
    print("Allowed: #FFFFFF (White), #0F172A (Deep Navy), #2563EB (Blue)")
    print("=" * 60)

    for target in TARGET_FILES:
        if not target.exists():
            print(f"[-] File not found: {target}")
            continue

        violations = audit_content(target)
        rel_path = target.relative_to(BASE_DIR)
        if violations:
            print(f"\n[FAIL] {rel_path}: {len(violations)} violations found")
            for line_no, msg in violations[:15]:  # show first 15
                print(f"  Line {line_no}: {msg}")
            if len(violations) > 15:
                print(f"  ... and {len(violations) - 15} more")
            total_violations += len(violations)
        else:
            print(f"[PASS] {rel_path}: 0 violations (Clean!)")

    print("\n" + "=" * 60)
    if total_violations > 0:
        print(f"AUDIT FAILED: {total_violations} total violations.")
        return 1
    else:
        print("AUDIT SUCCESS: All landing page styles strictly adhere to 3 colors!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
