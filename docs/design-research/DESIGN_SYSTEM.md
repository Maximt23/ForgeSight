# 🎨 CadOwl Design System — The North Star

**Project:** CadOwl = ForgeSight + MAXILLM + VIVE-XR + SiteOwl-Killer + CAD, unified.
**Bar:** Google / Anthropic grade. Linear-clean. Vercel-confident. Claude-warm.
**Date:** 2026-05-21

> Inspiration mined from: 21st.dev (58 categories, 1200+ components), magicui (209 components), shadcn-ui (50+ primitives). Top patterns extracted by qa-kitten scout + repo analysis.

---

## 0. ForgeSearch — the SPINE (read this first)

**ForgeSearch is the primary interaction layer of the entire app.** Everything else is a surface ForgeSearch can operate on.

It is a Google-grade AI command bar that:

- Lives **top-center** of every page, persistent, glass-morphic
- Opens to a full-screen overlay on **⌘K / Ctrl+K** (shared-element morph via View Transitions API)
- Has a **floating-pill mode** on the canvas surface
- Classifies user intent in real time into **six categories** (color + icon coded):
  - 🔍 **Query** `#4a8eff` — find, show, list, highlight
  - ↔️ **Modify** `#a855f7` — move, connect, rename, reassign
  - ✨ **Generate** `#ec4899` — add, create, design, draw, propose
  - 🛡 **Validate** `#ffc220` — audit, check, compare against standards
  - ⬇️ **Export** `#22c55e` — CSV, PDF, SiteOwl, vendor email
  - 🗑 **Destructive** `#ef4444` — delete, clear, reset (always confirms)
- Supports `/slash` commands (`/design`, `/qa`, `/export`, `/find`, `/explain`, `/fix`)
- Supports `@mentions` to scope context (`@cameras`, `@grocery`, `@IDF-2`)
- Returns three result shapes: **AI synthesis text**, **entity rows**, **canvas operation preview** with action chips
- Always includes a latency stamp (e.g. `127 ms`) so the system feels honest about its work

**Design discipline (non-negotiable):**

- Chrome is **blue + neutrals only**. The six intent colors appear *only* inside the live classifier badge and the static intent-grid card chips. Never as backgrounds, never as section headers, never as button fills.
- Intent badges always pair **color + icon + label** for WCAG 2.2 SC 1.4.1 (color-blind accessibility).
- The bar is the **same component everywhere** — top-bar, canvas pill, overlay all share `view-transition-name: forge-bar` for a true morph (declare on exactly one source + one target per frame; spec aborts on duplicates).
- A persistent **autoplay loop** below the hero shows ForgeSearch operating itself (typewriter → intent classify → results stream) on a ~14s cycle. This is how visitors understand it's a spine, not a search box.

**Build status:** prototype shipped at `design-research/forgesearch-preview.html`, audited at **9.0/10** by qa-kitten across 3 review rounds.

---

## 1. Five Design Laws (non-negotiable)

These are derived from the qa-kitten scout's observations about which components on 21st.dev actually win.

1. **Motion is the product.** Every primary surface has one — and only one — ambient motion. Aurora gradient, animated beam, flickering grid, or shimmer. Static = forgettable.
2. **One luminous focal point per screen.** Near-black canvas, one glowing element. Halo, lamp, gradient orb. No competing glows.
3. **Display type IS the chrome.** Oversized humanist sans at 600–800 weight is the headline AND the decoration. No icon clutter near hero text.
4. **Liquid glass over flat.** Translucent surfaces with `backdrop-filter: blur(20px)` beat opaque cards. iOS 18 / visionOS aesthetic is the current peak.
5. **Density is the enemy of confidence.** Whitespace is the most expensive design asset. If a card has more than 3 elements, it's probably wrong.

---

## 2. Color Tokens

Deep-dark canvas (premium SaaS), Walmart Blue as primary CTA thread, Spark Yellow as accent flicker. Designed for WCAG 2.2 AA.

