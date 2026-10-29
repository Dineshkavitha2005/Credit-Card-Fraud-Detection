import os, sys
sys.path.insert(0, os.path.abspath('.'))
from app import create_app

app = create_app()
with app.test_client() as client:
    res = client.get('/', follow_redirects=False)
    html = res.data.decode('utf-8')
    checks = [
        ('res.status_code == 200', res.status_code == 200),
        ('Intelligent Fraud Defense or Sentinel in html', ('Intelligent Fraud Defense' in html or 'Sentinel' in html)),
        ('Real-Time Transaction Surveillance in html', ('Real-Time Transaction Surveillance' in html)),
        ('<h1 in html', ('<h1' in html)),
        ('class="hero" in html', ('class="hero"' in html)),
        ('/login in html', ('/login' in html)),
        ('/register in html', ('/register' in html)),
    ]
    for name, val in checks:
        print(f"[{'PASS' if val else 'FAIL'}] {name}")
