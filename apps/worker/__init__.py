"""
CadOwl Async Worker
===================

Runs long-lived background jobs that shouldn't block the API thread:
- DXF parsing
- PDF rendering
- ML inference
- Bulk import processing
- Periodic Saone/Grafana sync

Uses Arq (Redis-backed) for queue management.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""
