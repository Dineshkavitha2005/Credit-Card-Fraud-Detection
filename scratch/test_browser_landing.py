"""
Playwright Browser QA Script for Sentinel Redesigned Landing Page
Tests all 14 sections, interactions (scenarios, tabs, FAQ, theme, drawer),
responsive viewports (1440, 768, 375), and captures high-res screenshots.
"""

import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
from pathlib import Path
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = Path(r"C:\Users\Dinesh A\.gemini\antigravity-ide\brain\0eaa8e7e-70da-417c-8cef-243d4a7f15fa")
BASE_URL = "http://127.0.0.1:5001"

def run_qa():
    print("[+] Starting Sentinel Browser QA with Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        errors = []
        page.on("pageerror", lambda err: errors.append(f"Page Error: {err}"))
        page.on("console", lambda msg: print(f"  [Console {msg.type}]: {msg.text}") if msg.type == "error" else None)

        # 1. Load Page
        print(f"[+] Navigating to {BASE_URL} at 1440x900...")
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Verify Title & Meta
        title = page.title()
        print(f"[✓] Page Title: {title}")
        assert "Sentinel" in title, "Title missing Sentinel"

        # 2. Hero & Status Strip
        hero = page.locator("#hero")
        hero.screenshot(path=str(ARTIFACT_DIR / "hero_light.png"))
        print("[✓] Saved hero_light.png")

        status_strip = page.locator(".status-strip-section")
        status_strip.screenshot(path=str(ARTIFACT_DIR / "status_strip.png"))
        print("[✓] Saved status_strip.png")

        # 3. Problem Section
        problem = page.locator("#problem")
        problem.screenshot(path=str(ARTIFACT_DIR / "problem_section.png"))
        print("[✓] Saved problem_section.png")

        # 4. How Sentinel Works (Alternating 3-step section)
        how_it_works = page.locator("#how-it-works")
        how_it_works.screenshot(path=str(ARTIFACT_DIR / "how_it_works.png"))
        print("[✓] Saved how_it_works.png")

        # 5. Live Detection Workbench Interactions
        print("[+] Testing Workbench Scenario toggles...")
        # Scenario B: Credential Stuffing
        btn_b = page.locator("button[data-scenario='stuffing']")
        btn_b.click()
        page.wait_for_timeout(400)
        amount_text = page.locator("#wb-amount").inner_text()
        print(f"  Scenario B amount: {amount_text}")
        assert "99" in amount_text, f"Expected 99 in amount, got {amount_text}"

        # Scenario C: Verified Cardholder
        btn_c = page.locator("button[data-scenario='legitimate']")
        btn_c.click()
        page.wait_for_timeout(400)
        decision_text = page.locator("#wb-decision").inner_text()
        print(f"  Scenario C decision: {decision_text}")
        assert "ALLOW" in decision_text, f"Expected ALLOW, got {decision_text}"

        # Scenario A: Velocity Surge
        btn_a = page.locator("button[data-scenario='velocity']")
        btn_a.click()
        page.wait_for_timeout(400)
        decision_a = page.locator("#wb-decision").inner_text()
        print(f"  Scenario A decision: {decision_a}")
        assert "BLOCK" in decision_a, f"Expected BLOCK, got {decision_a}"

        workbench = page.locator("#live-detection")
        workbench.screenshot(path=str(ARTIFACT_DIR / "workbench_scenario.png"))
        print("[✓] Saved workbench_scenario.png")

        # 6. Detection Pipeline
        pipeline = page.locator("#platform")
        pipeline.screenshot(path=str(ARTIFACT_DIR / "detection_pipeline.png"))
        print("[✓] Saved detection_pipeline.png")

        # 7. Risk Explainability
        explainability = page.locator("#explainability")
        explainability.screenshot(path=str(ARTIFACT_DIR / "risk_explainability.png"))
        print("[✓] Saved risk_explainability.png")

        # 8. Security Architecture
        security = page.locator("#security")
        security.screenshot(path=str(ARTIFACT_DIR / "security_architecture.png"))
        print("[✓] Saved security_architecture.png")

        # 9. Audit Trail
        audit = page.locator("#audit")
        audit.screenshot(path=str(ARTIFACT_DIR / "audit_trail.png"))
        print("[✓] Saved audit_trail.png")

        # 10. Console Showcase Tabs
        print("[+] Testing Console Showcase tabs...")
        page.locator(".console-tab[data-tab='transactions']").click()
        page.wait_for_timeout(200)
        page.locator(".console-tab[data-tab='alerts']").click()
        page.wait_for_timeout(200)
        page.locator(".console-tab[data-tab='overview']").click()
        page.wait_for_timeout(200)

        console_el = page.locator("#product-console")
        console_el.screenshot(path=str(ARTIFACT_DIR / "console_showcase.png"))
        print("[✓] Saved console_showcase.png")

        # 11. Engineering Bento Grid
        bento = page.locator("#engineering")
        bento.screenshot(path=str(ARTIFACT_DIR / "engineering_bento.png"))
        print("[✓] Saved engineering_bento.png")

        # 12. FAQ Accordion Interaction
        print("[+] Testing FAQ Accordion...")
        faq_btn_1 = page.locator("#faq-btn-1")
        faq_ans_1 = page.locator("#faq-ans-1")
        faq_btn_1.click()
        page.wait_for_timeout(350)
        assert "open" in (faq_ans_1.get_attribute("class") or ""), "FAQ 1 failed to open"

        faq_btn_2 = page.locator("#faq-btn-2")
        faq_ans_2 = page.locator("#faq-ans-2")
        faq_btn_2.click()
        page.wait_for_timeout(350)
        assert "open" in (faq_ans_2.get_attribute("class") or ""), "FAQ 2 failed to open"
        assert "open" not in (faq_ans_1.get_attribute("class") or ""), "FAQ 1 failed to close when FAQ 2 opened"

        faq_el = page.locator("#faq")
        faq_el.screenshot(path=str(ARTIFACT_DIR / "faq_accordion_open.png"))
        print("[✓] Saved faq_accordion_open.png")

        # 13. Final CTA & Footer
        cta_footer = page.locator(".deployment-cta-section")
        cta_footer.screenshot(path=str(ARTIFACT_DIR / "final_cta.png"))
        print("[✓] Saved final_cta.png")

        # 14. Theme Switcher (Dark Mode)
        print("[+] Testing Theme Switcher to Dark Mode...")
        theme_toggle = page.locator(".theme-toggle-btn").first
        theme_toggle.click()
        page.wait_for_timeout(500)
        data_theme = page.locator("html").get_attribute("data-theme")
        print(f"  data-theme attribute: {data_theme}")
        assert data_theme == "dark", f"Expected data-theme='dark', got {data_theme}"

        hero.screenshot(path=str(ARTIFACT_DIR / "hero_dark.png"))
        bento.screenshot(path=str(ARTIFACT_DIR / "bento_dark.png"))
        print("[✓] Saved hero_dark.png and bento_dark.png")

        # Switch back to light
        theme_toggle.click() # to system
        page.wait_for_timeout(200)
        theme_toggle.click() # to light
        page.wait_for_timeout(300)

        # 15. Mobile Viewport (375x812)
        print("[+] Testing Mobile Viewport (375x812)...")
        page.set_viewport_size({"width": 375, "height": 812})
        page.wait_for_timeout(500)

        # Verify no horizontal scroll
        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        inner_width = page.evaluate("() => window.innerWidth")
        print(f"  Mobile scrollWidth: {scroll_width}, innerWidth: {inner_width}")
        assert scroll_width <= inner_width, f"Horizontal overflow detected on mobile: {scroll_width} > {inner_width}"

        page.screenshot(path=str(ARTIFACT_DIR / "mobile_view.png"), full_page=False)
        print("[✓] Saved mobile_view.png")

        # Test Mobile Menu Drawer
        print("[+] Testing Mobile Navigation Drawer...")
        menu_btn = page.locator("#mobile-menu-btn")
        menu_btn.click()
        page.wait_for_timeout(400)

        drawer = page.locator("#mobile-nav-drawer")
        assert "open" in (drawer.get_attribute("class") or ""), "Mobile drawer failed to open"
        page.screenshot(path=str(ARTIFACT_DIR / "mobile_drawer_open.png"))
        print("[✓] Saved mobile_drawer_open.png")

        # Test Escape key closes drawer
        page.keyboard.press("Escape")
        page.wait_for_timeout(350)
        assert "open" not in (drawer.get_attribute("class") or ""), "Escape key failed to close drawer"
        print("[✓] Escape key successfully closed mobile drawer")

        # 16. Tablet Viewport (768x1024)
        print("[+] Testing Tablet Viewport (768x1024)...")
        page.set_viewport_size({"width": 768, "height": 1024})
        page.wait_for_timeout(400)
        page.screenshot(path=str(ARTIFACT_DIR / "tablet_view.png"))
        print("[✓] Saved tablet_view.png")

        browser.close()
        print("\n========================================================")
        print("BROWSER QA COMPLETED SUCCESSFULLY! ALL CHECKS PASSED!")
        print("========================================================")

if __name__ == "__main__":
    run_qa()
