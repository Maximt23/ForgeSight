# 📞 Support

Need help with CadOwl? Here's where to go.

---

## Quick Answers

| Question | Answer |
|----------|--------|
| How do I install? | See [README — Quick Start](README.md#-quick-start) |
| How do I import a DXF? | `python cad2siteowl.py "Input/FA/your_file.dxf"` |
| Where do exports go? | `Output/{system}/{store}_SiteOwl_Export.csv` |
| API docs? | `http://localhost:9010/docs` after starting the API |
| Architecture? | [docs/architecture.md](docs/architecture.md) |
| Integrations? | [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) |
| Bigger picture? | [docs/ECOSYSTEM.md](docs/ECOSYSTEM.md) |

---

## Reporting Issues

### Found a bug?
Open a [bug report](.github/ISSUE_TEMPLATE/bug_report.yml). Include:
- What you ran
- What you expected
- What actually happened
- Logs (with secrets redacted!)

### Have a feature idea?
Open a [feature request](.github/ISSUE_TEMPLATE/feature_request.yml).

### Found a security issue?
**Do not open a public issue.** See [SECURITY.md](SECURITY.md).

---

## Getting Help

### Synchronous
- 💬 **Slack**: `#mint-support` — fastest response during business hours
- 📞 **Teams**: General channel in MLPlatforms

### Asynchronous
- 📧 **Email**: Repo maintainer (see [CODEOWNERS](.github/CODEOWNERS))
- 🐛 **GitHub Issue**: For reproducible bugs or feature requests

### Self-Service
- 📚 **Docs**: Start at [README.md](README.md)
- 🐶 **Code Puppy**: Spawn one at [puppy.walmart.com](https://puppy.walmart.com)
  to help you write code that uses CadOwl
- 🎓 **Workshops**: [puppy.walmart.com/doghouse](https://puppy.walmart.com/doghouse)

---

## Common Issues

### "VPN required" or "DNS resolution failed"
You need to be on Walmart VPN or Eagle WiFi for internal Walmart services
(Doris, Saone, Grafana, Element). External services (OSM, Axis exports)
work without VPN.

### "Module not found" after install
Make sure you activated the venv:
```bash
.venv\Scripts\activate    # Windows
source .venv/bin/activate # macOS/Linux
```

### "Doris store not found"
Check the store number in Doris directly. Closed/under-construction stores
may not be visible in the standard API.

### "Saone returns all cameras offline"
Verify your `SAONE_API_KEY` in `.env`. Test directly at
https://saone.walmart.com/insights/connectivity/connectionAvailability.

### "Grafana 401 Unauthorized"
Generate a new API key in Grafana → Settings → API Keys. Update `.env`.

### "Camera not mapping to switch port"
Run a fresh ARP scan on the switch, then retry. Stale ARP tables cause
this. Long-term fix: enable LLDP on cameras.

### Multi-puppy conflicts
Check `relayops/state/conflicts.md`. If two puppies are touching the same
files, one must back off. Coordinate via `relayops/outbox/`.

---

## Office Hours

The maintainer holds **virtual office hours every Wednesday 2-3pm CT** in
the `#mint-support` Slack channel. Drop in with questions, design reviews,
or just to chat about the platform direction.

---

## Service Level

This is an **internal Walmart project under active development**. Best-effort
support during business hours. Critical issues addressed within 24 hours.

For production-grade SLOs, wait for Phase 6 (Production GA).

---

## Escalation Path

1. Try self-service docs first
2. Ask in `#mint-support` Slack
3. Open a GitHub issue if reproducible
4. Email the maintainer if urgent
5. Escalate to Walmart leadership only for blocking business impact

---

🐶 *We're here to help. Don't suffer in silence.*
