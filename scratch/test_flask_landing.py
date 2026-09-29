import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from app import create_app

app = create_app()

with app.test_client() as client:
    resp = client.get('/')
    print("GET / Status Code:", resp.status_code)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    
    html = resp.get_data(as_text=True)
    print("Page length:", len(html))
    
    # Check essential section headings and contents
    assert "Stop Card Fraud" in html, "Missing Hero title"
    assert "From swipe to prevention in three steps" in html, "Missing How It Works title"
    assert "Built for speed. Designed for scale." in html, "Missing Bento title"
    assert "Start free. Scale without limits." in html, "Missing Pricing title"
    assert "Everything you need to know." in html, "Missing FAQ title"
    assert "Learn, build, and grow with Sentinel." in html, "Missing Resources title"
    assert "Your revenue deserves bulletproof protection." in html, "Missing CTA Banner title"
    assert "sim-btn-normal" in html, "Missing simulation button"
    assert "btn-yearly" in html, "Missing yearly toggle button"
    assert "demo-modal-backdrop" in html, "Missing demo modal"
    assert "mobile-nav-drawer" in html, "Missing mobile drawer"
    
    print("\n[SUCCESS] All sections and interactive elements verified in rendered landing HTML!")
