# Site & Design Lifecycle Data Model

## Overview

This document defines the lifecycle states, types, and statuses for the CadOwl platform.

## Site Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SITE LIFECYCLE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌──────────┐    ┌──────────┐ │
│  │ SANDBOX  │───►│   DESIGN     │───►│ INSTALL  │───►│   LIVE   │ │
│  │          │    │              │    │          │    │          │ │
│  │ Testing  │    │  Planning    │    │ Building │    │ Operating│ │
│  │ Proto-   │    │  Approval    │    │ Commis-  │    │ Maint-   │ │
│  │ typing   │    │  Budgeting   │    │ sioning  │    │ enance   │ │
│  └──────────┘    └──────────────┘    └──────────┘    └──────────┘ │
│       │                │                  │               │        │
│       │                │                  │               │        │
│       ▼                ▼                  ▼               ▼        │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    ARCHIVED                                  │  │
│  │         (Completed, Cancelled, Superseded)                   │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Site Types

| Type | Description | Use Case |
|:-----|:------------|:---------|
| `sandbox` | Experimental/testing | Prototyping designs, training, demos |
| `design` | Active design phase | New stores, remodels, upgrades |
| `installation` | Being built/installed | Vendor on-site, commissioning |
| `live` | Operational site | Maintenance, monitoring, updates |
| `archived` | Historical/closed | Completed projects, closed stores |

## Design Types

| Type | Code | Systems Included |
|:-----|:-----|:-----------------|
| `cctv` | CCTV | Video surveillance only |
| `fire_alarm` | FA | Fire detection & notification |
| `intrusion` | INT | Burglar alarm, motion sensors |
| `access_control` | AC | Card readers, door controllers |
| `integrated` | INT-ALL | All security systems |
| `network` | NET | Infrastructure only (IDF, cabling) |
| `audio_visual` | AV | PVM, speakers, intercoms |

## Design Statuses

```
┌─────────────────────────────────────────────────────────────────┐
│                    DESIGN STATUS FLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐                                                    │
│  │  DRAFT  │ ─── Initial creation, editable                    │
│  └────┬────┘                                                    │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────┐                                                │
│  │  SUBMITTED  │ ─── Sent for review                           │
│  └──────┬──────┘                                                │
│         │                                                       │
│    ┌────┴────┐                                                  │
│    ▼         ▼                                                  │
│ ┌────────┐ ┌──────────┐                                        │
│ │REVISION│ │IN_REVIEW │ ─── Being reviewed by approver         │
│ │REQUIRED│ └────┬─────┘                                        │
│ └───┬────┘      │                                               │
│     │      ┌────┴────┐                                          │
│     │      ▼         ▼                                          │
│     │  ┌────────┐ ┌────────┐                                   │
│     └─►│REJECTED│ │APPROVED│ ─── Ready for installation        │
│        └────────┘ └───┬────┘                                   │
│                       │                                         │
│                       ▼                                         │
│               ┌─────────────┐                                   │
│               │ IN_PROGRESS │ ─── Installation active          │
│               └──────┬──────┘                                   │
│                      │                                          │
│                 ┌────┴────┐                                     │
│                 ▼         ▼                                     │
│            ┌────────┐ ┌───────┐                                │
│            │ON_HOLD │ │COMPLETE│ ─── Installation done         │
│            └────────┘ └───┬───┘                                │
│                           │                                     │
│                           ▼                                     │
│                    ┌───────────┐                                │
│                    │COMMISSIONED│ ─── Tested & handed over     │
│                    └─────┬─────┘                                │
│                          │                                      │
│                          ▼                                      │
│                     ┌────────┐                                  │
│                     │  LIVE  │ ─── In production               │
│                     └────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Status Definitions

| Status | Description | Who Can Edit | Next States |
|:-------|:------------|:-------------|:------------|
| `draft` | Initial creation | Designer | submitted |
| `submitted` | Awaiting review | Read-only | in_review, revision_required |
| `in_review` | Being reviewed | Reviewer only | approved, rejected, revision_required |
| `revision_required` | Needs changes | Designer | submitted |
| `rejected` | Not approved | Read-only | draft (clone) |
| `approved` | Ready to build | Read-only | in_progress |
| `in_progress` | Being installed | Installer | complete, on_hold |
| `on_hold` | Paused | PM only | in_progress |
| `complete` | Installation done | Read-only | commissioned |
| `commissioned` | Tested & verified | Read-only | live |
| `live` | In production | Maintenance | archived |
| `archived` | Closed/historical | Read-only | - |

## Permissions Matrix

| Role | Sandbox | Design | Installation | Live |
|:-----|:--------|:-------|:-------------|:-----|
| Designer | Full | Create/Edit | Read | Read |
| Reviewer | Read | Review/Approve | Read | Read |
| PM | Full | Full | Full | Read |
| Installer | Read | Read | Edit | Read |
| Maintenance | Read | Read | Read | Edit |
| Admin | Full | Full | Full | Full |