```css
:root {
  /* Canvas */
  --bg-base:        #0a0a0c;  /* page bg, near-black with cool tint */
  --bg-surface:     #131318;  /* default card */
  --bg-elevated:    #1c1c23;  /* hover / popover */
  --bg-glass:       rgba(28,28,35,0.55);  /* blurred panels */

  /* Lines */
  --border-subtle:  #232329;
  --border-strong:  #34343d;
  --border-glow:    rgba(0,83,226,0.45);  /* focus rings */

  /* Text */
  --text-primary:   #fafafa;  /* 16.8:1 on bg-base */
  --text-secondary: #a1a1aa;  /* 7.2:1 — body */
  --text-tertiary:  #71717a;  /* 4.6:1 — captions */
  --text-disabled:  #52525b;

  /* Brand (Walmart) */
  --brand-blue:     #0053e2;  /* primary CTA */
  --brand-blue-hi:  #1a66ea;  /* hover (+10) */
  --brand-blue-lo:  #003db8;  /* pressed (+30) */
  --spark-yellow:   #ffc220;  /* badges, sparkles */
  --spark-amber:    #995213;  /* warning text */

  /* Semantic */
  --success:        #2a8703;
  --warning-bg:     rgba(255,194,32,0.10);
  --error:          #ea1100;

  /* Gradients */
  --grad-hero:      linear-gradient(135deg, #0053e2 0%, #7c3aed 50%, #ec4899 100%);
  --grad-aurora:    radial-gradient(ellipse at top, rgba(0,83,226,0.35) 0%, transparent 60%);
  --grad-lamp:      radial-gradient(ellipse 80% 50% at 50% -10%, rgba(124,58,237,0.4), transparent);
}
```

**Light mode (deferred)** — we ship dark-first like Vercel/Linear. Light mode is v2.

---

## 3. Typography

| Token | Stack | Use |
|---|---|---|
| `--font-display` | `'Geist', ui-sans-serif, system-ui, 'Segoe UI Variable', 'Inter'` | h1, h2, hero |
| `--font-body` | `'Inter', ui-sans-serif, system-ui, 'Segoe UI'` | paragraphs, UI |
| `--font-mono` | `'Geist Mono', ui-monospace, 'Cascadia Code', 'JetBrains Mono'` | code, data |

**Scale (1.250 major-third ramp):**

| Token | rem | px | Weight | Tracking |
|---|---|---|---|---|
| `text-display-xl` | 4.768 | 76.3 | 700 | -0.04em |
| `text-display-lg` | 3.815 | 61   | 700 | -0.035em |
| `text-display-md` | 3.052 | 48.8 | 600 | -0.03em |
| `text-h1`         | 2.441 | 39   | 600 | -0.025em |
| `text-h2`         | 1.953 | 31.3 | 600 | -0.02em |
| `text-h3`         | 1.563 | 25   | 600 | -0.015em |
| `text-body-lg`    | 1.250 | 20   | 400 | -0.01em |
| `text-body`       | 1.000 | 16   | 400 | 0 |
| `text-body-sm`    | 0.875 | 14   | 400 | 0 |
| `text-caption`    | 0.750 | 12   | 500 | 0.02em |

Display sizes always pair with tight leading (1.05–1.15). Body text is 1.6.

---

## 4. Spacing & Layout

4px base unit. **Only use multiples of 4.** This is the single most-violated rule.

```
0 1 2 4 6 8 12 16 20 24 32 40 48 64 80 96 128
```

Container max-width: `1280px` (content), `1536px` (dashboards).
Sidebar width: `260px` (collapsed `64px`).
Page gutter: `24px` mobile, `48px` desktop.

---

## 5. Motion Principles

