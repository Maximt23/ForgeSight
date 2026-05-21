# 📝 Design Workflow Guide

This guide explains how designs move through the approval workflow from creation to production.

---

## Workflow Overview

```
┌─────────┐     ┌───────────┐     ┌───────────┐     ┌──────────┐
│  DRAFT  │────►│ SUBMITTED │────►│ IN_REVIEW │────►│ APPROVED │
└─────────┘     └───────────┘     └─────┬─────┘     └────┬─────┘
                      ▲                 │                │
                      │                 ▼                ▼
                      │           ┌──────────┐    ┌─────────────┐
                      └───────────│ REVISION │    │ IN_PROGRESS │
                                  │ REQUIRED │    └──────┬──────┘
                                  └──────────┘           │
                                                         ▼
                                                  ┌──────────┐
                                                  │ COMPLETE │
                                                  └────┬─────┘
                                                       │
                                                       ▼
                                               ┌──────────────┐
                                               │ COMMISSIONED │
                                               └──────┬───────┘
                                                      │
                                                      ▼
                                                  ┌──────┐
                                                  │ LIVE │
                                                  └──────┘
```

---

## Status Definitions

| Status | Description | Who Can Edit | Next Steps |
|:-------|:------------|:-------------|:-----------|
| **Draft** | Initial creation | Designer | Submit for review |
| **Submitted** | Awaiting review | Read-only | Reviewer picks up |
| **In Review** | Being reviewed | Reviewer notes | Approve or request revision |
| **Revision Required** | Needs changes | Designer | Make changes, resubmit |
| **Rejected** | Not approved | Read-only | Start new design |
| **Approved** | Ready to build | Read-only | Assign vendor, start install |
| **In Progress** | Being installed | Installer | Mark complete or hold |
| **On Hold** | Paused | PM only | Resume when ready |
| **Complete** | Installation done | Read-only | Commission |
| **Commissioned** | Tested & verified | Read-only | Go live |
| **Live** | In production | Maintenance | Archive when done |

---

## Step-by-Step Workflow

### 1️⃣ Create Design (Designer)

```bash
curl -X POST http://localhost:9010/api/v1/designs \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "...",
    "site_id": "...",
    "name": "Store 1234 CCTV Upgrade",
    "design_type": "cctv",
    "priority": "high",
    "description": "Add 15 cameras to cover new grocery section"
  }'
```

**Status**: `DRAFT`

---

### 2️⃣ Submit for Review (Designer)

```bash
curl -X PATCH http://localhost:9010/api/v1/designs/{id}/status \
  -d '{
    "new_status": "submitted",
    "changed_by": "designer@walmart.com",
    "reason": "Ready for PM review"
  }'
```

**Status**: `SUBMITTED`

---

### 3️⃣ Review Design (Reviewer/PM)

Reviewer picks up the design:

```bash
curl -X PATCH http://localhost:9010/api/v1/designs/{id}/status \
  -d '{
    "new_status": "in_review",
    "changed_by": "pm@walmart.com"
  }'
```

**Status**: `IN_REVIEW`

---

### 4️⃣a Approve Design ✅

```bash
curl -X PATCH http://localhost:9010/api/v1/designs/{id}/status \
  -d '{
    "new_status": "approved",
    "changed_by": "pm@walmart.com",
    "reason": "Design meets requirements, budget approved"
  }'
```

**Status**: `APPROVED`

---

### 4️⃣b Request Revision 🔄

```bash
curl -X PATCH http://localhost:9010/api/v1/designs/{id}/status \
  -d '{
    "new_status": "revision_required",
    "changed_by": "pm@walmart.com",
    "reason": "Missing cameras in pharmacy area, need 3 more"
  }'
```

**Status**: `REVISION_REQUIRED`

Designer makes changes and resubmits (back to step 2).

---

### 5️⃣ Assign Vendor (PM)

```bash
curl -X PATCH http://localhost:9010/api/v1/designs/{id}/vendor \
  -d '{
    "vendor_id": "...",
    "vendor_status": "assigned"
  }'
```

---

### 6️⃣ Start Installation (Installer)

```bash
curl -X PATCH http://localhost:9010/api/v1/designs/{id}/status \
  -d '{
    "new_status": "in_progress",
    "changed_by": "installer@vendor.com"
  }'
```

**Status**: `IN_PROGRESS`

---

### 7️⃣ Complete Installation (Installer)

```bash
curl -X PATCH http://localhost:9010/api/v1/designs/{id}/status \
  -d '{
    "new_status": "complete",
    "changed_by": "installer@vendor.com",
    "reason": "All cameras installed and tested"
  }'
```

**Status**: `COMPLETE`

---

### 8️⃣ Commission (PM)

```bash
curl -X PATCH http://localhost:9010/api/v1/designs/{id}/status \
  -d '{
    "new_status": "commissioned",
    "changed_by": "pm@walmart.com",
    "reason": "All systems verified, training complete"
  }'
```

**Status**: `COMMISSIONED`

---

### 9️⃣ Go Live (PM)

```bash
curl -X PATCH http://localhost:9010/api/v1/designs/{id}/status \
  -d '{
    "new_status": "live",
    "changed_by": "pm@walmart.com"
  }'
```

**Status**: `LIVE` 🎉

---

## Design Types

| Type | Code | Description |
|:-----|:-----|:------------|
| CCTV | `cctv` | Video surveillance cameras |
| Fire Alarm | `fire_alarm` | Detection & notification |
| Intrusion | `intrusion` | Burglar alarm, motion |
| Access Control | `access_control` | Card readers, doors |
| Integrated | `integrated` | All security systems |
| Network | `network` | IDF, cabling, infrastructure |
| Audio Visual | `audio_visual` | PVM, speakers, intercoms |

---

## Priority Levels

| Priority | SLA | Use Case |
|:---------|:----|:---------|
| **Critical** | 24 hours | Security incidents, urgent fixes |
| **High** | 3 days | Store openings, remodels |
| **Normal** | 2 weeks | Scheduled upgrades |
| **Low** | 30 days | Minor improvements |
| **Backlog** | TBD | Future consideration |

---

## Related

- [Site Lifecycle](User-Guide-Site-Lifecycle.md)
- [Authentication](Dev-Authentication.md)
- [API Reference](Dev-API-Reference.md)
