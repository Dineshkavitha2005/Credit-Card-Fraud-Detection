import os
import re
import pytest

class TestResponsiveCompatibility:
    """Regression test suite verifying cross-browser and responsive CSS constraints."""

    def test_css_sentinel_main_flexbox_constraints(self):
        """Ensure .sentinel-main has min-width: 0 and max-width to prevent flexbox unconstrained overflow."""
        css_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'css', 'sentinel.css'))
        assert os.path.exists(css_path), f"CSS file missing: {css_path}"
        
        with open(css_path, 'r', encoding='utf-8') as f:
            css = f.read()

        main_match = re.search(r'\.sentinel-main\s*\{([^}]+)\}', css)
        assert main_match is not None, ".sentinel-main rule not found in sentinel.css"
        main_rules = main_match.group(1)

        assert 'min-width: 0' in main_rules or 'min-width:0' in main_rules, (
            ".sentinel-main must declare 'min-width: 0;' to permit flex child shrinking"
        )
        assert 'max-width:' in main_rules, (
            ".sentinel-main must declare max-width constraint to prevent document overflow"
        )

    def test_css_table_container_overflow_handling(self):
        """Ensure .data-table-container has horizontal scroll capability for wide tables."""
        css_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'css', 'sentinel.css'))
        with open(css_path, 'r', encoding='utf-8') as f:
            css = f.read()

        table_container_match = re.search(r'\.data-table-container\s*\{([^}]+)\}', css)
        assert table_container_match is not None, ".data-table-container rule not found"
        tc_rules = table_container_match.group(1)

        assert 'overflow-x: auto' in tc_rules or 'overflow-x:auto' in tc_rules, (
            ".data-table-container must declare overflow-x: auto to enable horizontal scrolling"
        )

    def test_css_mobile_media_queries_exist(self):
        """Verify responsive breakpoints for tablet (768px) and mobile (<= 560px) are configured."""
        css_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'css', 'sentinel.css'))
        with open(css_path, 'r', encoding='utf-8') as f:
            css = f.read()

        assert '@media (max-width: 768px)' in css or '@media(max-width:768px)' in css, (
            "Breakpoint @media (max-width: 768px) missing from sentinel.css"
        )
        assert '@media (max-width: 560px)' in css or '@media(max-width:560px)' in css, (
            "Compact mobile breakpoint @media (max-width: 560px) missing from sentinel.css"
        )

    def test_css_mobile_topbar_overflow_prevention(self):
        """Verify mobile topbar compacts status pill and breadcrumbs on ultra-compact viewports."""
        css_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'css', 'sentinel.css'))
        with open(css_path, 'r', encoding='utf-8') as f:
            css = f.read()

        mobile_mq = re.search(r'@media\s*\(\s*max-width:\s*560px\s*\)\s*\{([^}]+(\{[^}]*\}[^}]+)*)\}', css)
        assert mobile_mq is not None, "@media (max-width: 560px) block missing"
        mq_content = mobile_mq.group(1)

        assert '.system-status-indicator' in mq_content, (
            "Mobile media query must handle .system-status-indicator to avoid topbar overflow"
        )