| Token | Value | Use |
|---|---|---|
| `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` | default enter |
| `--ease-in-out` | `cubic-bezier(0.65, 0, 0.35, 1)` | hovers, toggles |
| `--ease-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | playful pops |
| `--dur-instant` | `80ms` | tooltips, focus |
| `--dur-fast` | `180ms` | hovers, dropdowns |
| `--dur-base` | `320ms` | modals, page bits |
| `--dur-slow` | `600ms` | hero reveals |
| `--dur-ambient` | `8000ms+` | background motion |

**The Anthropic reveal** (use everywhere on first paint):
```css
@keyframes anthropic-in {
  from { opacity: 0; transform: translateY(8px); filter: blur(4px); }
  to   { opacity: 1; transform: translateY(0); filter: blur(0); }
}
.reveal { animation: anthropic-in 600ms var(--ease-out) backwards; }
.reveal-1 { animation-delay: 60ms; }
.reveal-2 { animation-delay: 120ms; }
.reveal-3 { animation-delay: 180ms; }
.reveal-4 { animation-delay: 240ms; }
```

**Reduced motion:** ALWAYS guard with `@media (prefers-reduced-motion: reduce)` and collapse to opacity-only transitions.

---

## 6. The Component Picklist (for CadOwl v1)

Curated from 21st.dev + magicui. These are the components we will lift the *patterns* from (not the code verbatim — we'll re-implement in vanilla HTML/CSS/HTMX where possible to stay on stack).

### Hero / Landing
- `aurora-background` (aceternity) — page-top ambient
- `lamp` (aceternity) — section breakers
- `bento-grid` (kokonutd / magicui) — feature showcase
- `animated-beam` (magicui) — show CadOwl ↔ MAXILLM ↔ XR data flow

### Dashboard chrome
- `sidebar` (shadcn-ui) — primary nav (collapsible, icon-only mode)
- `command palette` (cmdk pattern) — ⌘K everything
- `dock` (magicui) — quick actions floater on viewer screens
- `animated-list` (magicui) — activity feed
- `border-beam` (magicui) — highlight active panel

### AI chat (MAXILLM surface)
- `ai-prompt-box` (easemize) — main input
- `animated-ai-chat` (jatin-yadav05) — message stream
- `agent-plan` (isaiahbjork) — render multi-step plans
- `shimmer-button` (magicui) — "Run" CTA

### Data & ops
- `data-table` (shadcn-ui) — survey rows, devices
- `animated-circular-progress-bar` (magicui) — upload/sync status
- `globe` (magicui) — store locations overview
- `file-tree` (magicui) — CAD layer browser

### Micro-delight
- `sparkles` (aceternity) — success states
- `confetti` (magicui) — survey-complete moments
- `blur-fade` (magicui) — content reveals
- `aurora-text` (magicui) — accent words in headlines

---

## 7. Stack Decision

Per Walmart default + Maxim's existing repo (Python tooling, FastAPI compatible):

| Layer | Tech | Why |
|---|---|---|
| Backend | **FastAPI** + SQLite | Default stack; matches `platform_api.py` already in repo |
| Templating | **Jinja2** | Server-rendered, SEO-able |
| Interactivity | **HTMX** + **Alpine.js** (3KB) | Reactive without React ceremony |
| Styling | **Tailwind v3** (CDN for prototype, build for prod) | Atomic, fast |
| Motion | **Motion One** (~3.8KB) + CSS keyframes | Framer-quality with vanilla JS |
| Icons | **Lucide** (CDN) | Same set shadcn uses |
| 3D / CAD viewer | reuse existing `floorplan_viewer.py` (PyVista) → embed via iframe or convert to **three.js** | TBD pending CAD-viewer audit |
| Charts | **Chart.js** (per Walmart rules for reports) | |

This gives us **80% of the magicui visual vocabulary** without React. The 20% we lose (Three.js shaders, complex GSAP scroll-jacking) we either skip or upgrade selectively with vanilla three.js / GSAP.

---

## 8. What's Next

1. ✅ Design system documented (this file)
2. ✅ **Design-preview HTML** — hero + bento + AI chat + sidebar mockups (`design-preview.html`)
3. ✅ **ForgeSearch prototype** — 9.0/10 audited, the centerpiece (`forgesearch-preview.html`)
4. ⏭ **Scaffold the real FastAPI app** at `C:\MAXILLM\app\` with:
   - Jinja base layout that includes the persistent ForgeSearch bar on every page
   - `/api/forgesearch/classify` — returns intent + confidence (rule-first, LLM-fallback)
   - `/api/forgesearch/execute` — routes intent to the matching executor (query/modify/generate/validate/export)
   - Executors call into the real domain: SQLite device table, CAD JSON, validation rules, SiteOwl CSV writer
   - MAXILLM (Ollama at `:11434`) is the LLM provider for synthesis + complex classification
5. ⏭ Wire first three routes: `/` (overview), `/canvas` (floorplan viewer), `/devices` (table)
6. ⏭ Replace `floorplan_viewer.py` (PyVista) with a three.js canvas that ForgeSearch can operate on
7. ⏭ Migrate `master_dashboard_3508.json` → SQLite via SQLModel for relational queries

---

*"Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away." — Saint-Exupéry, also the entire shadcn/Anthropic playbook.*
