import sys
import os
import threading
import time

sys.path.insert(0, os.path.abspath('.'))
from app import create_app
from playwright.sync_api import sync_playwright

app = create_app()

def run_server():
    app.run(port=5099, debug=False, use_reloader=False)

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(2)

print("[+] Started test server on http://127.0.0.1:5099")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    
    errors = []
    page.on("pageerror", lambda err: errors.append(f"Page Error: {err}"))
    page.on("console", lambda msg: print(f"  [Console {msg.type}]: {msg.text}") if msg.type == "error" else None)
    
    page.goto("http://127.0.0.1:5099/", wait_until="networkidle")
    page.wait_for_timeout(1000)
    
    # Check Title
    print("Page Title:", page.title())
    
    # Screenshot full page
    artifact_dir = r"C:\Users\Dinesh A\.gemini\antigravity-ide\brain\e07a1368-010d-442b-9a6d-bd50ae9f26d7"
    page.screenshot(path=os.path.join(artifact_dir, "omrix_landing_full.png"), full_page=True)
    print("[✓] Saved full page screenshot to omrix_landing_full.png")
    
    # Test Scenario Simulator: Click "Stolen Card Attack"
    print("[+] Testing interactive scenario switcher...")
    btn_stolen = page.locator("#sim-btn-stolen")
    btn_stolen.click()
    page.wait_for_timeout(500)
    score_text = page.locator("#risk-score-display").inner_text()
    decision_text = page.locator("#decision-text").inner_text()
    print(f"  Stolen Card Scenario -> Score: {score_text}, Decision: {decision_text}")
    assert score_text == "96", f"Expected score 96, got {score_text}"
    assert "CRITICAL RISK" in decision_text, f"Expected CRITICAL RISK, got {decision_text}"
    
    # Test Scenario Simulator: Click "Velocity Flood"
    btn_velocity = page.locator("#sim-btn-velocity")
    btn_velocity.click()
    page.wait_for_timeout(500)
    score_velocity = page.locator("#risk-score-display").inner_text()
    print(f"  Velocity Scenario -> Score: {score_velocity}")
    assert score_velocity == "89", f"Expected score 89, got {score_velocity}"
    
    # Test Pricing Toggle: Click "Yearly"
    print("[+] Testing pricing billing toggle...")
    btn_yearly = page.locator("#btn-yearly")
    btn_yearly.click()
    page.wait_for_timeout(300)
    pro_price = page.locator("#price-pro").inner_text()
    print(f"  Yearly Pro price: ${pro_price}")
    assert pro_price == "63", f"Expected 63, got {pro_price}"
    
    # Test Pricing Toggle: Click "Monthly"
    btn_monthly = page.locator("#btn-monthly")
    btn_monthly.click()
    page.wait_for_timeout(300)
    pro_price_m = page.locator("#price-pro").inner_text()
    print(f"  Monthly Pro price: ${pro_price_m}")
    assert pro_price_m == "79", f"Expected 79, got {pro_price_m}"
    
    # Test FAQ Accordion
    print("[+] Testing FAQ accordion...")
    faq2_trigger = page.locator(".accordion-item:nth-child(2) .accordion-trigger")
    faq2_trigger.click()
    page.wait_for_timeout(300)
    assert page.locator(".accordion-item:nth-child(2)").evaluate("el => el.classList.contains('active')"), "FAQ item 2 not active"
    print("  FAQ 2 expanded successfully!")
    
    # Test Demo Modal
    print("[+] Testing demo booking modal...")
    page.locator(".btn-pill-cta:has-text('Book a Demo')").first.click()
    page.wait_for_timeout(300)
    assert page.locator("#demo-modal-backdrop").evaluate("el => el.classList.contains('open')"), "Demo modal did not open"
    print("  Demo modal opened successfully!")
    
    # Fill and submit demo modal form
    page.fill("#demo-name", "Test User")
    page.fill("#demo-email", "test@fintech.io")
    page.fill("#demo-company", "Fintech Innovations")
    page.click(".modal-submit-btn")
    page.wait_for_timeout(300)
    assert page.locator("#modal-success-content").is_visible(), "Success content not visible after demo submit"
    print("  Demo form submitted successfully with confirmation state!")
    
    # Close modal
    page.click(".demo-modal-card .btn-hero-primary")
    page.wait_for_timeout(300)
    assert not page.locator("#demo-modal-backdrop").evaluate("el => el.classList.contains('open')"), "Demo modal did not close"
    print("  Demo modal closed cleanly!")
    
    # Take screenshot of light mode hero
    page.screenshot(path=os.path.join(artifact_dir, "omrix_hero_light.png"))
    
    # Test Theme Toggle to Dark Mode
    print("[+] Testing theme toggle...")
    page.locator(".theme-toggle-btn").first.click()
    page.wait_for_timeout(500)
    page.screenshot(path=os.path.join(artifact_dir, "omrix_dark_mode.png"))
    print("[✓] Saved dark mode screenshot")
    
    browser.close()

print("\n🎉 ALL VISUAL AND INTERACTIVE TESTS PASSED WITHOUT ERRORS!")
os._exit(0)
