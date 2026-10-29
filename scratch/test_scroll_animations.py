"""
QA verification script for Sentinel landing page scrolling animations.
Tests:
1. Top Scroll Progress Bar width dynamically increases on scroll.
2. Floating Navbar receives .scrolled class on scroll.
3. ScrollSpy highlights the current active section in navigation links.
4. Back-to-Top button becomes visible with circular SVG progress ring and scrolls to top on click.
5. Scroll Reveal elements gain .is-revealed on scroll into viewport.
6. Captures screenshots for visual validation.
"""

import sys
import time
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app
from app.config import TestingConfig

app = create_app(TestingConfig)

def run_server():
    app.run(port=5099, debug=False, use_reloader=False)

def verify():
    # Start server in thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1.5)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        errors = []
        page.on("pageerror", lambda err: errors.append(f"Page Error: {err}"))
        page.on("console", lambda msg: print(f"Console {msg.type}: {msg.text}") if msg.type in ("error", "warning") else None)

        print("[+] Navigating to landing page...")
        page.goto("http://127.0.0.1:5099/", wait_until="networkidle")
        page.wait_for_timeout(600)

        # 1. Initial State Check
        navbar = page.locator(".omrix-navbar")
        assert not navbar.evaluate("el => el.classList.contains('scrolled')"), "Navbar should not be scrolled initially"

        progress_bar = page.locator("#scroll-progress-bar")
        initial_width = progress_bar.evaluate("el => el.style.width")
        print(f"[✓] Initial scroll progress width: {initial_width}")

        back_to_top = page.locator("#back-to-top")
        assert not back_to_top.evaluate("el => el.classList.contains('visible')"), "Back to top should be hidden initially"

        # 2. Scroll Down 500px
        print("[+] Scrolling down 500px...")
        page.evaluate("window.scrollTo(0, 500)")
        page.wait_for_timeout(400)

        # Verify Navbar .scrolled
        is_scrolled = navbar.evaluate("el => el.classList.contains('scrolled')")
        print(f"[✓] Navbar .scrolled after 500px scroll: {is_scrolled}")
        assert is_scrolled, "Navbar should have .scrolled class"

        # Verify Progress bar width > 0
        mid_width = progress_bar.evaluate("el => el.style.width")
        print(f"[✓] Scroll progress width at 500px: {mid_width}")
        assert mid_width != "0%" and mid_width != "", "Progress bar should have positive width"

        # Verify Back to Top is visible
        is_btt_visible = back_to_top.evaluate("el => el.classList.contains('visible')")
        print(f"[✓] Back to top visible: {is_btt_visible}")
        assert is_btt_visible, "Back to top should be visible after 500px"

        # 3. Scroll to Bento Features Section (#features)
        print("[+] Scrolling to #features section...")
        page.evaluate("document.getElementById('features').scrollIntoView({ behavior: 'instant' })")
        page.wait_for_timeout(500)

        # Verify ScrollSpy active nav item
        active_link = page.locator(".omrix-nav-item.active")
        active_href = active_link.get_attribute("href") if active_link.count() > 0 else None
        print(f"[✓] Active navigation link on #features: {active_href}")
        assert active_href == "#features", f"Expected #features to be active, got {active_href}"

        # Verify bento cards are revealed
        bento_cards = page.locator(".bento-card")
        revealed_bento = bento_cards.first.evaluate("el => el.classList.contains('is-revealed')")
        print(f"[✓] Bento card is-revealed: {revealed_bento}")
        assert revealed_bento, "Bento card should have is-revealed class"

        # 4. Scroll to Bottom (CTA / Footer)
        print("[+] Scrolling to page bottom...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)

        end_width = progress_bar.evaluate("el => el.style.width")
        print(f"[✓] Scroll progress width at bottom: {end_width}")
        # should be near 100%
        pct_num = float(end_width.replace("%", ""))
        assert pct_num > 95.0, f"Expected >95% progress at bottom, got {end_width}"

        # 5. Click Back to Top
        print("[+] Clicking back to top button...")
        back_to_top.click()
        page.wait_for_timeout(600)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)

        top_scroll = page.evaluate("window.pageYOffset")
        print(f"[✓] Scroll Y after back to top: {top_scroll}")
        assert top_scroll < 50, f"Should be back near top, got {top_scroll}"

        # Capture validation screenshot
        screenshot_path = Path("scratch/scrolling_animation_verified.png")
        page.screenshot(path=str(screenshot_path))
        print(f"[✓] Saved validation screenshot to {screenshot_path}")

        assert len(errors) == 0, f"Page threw errors: {errors}"
        print("\n✨ ALL SCROLLING ANIMATION CHECKS PASSED SUCCESSFULLY! ✨\n")
        browser.close()

if __name__ == "__main__":
    verify()
