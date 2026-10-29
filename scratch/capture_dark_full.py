import sys
import os
import threading
import time

sys.path.insert(0, os.path.abspath('.'))
from app import create_app
from playwright.sync_api import sync_playwright

app = create_app()

def run_server():
    app.run(port=5098, debug=False, use_reloader=False)

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(2)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:5098/", wait_until="networkidle")
    page.wait_for_timeout(500)
    
    # Toggle to dark mode
    page.locator(".theme-toggle-btn").first.click()
    page.wait_for_timeout(500)
    
    artifact_dir = r"C:\Users\Dinesh A\.gemini\antigravity-ide\brain\e07a1368-010d-442b-9a6d-bd50ae9f26d7"
    page.screenshot(path=os.path.join(artifact_dir, "omrix_landing_full_dark.png"), full_page=True)
    print("[✓] Saved full page dark mode screenshot to omrix_landing_full_dark.png")
    browser.close()

os._exit(0)
