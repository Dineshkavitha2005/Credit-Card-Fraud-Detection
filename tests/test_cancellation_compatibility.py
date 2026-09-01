"""
Automated Regression Test Suite for Sentinel Asynchronous Fetch & Cancellation Resilience
Tests AbortController integration, Safari/WebKit TypeError: "Load failed" compatibility,
monotonic request sequencing, memory management, and genuine network error preservation.
"""

import os
import re
import subprocess
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
STATIC_JS_DIR = os.path.join(ROOT_DIR, 'static', 'js')
TEMPLATES_DIR = os.path.join(ROOT_DIR, 'templates')


class TestSentinelCancellationCompatibility:
    """Verify frontend asynchronous fetch handling and AbortController architecture."""

    def test_sentinel_js_exports_cancellation_api(self):
        """Ensure sentinel.js implements and exports cancellableFetch, isAbortError, abortRequests, abortAllRequests, isLatest."""
        sentinel_path = os.path.join(STATIC_JS_DIR, 'sentinel.js')
        assert os.path.exists(sentinel_path), f"sentinel.js missing: {sentinel_path}"

        with open(sentinel_path, 'r', encoding='utf-8') as f:
            js = f.read()

        # Check function declarations
        assert 'function isAbortError' in js, "isAbortError function missing in sentinel.js"
        assert 'function abortRequests' in js, "abortRequests function missing in sentinel.js"
        assert 'function abortAllRequests' in js, "abortAllRequests function missing in sentinel.js"
        assert 'function isLatest' in js, "isLatest function missing in sentinel.js"
        assert 'async function cancellableFetch' in js, "cancellableFetch function missing in sentinel.js"

        # Check export return object
        return_match = re.search(r'return\s*\{([^}]+)\};', js)
        assert return_match is not None, "Sentinel return export object not found in sentinel.js"
        exports = return_match.group(1)

        assert 'isAbortError' in exports, "isAbortError must be exported from Sentinel"
        assert 'abortRequests' in exports, "abortRequests must be exported from Sentinel"
        assert 'abortAllRequests' in exports, "abortAllRequests must be exported from Sentinel"
        assert 'cancellableFetch' in exports, "cancellableFetch must be exported from Sentinel"
        assert 'isLatest' in exports, "isLatest must be exported from Sentinel"

    def test_safari_webkit_quirks_and_genuine_error_preservation(self):
        """Verify isAbortError accounts for Safari/WebKit quirks while preserving genuine network failures."""
        sentinel_path = os.path.join(STATIC_JS_DIR, 'sentinel.js')
        with open(sentinel_path, 'r', encoding='utf-8') as f:
            js = f.read()

        fn_match = re.search(r'function isAbortError\s*\([^)]*\)\s*\{([\s\S]*?)\n  \}', js)
        assert fn_match is not None, "isAbortError body not found"
        body = fn_match.group(1)

        # Standard AbortError check
        assert "err.name === 'AbortError'" in body or 'err.name == "AbortError"' in body
        # DOMException code 20 check
        assert 'err.code === 20' in body or 'err.code == 20' in body
        # Safari/WebKit TypeError: "Load failed" when signal is aborted
        assert 'signal' in body and 'aborted' in body
        assert 'load failed' in body.lower()
        # Must NOT unconditionally treat TypeError as abort when signal is NOT aborted
        assert "signal.aborted" in body or "(signal && signal.aborted)" in body

    def test_navigation_and_drawer_teardown_listeners(self):
        """Verify teardown event listeners abort in-flight requests on page navigation and drawer closure."""
        sentinel_path = os.path.join(STATIC_JS_DIR, 'sentinel.js')
        with open(sentinel_path, 'r', encoding='utf-8') as f:
            js = f.read()

        assert 'beforeunload' in js, "beforeunload listener missing in sentinel.js"
        assert 'pagehide' in js, "pagehide listener missing in sentinel.js"
        assert "abortRequests('drawer-detail')" in js or 'abortRequests("drawer-detail")' in js, (
            "closeDrawer must abort drawer-detail requests"
        )

    def test_ui_states_api_call_abort_resilience(self):
        """Verify UIState.apiCall forwards abort signals, clears slow timers, and suppresses error toasts on abort."""
        ui_states_path = os.path.join(STATIC_JS_DIR, 'ui-states.js')
        with open(ui_states_path, 'r', encoding='utf-8') as f:
            js = f.read()

        api_call_match = re.search(r'async apiCall\s*\([^)]*\)\s*\{([\s\S]*?)\n        \},', js)
        assert api_call_match is not None, "apiCall method not found in ui-states.js"
        body = api_call_match.group(1)

        assert 'isAbortError' in body or 'options.signal' in body
        assert 'clearTimeout(slowTimer)' in body, "apiCall catch block must clear slow timer"

    @pytest.mark.parametrize("template_name,expected_key", [
        ("dashboard.html", "dashboard-overview"),
        ("transactions.html", "transactions-list"),
        ("analytics.html", "analytics-overview"),
        ("alerts.html", "alerts-list"),
        ("cards.html", "cards-list"),
        ("reports.html", "reports-list"),
        ("admin_users.html", "admin-users-list"),
        ("admin_audit_logs.html", "admin-audit-logs"),
        ("settings.html", "fraud-rules-list"),
    ])
    def test_templates_use_cancellable_fetch_and_handle_aborts(self, template_name, expected_key):
        """Verify all major data-fetching views use Sentinel.cancellableFetch and Sentinel.isAbortError."""
        template_path = os.path.join(TEMPLATES_DIR, template_name)
        assert os.path.exists(template_path), f"Template missing: {template_path}"

        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()

        assert f"Sentinel.cancellableFetch('{expected_key}'" in html or f'Sentinel.cancellableFetch("{expected_key}"' in html, (
            f"{template_name} must invoke Sentinel.cancellableFetch with key '{expected_key}'"
        )
        assert 'Sentinel.isAbortError' in html, (
            f"{template_name} catch block must check Sentinel.isAbortError to suppress false error banners"
        )
        assert f"Sentinel.isLatest('{expected_key}'" in html or f'Sentinel.isLatest("{expected_key}"' in html, (
            f"{template_name} must check Sentinel.isLatest to prevent race condition overwrites"
        )

    def test_node_simulation_suite_execution(self):
        """Execute the Node.js headless environment test suite to verify runtime behavior."""
        node_test_script = os.path.join(ROOT_DIR, 'tests', 'test_cancellation_node.js')
        assert os.path.exists(node_test_script), f"Node test script missing: {node_test_script}"

        result = subprocess.run(
            ['node', node_test_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"Node.js cancellation test suite failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        assert "ALL NODE TESTS PASSED" in result.stdout, "Node test suite did not complete successfully"
