"""
Sentinel Backend Package
"""
import os
import sys

# Ensure backend root is discoverable
BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


def __getattr__(name):
    """
    Lazy export of app attributes to avoid circular imports during module loading.
    """
    import importlib
    app_module = importlib.import_module('app')
    if hasattr(app_module, name):
        return getattr(app_module, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
