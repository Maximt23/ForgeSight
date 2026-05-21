# 🛡️ Security Policy

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

CadOwl handles Walmart store infrastructure data. A security bug here can
affect physical security systems across hundreds of stores. We take this
seriously.

### How to Report

1. **Email** the repo maintainer directly (see [CODEOWNERS](.github/CODEOWNERS))
2. **Slack** the maintainer privately in `#mint-support`
3. **For high-severity issues** affecting Walmart production systems, also
   follow Walmart's internal security incident response process.

### What to Include

- A clear description of the vulnerability
- Steps to reproduce
- Affected versions / commits
- Potential impact
- Suggested fix (if you have one)
- Whether you've already disclosed to anyone else

### What to Expect

- **Acknowledgment** within 24 hours (weekdays)
- **Initial assessment** within 3 business days
- **Fix timeline** based on severity:
  - Critical: same-day patch
  - High: within 1 week
  - Medium: within 1 month
  - Low: in the next planned release
- **Credit** in `CHANGELOG.md` once the fix is shipped (unless you prefer
  anonymity)

---

## Sensitive Data — Never Commit

| Category | Examples | Why |
|----------|----------|-----|
| **API keys** | Doris, Saone, Grafana, Element tokens | Direct credential leak |
| **Passwords / secrets** | DB creds, SSH keys, OAuth secrets | Direct credential leak |
| **PII** | Names, emails, SSNs, phone numbers | Privacy / regulatory |
| **HIPAA / PHI** | Health data of any kind | Regulatory (HIPAA) |
| **PCI** | Card numbers, CVVs | Regulatory (PCI-DSS) |
| **Customer media** | Photos/videos with faces, license plates | Privacy + brand |
| **Competitor data** | Scraped pricing, assortment | Walmart policy violation |
| **Real store layouts** | Detailed maps of sensitive areas | Physical security risk |

### If You Accidentally Commit a Secret

1. **Rotate the secret immediately** (don't wait for the cleanup)
2. **Remove from history**:
   ```bash
   # For a single file
   git filter-repo --invert-paths --path path/to/secret_file
   # For a single line in a file, use BFG Repo-Cleaner
   ```
3. **Force-push the rewritten history** (this is the one case force-push
   is allowed, and only after coordinating with the team)
4. **Notify** the security contact
5. **Document** the incident in a private retrospective

---

## Defensive Coding Standards

### Input Validation
- All API inputs validated against JSON Schema
- Coordinate ranges checked (`0 ≤ x,y ≤ 100`)
- File uploads size-limited and MIME-checked
- SQL queries always parameterized (when we move to Postgres)

### Authentication & Authorization
- All endpoints require auth (no anonymous writes)
- Role-based access enforced at the API layer
- Audit log records `user_id` for every mutation

### Output Sanitization
- No raw error messages with stack traces in API responses
- File paths never echoed back to clients
- Internal IPs/hostnames stripped from public responses

### Dependencies
- `requirements.txt` pinned to specific versions
- `pip-audit` or similar runs in CI
- Critical CVE = drop everything and patch

### Logging
- **Never log**: passwords, API keys, full credit card numbers, SSNs
- **Always log**: user_id, request_id, action, resource_id, outcome
- **Retention**: 90 days for app logs, 1 year for audit ledger

---

## Cryptography

- TLS 1.2+ for all external HTTP calls
- Walmart's standard certificate authority chain
- No custom crypto. Use battle-tested libraries (`cryptography`, `bcrypt`).
- Secrets stored in environment variables or Walmart's secret manager.
  **Never** in source.

---

## Third-Party Integrations

| Integration | Trust Level | Notes |
|-------------|-------------|-------|
| Doris | Read-only, internal | Walmart SSO |
| Saone | Read-only, internal | Walmart SSO |
| Grafana | Read-only, internal | API key in env |
| OpenStreetMap | Public, rate-limited | Cache results |
| Axis | Imported files only | No API |

When adding a new integration:
1. Document auth method here
2. Add to `SECURITY.md` integration table
3. Threat-model the data flow
4. Add to CI secret scanning allow-list (if needed)

---

## Compliance Notes

- **Walmart Information Security policies** apply to this repo
- **No customer PII** in test fixtures (use synthetic data)
- **No HIPAA data** ever — even by accident, even in tests
- **No PCI scope** — we don't handle payment data
- **Internal use only** — do not open-source without Walmart Legal review

---

## Out of Scope

The following are **NOT** security issues for this repo:
- Performance issues (open a bug instead)
- UX bugs (open a feature request)
- Issues in third-party systems we integrate with (report to that team)
- Issues in dependencies (open upstream, optionally backport)

---

🐶 *Security is everyone's job. When in doubt, ask.*
