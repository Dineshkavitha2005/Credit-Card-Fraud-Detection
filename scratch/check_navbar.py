import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
import threading, time
from app import create_app
from app.config import TestingConfig

app = create_app(TestingConfig)
threading.Thread(target=lambda: app.run(port=5088, debug=False, use_reloader=False), daemon=True).start()
time.sleep(1.5)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for width in [1440, 1200, 1080, 992, 900]:
        page = browser.new_page(viewport={'width': width, 'height': 800})
        page.goto('http://127.0.0.1:5088/')
        page.wait_for_timeout(300)
        nav = page.locator('.omrix-navbar')
        box = nav.bounding_box()
        items = page.locator('.omrix-nav-item')
        print(f"=== Viewport Width: {width} ===")
        print(f"Navbar: width={box['width']:.1f}, height={box['height']:.1f}")
        for i in range(items.count()):
            item = items.nth(i)
            ibox = item.bounding_box()
            text = item.text_content().strip()
            print(f"   Nav Item '{text}': width={ibox['width']:.1f}, height={ibox['height']:.1f}")
        btn = page.locator('#main-header .btn-pill-cta')
        if btn.count() > 0 and btn.is_visible():
            bbox = btn.bounding_box()
            print(f"   CTA btn: width={bbox['width']:.1f}, height={bbox['height']:.1f}")
        sign_in = page.locator('#main-header .nav-sign-in')
        if sign_in.count() > 0 and sign_in.is_visible():
            sbox = sign_in.bounding_box()
            print(f"   Sign In: width={sbox['width']:.1f}, height={sbox['height']:.1f}")
        page.screenshot(path=f"scratch/navbar_{width}.png")
    browser.close()
