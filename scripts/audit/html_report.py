"""
HTML report generator for audit results.

Produces a self-contained HTML file (no external deps) using
Walmart brand colors and Tailwind via CDN. Sortable, filterable
by severity, drill-down per check.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .types import CheckResult, Severity

# Walmart brand colors
_COLORS = {
    Severity.CRITICAL: ("#ea1100", "#fff", "🚨"),  # red.100
    Severity.ERROR: ("#ea1100", "#fff", "❌"),
    Severity.WARNING: ("#995213", "#fff7e6", "⚠️"),  # spark.140 / spark.10
    Severity.INFO: ("#0053e2", "#e6efff", "ℹ️"),  # blue.100
}


def _severity_badge(sev: Severity) -> str:
    bg, fg, icon = _COLORS[sev]
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:4px;font-size:12px;font-weight:600;">{icon} {sev.value.upper()}</span>'
    )


def _result_summary_row(result: CheckResult) -> str:
    by_sev = {sev.value: sum(1 for f in result.findings if f.severity == sev) for sev in Severity}
    status = "✅ PASS" if result.passed else "❌ FAIL"
    status_color = "#2a8703" if result.passed else "#ea1100"
    return f"""
    <tr>
      <td><a href="#check-{result.check}" style="color:#0053e2;font-weight:600;">{html.escape(result.check)}</a></td>
      <td style="color:{status_color};font-weight:600;">{status}</td>
      <td>{result.items_scanned:,}</td>
      <td>{result.duration_ms:.0f}ms</td>
      <td><span style="color:#ea1100;">{by_sev['critical']}</span></td>
      <td><span style="color:#ea1100;">{by_sev['error']}</span></td>
      <td><span style="color:#995213;">{by_sev['warning']}</span></td>
      <td><span style="color:#0053e2;">{by_sev['info']}</span></td>
    </tr>
    """


def _findings_table(findings: Iterable) -> str:
    rows = []
    for f in findings:
        location = ""
        if f.file:
            location = f"<code style='font-size:11px;color:#666;'>{html.escape(f.file)}"
            if f.line:
                location += f":{f.line}"
            location += "</code>"

        suggestion = ""
        if f.suggestion:
            suggestion = f'<div style="margin-top:4px;font-size:12px;color:#444;font-style:italic;">→ {html.escape(f.suggestion)}</div>'

        rows.append(f"""
        <tr class="finding finding-{f.severity.value}">
          <td>{_severity_badge(f.severity)}</td>
          <td>
            <div style="font-weight:600;">{html.escape(f.title)}</div>
            <div style="font-size:13px;color:#555;margin-top:2px;">{html.escape(f.detail[:300])}{('...' if len(f.detail) > 300 else '')}</div>
            {suggestion}
          </td>
          <td>{location}</td>
        </tr>
        """)
    return "".join(rows)


def render(results: list[CheckResult], output_path: Path) -> None:
    total_findings = sum(len(r.findings) for r in results)
    total_errors = sum(
        sum(1 for f in r.findings if f.severity in (Severity.ERROR, Severity.CRITICAL))
        for r in results
    )
    total_warnings = sum(
        sum(1 for f in r.findings if f.severity == Severity.WARNING) for r in results
    )
    total_info = sum(
        sum(1 for f in r.findings if f.severity == Severity.INFO) for r in results
    )
    all_passed = all(r.passed for r in results)
    overall_status = "✅ ALL CHECKS PASSED" if all_passed else "❌ AUDIT FAILED"
    overall_color = "#2a8703" if all_passed else "#ea1100"

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    summary_rows = "".join(_result_summary_row(r) for r in results)

    check_sections = []
    for r in results:
        if not r.findings and r.passed:
            section_body = '<p style="color:#2a8703;font-weight:600;">✅ No findings.</p>'
        else:
            section_body = f"""
            <table style="width:100%;border-collapse:collapse;">
              <thead style="background:#f5f5f5;">
                <tr>
                  <th style="text-align:left;padding:8px;width:120px;">Severity</th>
                  <th style="text-align:left;padding:8px;">Finding</th>
                  <th style="text-align:left;padding:8px;width:300px;">Location</th>
                </tr>
              </thead>
              <tbody>{_findings_table(r.findings)}</tbody>
            </table>
            """

        check_sections.append(f"""
        <section id="check-{r.check}" style="margin-top:32px;background:white;padding:24px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
          <h2 style="margin:0 0 8px 0;color:#0053e2;">📋 {html.escape(r.check)}</h2>
          <p style="color:#666;margin:0 0 16px 0;font-size:14px;">
            Scanned {r.items_scanned:,} items in {r.duration_ms:.0f}ms · {len(r.findings)} finding(s)
          </p>
          {section_body}
        </section>
        """)

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>CadOwl Audit Report — {generated}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      background: #f8f9fa;
      color: #1a1a1a;
      margin: 0;
      padding: 24px;
      line-height: 1.5;
    }}
    .container {{ max-width: 1280px; margin: 0 auto; }}
    .hero {{
      background: linear-gradient(135deg, #0053e2 0%, #003a9e 100%);
      color: white;
      padding: 32px;
      border-radius: 8px;
      margin-bottom: 24px;
    }}
    .hero h1 {{ margin: 0 0 8px 0; font-size: 28px; }}
    .hero p {{ margin: 0; opacity: 0.9; font-size: 14px; }}
    .status-banner {{
      background: white;
      padding: 20px 24px;
      border-radius: 8px;
      margin-bottom: 24px;
      border-left: 6px solid {overall_color};
    }}
    .status-banner h2 {{ margin: 0; color: {overall_color}; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }}
    .stat {{
      background: white;
      padding: 20px;
      border-radius: 8px;
      text-align: center;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    .stat .num {{ font-size: 36px; font-weight: 700; }}
    .stat .label {{ color: #666; font-size: 13px; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
    .summary-table {{
      background: white;
      padding: 24px;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
      width: 100%;
    }}
    .summary-table table {{ width: 100%; border-collapse: collapse; }}
    .summary-table th {{ text-align: left; padding: 8px; background: #f5f5f5; font-size: 13px; }}
    .summary-table td {{ padding: 12px 8px; border-bottom: 1px solid #eee; }}
    table tr.finding td {{ padding: 12px 8px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
    .filter-bar {{
      background: white;
      padding: 12px 16px;
      border-radius: 8px;
      margin: 24px 0 16px 0;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    .filter-bar button {{
      background: #0053e2;
      color: white;
      border: none;
      padding: 6px 16px;
      border-radius: 4px;
      cursor: pointer;
      margin-right: 8px;
      font-size: 13px;
      font-weight: 600;
    }}
    .filter-bar button.inactive {{ background: #ddd; color: #666; }}
    .filter-bar button:hover {{ opacity: 0.9; }}
    code {{ font-family: "SF Mono", Consolas, monospace; background: #f5f5f5; padding: 2px 4px; border-radius: 3px; }}
    footer {{ text-align: center; color: #666; font-size: 13px; margin: 48px 0 16px 0; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="hero">
      <h1>🐶 CadOwl / ForgeSight Audit Report</h1>
      <p>Generated {generated} · Walmart Internal · No hallucinations on our watch.</p>
    </div>

    <div class="status-banner">
      <h2>{overall_status}</h2>
    </div>

    <div class="stats">
      <div class="stat">
        <div class="num" style="color:#1a1a1a;">{len(results)}</div>
        <div class="label">Checks Run</div>
      </div>
      <div class="stat">
        <div class="num" style="color:#ea1100;">{total_errors}</div>
        <div class="label">Errors</div>
      </div>
      <div class="stat">
        <div class="num" style="color:#995213;">{total_warnings}</div>
        <div class="label">Warnings</div>
      </div>
      <div class="stat">
        <div class="num" style="color:#0053e2;">{total_info}</div>
        <div class="label">Info</div>
      </div>
    </div>

    <div class="summary-table">
      <h2 style="margin:0 0 16px 0;">📊 Check Summary</h2>
      <table>
        <thead>
          <tr>
            <th>Check</th>
            <th>Status</th>
            <th>Scanned</th>
            <th>Time</th>
            <th style="color:#ea1100;">Critical</th>
            <th style="color:#ea1100;">Error</th>
            <th style="color:#995213;">Warning</th>
            <th style="color:#0053e2;">Info</th>
          </tr>
        </thead>
        <tbody>{summary_rows}</tbody>
      </table>
    </div>

    <div class="filter-bar">
      <span style="margin-right:12px;font-weight:600;">Filter:</span>
      <button onclick="filterFindings('all')">All ({total_findings})</button>
      <button onclick="filterFindings('critical')">🚨 Critical</button>
      <button onclick="filterFindings('error')">❌ Errors ({total_errors})</button>
      <button onclick="filterFindings('warning')">⚠️ Warnings ({total_warnings})</button>
      <button onclick="filterFindings('info')">ℹ️ Info ({total_info})</button>
    </div>

    {"".join(check_sections)}

    <footer>
      <p>🐶 Generated by <code>scripts/audit</code> · Maxim's Puppy<br>
      Copyright © 2024-2026 Walmart Inc. All rights reserved.</p>
    </footer>
  </div>

  <script>
    function filterFindings(severity) {{
      const rows = document.querySelectorAll('tr.finding');
      rows.forEach(row => {{
        if (severity === 'all') {{
          row.style.display = '';
        }} else {{
          row.style.display = row.classList.contains('finding-' + severity) ? '' : 'none';
        }}
      }});
    }}
  </script>
</body>
</html>
"""
    output_path.write_text(html_doc, encoding="utf-8")
