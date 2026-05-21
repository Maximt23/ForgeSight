"""
Pytest configuration shared across all tests.

Sets up the test environment BEFORE any application module is imported.
The auth module reads `CADOWL_DEV_MODE` at class-definition time, so this
file must run before any `from apps...` import in the test suite.
"""

import os

# ─── MUST come before any apps.* import ────────────────────────────────
# Force dev-mode auth bypass for tests. Real auth is tested separately
# in tests/integration/test_auth.py with explicit env-var overrides.
os.environ.setdefault("CADOWL_DEV_MODE", "true")
os.environ.setdefault("CADOWL_DEV_USER", "test.user@walmart.com")

# Use in-memory / temp data for tests
os.environ.setdefault("LOG_LEVEL", "WARNING")  # quiet tests
