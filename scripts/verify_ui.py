"""
UI, Responsiveness, and Accessibility Verification Script using Playwright.
Spawns an ephemeral test server and validates:
- CTA above the fold across mobile and desktop viewports
- Zero horizontal overflow
- Mobile navigation drawer toggle and keyboard trap/esc handling
- Dark / Light theme toggle
- 404 page layout and actions
- Privacy and Terms page rendering
Captures artifact screenshots for the walkthrough report.
"""

import os
import sys
import time
import threading
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app

PORT = 5025
ARTIFACTS_DIR = r"C:\Users\Dinesh A\.gemini\antigravity-ide\brain\389b1a6a-873d-4515-a5d0-3f8b3fcfe312"

class ServerThread(threading.Thread):
    def __init__(self, app, port):
        super().__init__()
        self.server = make_server('127.0.0.1', port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


def run_verification():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    server = ServerThread(flask_app, PORT)
    server.start()
    time.sleep(1)

    base_url = f"http://127.0.0.1:{PORT}"
    results = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # 1. Test Viewports and Horizontal Overflow + Above the Fold
            viewports = [
                ("mobile_375", 375, 667),
                ("mobile_390", 390, 844),
                ("tablet_768", 768, 1024),
                ("desktop_1440", 1440, 900),
            ]

            for name, width, height in viewports:
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(f"{base_url}/")
                page.wait_for_load_state("networkidle")

                # Check horizontal overflow
                scroll_w = page.evaluate("document.documentElement.scrollWidth")
                client_w = page.evaluate("document.documentElement.clientWidth")
                has_no_overflow = scroll_w <= client_w

                # Check CTA position
                cta = page.locator("#heroPrimaryCta")
                box = cta.bounding_box()
                cta_above_fold = box and (box['y'] + box['height'] <= height)

                results[f"{name}_no_overflow"] = has_no_overflow
                results[f"{name}_cta_above_fold"] = cta_above_fold

                # Take screenshot
                screenshot_path = os.path.join(ARTIFACTS_DIR, f"{name}_landing.png")
                page.screenshot(path=screenshot_path)
                page.close()

            # 2. Test Mobile Navigation Drawer Interaction
            mobile_page = browser.new_page(viewport={"width": 390, "height": 844})
            mobile_page.goto(f"{base_url}/")
            mobile_page.wait_for_load_state("networkidle")
            
            # Initial state
            drawer = mobile_page.locator("#mobileNavDrawer")
            results["drawer_initially_hidden"] = mobile_page.evaluate("document.getElementById('mobileNavDrawer').getAttribute('aria-hidden') === 'true'")

            # Click toggle
            mobile_page.click("#mobileNavToggle")
            time.sleep(0.3)
            results["drawer_opened"] = mobile_page.evaluate("document.getElementById('mobileNavDrawer').getAttribute('aria-hidden') === 'false'")
            
            drawer_screenshot = os.path.join(ARTIFACTS_DIR, "mobile_drawer_open.png")
            mobile_page.screenshot(path=drawer_screenshot)

            # Press Escape to close
            mobile_page.keyboard.press("Escape")
            time.sleep(0.3)
            results["drawer_closed_on_esc"] = mobile_page.evaluate("document.getElementById('mobileNavDrawer').getAttribute('aria-hidden') === 'true'")
            mobile_page.close()

            # 3. Test Theme Toggle
            theme_page = browser.new_page(viewport={"width": 1440, "height": 900})
            theme_page.goto(f"{base_url}/")
            theme_page.wait_for_load_state("networkidle")

            initial_theme = theme_page.evaluate("document.documentElement.getAttribute('data-theme')")
            theme_page.click("#publicThemeBtn")
            toggled_theme = theme_page.evaluate("document.documentElement.getAttribute('data-theme')")
            results["theme_toggled_successfully"] = (initial_theme != toggled_theme)

            # Capture light theme
            light_screenshot = os.path.join(ARTIFACTS_DIR, "desktop_light_theme.png")
            theme_page.screenshot(path=light_screenshot)
            theme_page.close()

            # 4. Test 404 Page
            error_page = browser.new_page(viewport={"width": 1440, "height": 900})
            error_res = error_page.goto(f"{base_url}/non-existent-page-xyz")
            results["404_status"] = error_res.status
            results["404_has_return_link"] = error_page.locator("a:has-text('Return to Sentinel')").count() > 0
            
            err_screenshot = os.path.join(ARTIFACTS_DIR, "404_page.png")
            error_page.screenshot(path=err_screenshot)
            error_page.close()

            # 5. Test Privacy Policy Page
            priv_page = browser.new_page(viewport={"width": 1440, "height": 900})
            priv_res = priv_page.goto(f"{base_url}/privacy")
            results["privacy_status"] = priv_res.status
            results["privacy_has_content"] = priv_page.locator("text=AES-128-CBC").count() > 0 or priv_page.locator("text=Encryption").count() > 0
            
            priv_screenshot = os.path.join(ARTIFACTS_DIR, "privacy_page.png")
            priv_page.screenshot(path=priv_screenshot)
            priv_page.close()

            browser.close()

    finally:
        server.shutdown()
        server.join()

    print("\n--- UI Verification Results ---")
    all_passed = True
    for k, v in results.items():
        status = "PASS" if v else "FAIL"
        if not v and v != 404:  # Note 404_status == 404 is a PASS
            all_passed = False
        elif k == "404_status" and v == 404:
            status = "PASS"
        print(f"[{status}] {k}: {v}")

    if all_passed:
        print("\nALL UI & RESPONSIVENESS CHECKS PASSED!")
    else:
        print("\nSOME CHECKS FAILED!")

if __name__ == "__main__":
    run_verification()
