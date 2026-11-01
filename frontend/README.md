# 🎨 Sentinel Frontend Architecture

The **Sentinel** frontend provides an enterprise-grade user interface for fraud monitoring, risk intelligence, transaction simulation, and system administration. It is built with semantic HTML5, CSS custom properties (design tokens), Vanilla JavaScript (no heavy frontend frameworks required), and Jinja2 templates.

---

## 📁 Directory Structure

```text
frontend/
├── static/
│   ├── css/
│   │   ├── landing.css          # High-performance landing & marketing styles (strict 3-color palette)
│   │   ├── sentinel.css         # Application core stylesheet & design tokens
│   │   └── ui-states.css        # Interactive UI micro-interactions & feedback states
│   ├── js/
│   │   ├── landing-motion.js    # Canvas particle graph & hero interaction animations
│   │   ├── sentinel.js          # Core client library (theme engine, cancellable fetch, modals)
│   │   └── ui-states.js         # Alert banners, toast notifications, button loading spinners
│   ├── img/
│   │   ├── favicon.svg          # Vector SVG brand shield
│   │   ├── favicon-16x16.png    # High-DPI browser favicon
│   │   ├── favicon-32x32.png    # Retina browser favicon
│   │   ├── apple-touch-icon.png # iOS home screen icon
│   │   ├── sentinel-logo.png    # Primary brand mark
│   │   ├── sentinel-og.webp     # OpenGraph / social preview
│   │   └── dashboard-preview.webp # Interactive product preview
│   └── site.webmanifest         # Progressive Web Application manifest
│
└── templates/                   # Jinja2 HTML Templates
    ├── base.html                # Authenticated application master layout
    ├── public_base.html         # Public marketing & SEO master layout
    ├── landing.html             # High-conversion product landing page
    ├── dashboard.html           # Executive fraud monitoring cockpit
    ├── transactions.html        # Live transaction ledger & simulation engine
    ├── analytics.html           # Risk distribution, metrics & timeline charts
    ├── reports.html             # Audit & compliance report generation (PDF/CSV)
    ├── cards.html               # Cardholder security & instant card lock
    ├── alerts.html              # High-risk transaction alert manager
    ├── login.html               # Multi-factor authentication login
    ├── register.html            # User account registration
    ├── settings.html            # User preferences & appearance controls
    ├── profile.html             # Account profile & credentials
    ├── admin_users.html         # User administration & role management
    ├── admin_audit_logs.html    # Tamper-evident security audit trail
    ├── error.html               # Standardized error presentation
    ├── 404.html                 # Brand-aligned not found page
    ├── message.html             # Flash notification renderer
    ├── privacy.html             # Enterprise privacy disclosure
    ├── terms.html               # Terms of service
    ├── forgot_password.html     # Password recovery workflow
    ├── reset_password.html      # Secure password reset token intake
    └── seo_*.html               # Content-rich SEO informational pages
```

---

## 🎨 Design System & Color Tokens

Sentinel strictly enforces a cohesive color system defined via CSS custom properties in `static/css/sentinel.css` and `static/css/landing.css`:

| Token | Light Theme | Dark Theme | Purpose |
| :--- | :--- | :--- | :--- |
| `--bg-app` | `#f8fafc` | `#0b0f19` | Application canvas background |
| `--bg-surface` | `#ffffff` | `#111827` | Cards, panels, modal dialogs |
| `--text-primary` | `#0f172a` | `#f9fafb` | Primary headings and prominent text |
| `--text-secondary`| `#64748b` | `#9ca3af` | Supporting text, captions, timestamps |
| `--brand-primary` | `#2563eb` | `#3b82f6` | Primary buttons, active tabs, brand accents |
| `--border-color` | `#e2e8f0` | `#1f2937` | Dividers, table borders, card outlines |

### Strict 3-Color Landing Palette
The public landing page adheres to an ultra-clean **3-color palette**:
1. **White** (`#FFFFFF`): Clarity, typography contrast, clean cards
2. **Deep Navy** (`#0F172A`): Security, institutional stability, dark surface
3. **Sentinel Blue** (`#2563EB`): Trust, active calls to action, brand recognition

---

## 🌓 System-Aware Theme Engine

The theme engine (`static/js/sentinel.js`) provides seamless Light, Dark, and System modes:
- **Instant FOUC Prevention**: Inline bootstrap script in `<head>` applies the cached or system preference before paint.
- **Dynamic OS Listener**: In System mode, listening to `window.matchMedia('(prefers-color-scheme: dark)')` updates theme in real time when OS appearance toggles.
- **Persisted User Choice**: Manual override is saved to `localStorage.getItem('sentinel_theme_preference')`.

---

## ⚡ Asynchronous Fetch & Cancellation

Sentinel includes an integrated request manager (`cancellableFetch`) using standard `AbortController`:
- **Auto-cancellation**: In-flight filter and search requests are automatically aborted when new filters are applied.
- **Safari/WebKit Resilience**: Gracefully differentiates between intentional aborts (`AbortError` or Safari's `TypeError: Load failed`) and genuine network drops.
- **Sequence Guards**: Monotonic sequence numbers prevent out-of-order race conditions from overwriting fresh table data.

