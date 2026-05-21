# 🔄 Site Lifecycle Guide

Sites in CadOwl move through distinct lifecycle phases. This guide explains each phase and how to transition between them.

---

## Lifecycle Overview

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│ SANDBOX  │────►│  DESIGN  │────►│ INSTALLATION │────►│   LIVE   │
│          │     │          │     │              │     │          │
│ Testing  │     │ Planning │     │  Building    │     │ Running  │
└──────────┘     └──────────┘     └──────────────┘     └──────────┘
      │               │                  │                  │
      └───────────────┴──────────────────┴──────────────────┘
                              │
                              ▼
                       ┌──────────┐
                       │ ARCHIVED │
                       └──────────┘
```

---

## Site Types

### 🧪 Sandbox

**Purpose**: Testing, prototyping, training

**Use Cases**:
- Experimenting with new camera layouts
- Training new designers
- Demo environments for stakeholders
- Testing "what-if" scenarios

**Capabilities**:
- Full editing access
- Can clone from any site
- Auto-expires (configurable)
- No approval workflow required

**Transitions**:
- → Design (promote prototype to real project)
- → Archived (discard)

---

### 📐 Design

**Purpose**: Active design and planning phase

**Use Cases**:
- New store construction
- Store remodels
- System upgrades
- Adding new zones

**Capabilities**:
- Full design editing
- Approval workflow enforced
- Vendor assignment
- Budget tracking

**Transitions**:
- → Installation (approved and vendor assigned)
- → Archived (project cancelled)

---

### 🔧 Installation

**Purpose**: Active installation by vendors

**Use Cases**:
- Vendor on-site work
- Equipment deployment
- Commissioning activities

**Capabilities**:
- Limited editing (installation fields only)
- Progress tracking
- Photo documentation
- Punch list management

**Transitions**:
- → Live (installation complete & commissioned)
- → Archived (project cancelled)

---

### 🟢 Live

**Purpose**: Operational site in production

**Use Cases**:
- Day-to-day operations
- Maintenance activities
- System monitoring
- Minor updates

**Capabilities**:
- Read-only for most users
- Maintenance mode edits
- Incident tracking
- Performance monitoring

**Transitions**:
- → Archived (store closed)

---

### 📦 Archived

**Purpose**: Historical record keeping

**Use Cases**:
- Closed stores
- Completed projects
- Superseded designs

**Capabilities**:
- Read-only
- Full audit history preserved
- Can be referenced but not edited

**Transitions**:
- None (terminal state)

---

## Transitioning Sites

### Via API

```bash
# Move site from Design to Installation
curl -X PATCH http://localhost:9010/api/v1/sites/{site_id}/type \
  -H "Content-Type: application/json" \
  -d '{
    "new_type": "installation",
    "changed_by": "pm@walmart.com",
    "reason": "Vendor CEI assigned, ready to install"
  }'
```

### Via Dashboard

1. Navigate to **Sites** → Select site
2. Click **Actions** → **Change Phase**
3. Select new phase
4. Add reason (required)
5. Confirm transition

---

## Permissions by Phase

| Role | Sandbox | Design | Installation | Live |
|:-----|:-------:|:------:|:------------:|:----:|
| Viewer | 👁️ | 👁️ | 👁️ | 👁️ |
| Designer | ✏️ | ✏️ | 👁️ | 👁️ |
| Installer | 👁️ | 👁️ | ✏️ | 👁️ |
| PM | ✏️ | ✏️ | ✏️ | 👁️ |
| Admin | ✏️ | ✏️ | ✏️ | ✏️ |

👁️ = View only | ✏️ = Edit

---

## Best Practices

1. **Start in Sandbox** — Always prototype complex designs first
2. **Document Transitions** — Include clear reasons for audit trail
3. **Review Before Installation** — Ensure all approvals are in place
4. **Don't Rush to Live** — Complete commissioning checklist first

---

## Related

- [Design Workflow](User-Guide-Design-Workflow.md)
- [Sandbox Mode](User-Guide-Sandbox.md)
- [API Reference](Dev-API-Reference.md)
