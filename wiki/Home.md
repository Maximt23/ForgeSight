# 🔮 ForgeSight AI Wiki

> **Enterprise Security Design Intelligence Platform**

Welcome to the ForgeSight documentation! This wiki covers the entire product suite.

---

## 🚀 Product Suite

| Product | Description | Status |
|:--------|:------------|:-------|
| **[ForgeSight AI](#)** | Main platform & dashboard | ✅ Stable |
| **[ForgeSight CAD](ForgeSight-CAD.md)** | CAD/DXF/PDF design engine | ✅ Stable |
| **[ForgeSight Field](ForgeSight-Field.md)** | Mobile/VR site survey | 🟡 Beta |
| **[ForgeSight Vision](ForgeSight-Vision.md)** | Camera/FOV coverage | 🟡 Beta |
| **[ForgeSight Grid](ForgeSight-Grid.md)** | GIS/coordinates/zoning | ✅ Stable |
| **[ForgeSight Core](ForgeSight-Core.md)** | API/data platform | ✅ Stable |
| **[ForgeSight AutoDesign](ForgeSight-AutoDesign.md)** | ML design intelligence | 🔴 Alpha |

---

## 📖 Documentation

### Getting Started
- [Quick Start](Quick-Start.md) — Get running in 5 minutes
- [Installation](Installation.md) — Full setup guide
- [Configuration](Configuration.md) — Environment setup

### User Guides
- [Site Lifecycle](User-Guide-Site-Lifecycle.md) — Sandbox → Design → Live
- [Design Workflow](User-Guide-Design-Workflow.md) — Approval process
- [CAD Import](User-Guide-CAD-Import.md) — Importing drawings

### Developer Guides
- [Architecture](Dev-Architecture.md) — System design
- [API Reference](Dev-API-Reference.md) — REST endpoints
- [Authentication](Dev-Authentication.md) — Walmart SSO

### Reference
- [Glossary](Glossary.md) — Terms & definitions
- [FAQ](FAQ.md) — Common questions

---

## 🔗 Quick Links

| I want to... | Go to... |
|:-------------|:---------|
| Start quickly | [Quick Start](Quick-Start.md) |
| Import CAD files | [ForgeSight CAD](ForgeSight-CAD.md) |
| Use VR survey | [ForgeSight Field](ForgeSight-Field.md) |
| Analyze coverage | [ForgeSight Vision](ForgeSight-Vision.md) |
| Use the API | [API Reference](Dev-API-Reference.md) |
| Get AI suggestions | [ForgeSight AutoDesign](ForgeSight-AutoDesign.md) |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     ForgeSight AI                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │   CAD   │ │  Field  │ │ Vision  │ │  Grid   │           │
│  │ Engine  │ │  App    │ │ Engine  │ │ Engine  │           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
│       └───────────┴───────────┴───────────┘                 │
│                         │                                    │
│                         ▼                                    │
│              ┌─────────────────────┐                        │
│              │   ForgeSight Core   │                        │
│              │   API Platform      │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│                         ▼                                    │
│              ┌─────────────────────┐                        │
│              │ ForgeSight AutoDesign│                        │
│              │   ML Intelligence   │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤝 Support

- **Teams**: [ForgeSight Support Channel](https://teams.microsoft.com/l/channel/19%3AGbP8DGJjrXq1sL3IlXErZc5U7hk-IEqsokmnImcKyP41%40thread.tacv2/General?groupId=51caa2b5-ff58-4dc0-9ee0-c20eea1de9f8&tenantId=3cbcc3d3-094d-4006-9849-0d11d61f484d)
- **Slack**: [#forgesight-support](https://walmart.enterprise.slack.com/archives/C094Y1D24JY)
- **Issues**: [GitHub Issues](https://gecgithub01.walmart.com/vn59j7j/ForgeSight/issues)

---

*ForgeSight AI — Forging the Future of Security Design*
