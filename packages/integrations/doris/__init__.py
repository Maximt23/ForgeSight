"""
Doris store metadata integration.

Wraps Walmart's internal Doris store database. Read-only.
Cache-aware, retry-aware, structured-logged.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from .client import DorisClient, DorisStore, get_doris_client

__all__ = ["DorisClient", "DorisStore", "get_doris_client"]
