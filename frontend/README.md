# StudioFlow Design System

> An Apple-style operational dashboard system for an internal SRE control room. Used to monitor a real-time media production pipeline (Ingest → Transcode → Enrichment → Publish) and the AI agent that diagnoses incidents in it.

---

## The product

**StudioFlow** is a simulated, Apple-flavoured media production pipeline running as event-driven microservices on Cloud Run. The control room — what this design system serves — is the surface where SREs watch assets move stage to stage, where the **StudioFlow Agent** (Gemini 3.1 Pro via Dynatrace MCP) surfaces problems, and where an operator approves remediations the agent proposes.

The control room is **operational, not marketing**. Density is high. Status legibility at a glance matters more than delight. The vibe is a deliberately stripped-down internal Apple tool — not a SaaS landing page, not a consumer app — closer in spirit to Xcode's organizer, the macOS System Settings dark theme, or Final Cut Pro's project window than to anything on the open web.

### Surfaces
There is **one product surface** at this stage:
- **Studio Control Room** — Next.js 15 web app served from Cloud Run. Shows pipeline state, asset timeline, incident triage, agent decisions, and the human approval gate.

Mobile is not a goal. The room is a 1440px-and-up desktop experience.

### Source inputs used for this system

| Source | URL | What we read |
|--------|-----|--------------|
| StudioFlow repo (codebase) | <https://github.com/alanmaizon/studioflow> | `CLAUDE.md` (full product spec + architecture), `docs/demo-script.md`, `docs/architecture.md`, `docs/apple-narrative.md` |
| Brief tokens | provided inline by user | Tailwind theme tokens, glass panel + status pill component sketches, Apple/Cupertino aesthetic direction |

> The repo's `frontend/` directory is currently empty (`.gitkeep` only). That means **no production component code existed to mirror** — this design system establishes the visual vocabulary the frontend will be built against, derived from the spec in `CLAUDE.md` and the design tokens the user supplied. If the reader has access to a later snapshot of the repo with real Next.js components, those should take precedence over the recreations here. Browse the repo further to ground future work: <https://github.com/alanmaizon/studioflow>.

---

## CONTENT FUNDAMENTALS

### Voice
The control room talks like a **terse senior SRE writing for another senior SRE**. Operators read these strings at 3am, sometimes while a P0 is burning. Every label is the shortest thing that is still unambiguous.

- **No marketing register.** Never "Powerful AI agent". Always "Agent · idle" or "Agent · diagnosing".
- **Imperative for actions.** "Approve", "Reject", "Rollback", "Retry", "Acknowledge". Not "Click here to approve".
- **Past tense for events, present tense for state.** "Encoded at 14:32" / "Encoding · 38%".
- **You vs I.** The interface refers to the operator as "you" only in approval-gate copy where consent matters: _"You are about to roll back the encode service to commit `abc123`."_ Otherwise the UI is impersonal — no "I" from the agent. The agent doesn't say "I think the encode service is failing"; it emits a structured hypothesis card with evidence.
- **Cite, don't claim.** Every agent statement carries a trace ID, a DQL link, or a commit SHA. "Hypothesis: OOM under 4K concurrency · 3 traces · commit `enable-4k`".
- **Numbers over adjectives.** Not "high memory". Always "RSS 3.8 GiB / 4.0 GiB".

### Casing
- **Sentence case** everywhere — headers, buttons, menu items, table columns. _"Approve remediation"_, never _"Approve Remediation"_.
- **UPPERCASE** is reserved for **status pills only** (`INGESTED`, `ENCODING`, `FAILED`, `PUBLISHED`). Two- to ten-letter machine states, never used for actions.
- **Code-style identifiers** stay verbatim: service names `encode`, commit SHAs `abc123`, env vars `MEMORY_LEAK` — always in mono font, never re-cased.
- **Time**: 24-hour, local with explicit offset. `14:32:08 UTC+01` in dense tables; `2m ago` in chips.

### Tone examples
| Context | ✅ Use | ❌ Avoid |
|---|---|---|
| Empty state on incident list | "No active incidents." | "All systems go! 🚀" |
| Agent proposing action | "Proposed: rollback `encode` to `abc123`, scale memory 1→4 GiB." | "I recommend that we should probably roll back…" |
| Failure | "Encode failed · OOM killed · 3 retries exhausted." | "Oops! Something went wrong." |
| Approval gate | "You are about to execute 2 actions. This cannot be undone in one click." | "Are you sure you want to proceed?" |
| Toast | "Rolled back to `abc123`." | "Success! Your rollback was completed successfully." |

### Emoji
**No emoji.** Not in UI, not in copy. The only graphic accents are status dots and a small set of monochrome SF-Symbol-style glyphs. Emoji would break the register — this is a tool, not a chat app.

### Numbers, units, identifiers
- File sizes in IEC binary: `512 MiB`, `4.0 GiB`. Never `MB`/`GB` when referring to memory.
- Durations: `1.2s`, `47ms`, `12m`, `2h 14m`. Never `1.2 seconds`.
- Percentages: `38%` not `0.38`. No space.
- Counts: `3 traces`, `12 assets`. Pluralize correctly; `1 trace`.

---

## VISUAL FOUNDATIONS

### Palette
True dark, not "dark mode". The base is **#000000** — not a near-black. Elevation is signaled by translucent overlays on top of black, not lighter greys.

- **Background** `#000000` — the room.
- **Surface** `#1c1c1e` — cards, sidebars, table rows.
- **Surface (hover)** `#2c2c2e` — row hover, button hover.
- **Surface (raised glass)** `rgba(28,28,30,0.6) + backdrop-blur(40px)` — nav bars, modals, sticky headers, the agent's incident card.
- **Border** `rgba(255,255,255,0.08–0.12)` — never a hard line; always a 1px translucent inner stroke. No solid greys.
- **Foreground** `rgba(255,255,255,0.92)` primary, `rgba(255,255,255,0.55)` secondary, `rgba(255,255,255,0.32)` tertiary. Pure white is reserved for headlines.
- **Accent** `#0A84FF` — macOS Blue. Links, primary buttons, focus rings.
- **Status semantic**:
  - `#30D158` — success, published, healthy (muted emerald, not lime).
  - `#FF9F0A` — processing, encoding, attention (amber, not yellow).
  - `#FF453A` — error, OOM, failed (vivid crimson, never used decoratively).
  - `#5E5CE6` — agent activity (indigo — distinguishes machine action from human state).

All status colors are used at low-alpha fills (`/20`) with full-alpha text and a `/30` border in pills.

### Type
**SF Pro** (Apple's system family, self-hosted in `fonts/`) — used at two optical sizes:
- **SF Pro Display** for ≥ 20px (Display, H1, H2).
- **SF Pro Text** for < 20px (H3, body, caption, micro).

**JetBrains Mono** for trace IDs, commit SHAs, DQL snippets, and any monospaced data. SF Mono is not licensable for non-Apple platforms; JetBrains Mono has the closest metrics. See `assets/ICONS-SUBSTITUTION.md`.

Scale (display→micro):
- `Display` 48px / 56 / -0.02em / 600 — only the dashboard's hero metric.
- `H1` 32px / 40 / -0.01em / 600 — page titles.
- `H2` 22px / 28 / -0.005em / 600 — card headers.
- `H3` 17px / 24 / 0 / 600 — section headers.
- `Body` 15px / 22 / 0 / 400 — default.
- `Body-strong` 15px / 22 / 0 / 500.
- `Caption` 13px / 18 / 0 / 400 — table cells, secondary text.
- `Micro` 11px / 16 / 0.04em / 600 / uppercase — pill labels, axis labels.
- `Mono` 13px / 20 / 0 / 450 — JetBrains Mono.

Numerals are tabular by default (`font-variant-numeric: tabular-nums`) so columns of counts and durations line up.

### Spacing
4px base grid. The system uses `0, 2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80`. Cards have **16px interior padding** on dense surfaces, **24px** on the agent's primary cards. Section gutters are **32px**.

### Corner radii
- `6px` — pills, small chips, dropdowns.
- `10px` — buttons, inputs, table cells.
- `14px` — nested cards, popovers.
- `18px` (the `rounded-2xl` of the brief) — glass panels, modals, the main control-room cards.
- `999px` — status pills.

### Borders
There are no hard borders. Every "border" is a 1px translucent inner stroke (`border: 1px solid rgba(255,255,255,0.08)`), often paired with a 1px translucent outer line via `box-shadow: inset 0 0 0 1px ... , 0 0 0 1px ...` to create the "etched" Apple feel against black.

### Shadows / elevation
Elevation on black isn't a drop shadow — black-on-black shadows are invisible. Instead, elevation is conveyed with:
1. A **lighter background** (the `surface` tier ladder),
2. A **translucent inner highlight** at the top edge — `box-shadow: inset 0 1px 0 rgba(255,255,255,0.06)`,
3. For modals and popovers, a **soft outer halo** of pure black `0 24px 60px rgba(0,0,0,0.6)` to push surrounding content down,
4. A **subtle backdrop blur** (`backdrop-filter: blur(40px) saturate(180%)`) so what's behind reads as out-of-focus, not just dimmer.

### Backgrounds
- **Pure flat black** is the default. No gradients on the page background.
- **Subtle vignettes** only in the highest-elevation modal scrim: `radial-gradient(ellipse at top, rgba(10,132,255,0.08), transparent 60%)` behind a critical-incident sheet. Used sparingly — once per session at most.
- **No imagery** on the dashboard surfaces. **No illustrations.** **No patterns.** **No textures.** The aesthetic is operational; decorative imagery would break the register.
- The only "imagery" is **video poster frames** for asset cards — these are full-bleed within their card, slightly desaturated (`saturate(0.85)`) with a soft dark overlay (`linear-gradient(to top, rgba(0,0,0,0.6), transparent 50%)`) so overlaid text reads.

### Animation
- **Apple's standard easing**: `cubic-bezier(0.4, 0, 0.2, 1)` for state changes; `cubic-bezier(0.16, 1, 0.3, 1)` for entrances ("springy" without bounce).
- **Durations**: 120ms for hover/focus, 220ms for menu open, 320ms for panel slide, 480ms for modal sheet. No animation longer than 480ms in the control room.
- **No bounces.** No elastic overshoot. Nothing playful.
- **Layout shifts are forbidden.** Status pills switch color in place; counters animate via a 80ms cross-fade, not a number-roll.
- **Reduced motion**: respect `prefers-reduced-motion: reduce` by collapsing all transitions to `<60ms` opacity-only changes.

### Hover, press, focus, disabled
- **Hover** (rows, list items): background steps from `surface` → `surfaceHover` (`#1c1c1e` → `#2c2c2e`). On the page background, hover adds a `rgba(255,255,255,0.04)` overlay.
- **Hover** (primary button): the fill stays the same; the inset top highlight brightens from `0.06` to `0.12`. **Buttons do not shift color on hover** — they brighten by 1 stop.
- **Press**: the element compresses by 1px via `transform: translateY(0.5px)` and dims by 4% via `filter: brightness(0.96)`. 80ms. Never a scale-down.
- **Focus**: 2px `#0A84FF` outline at 2px offset, on every interactive element. Never removed — this is an operations tool.
- **Disabled**: opacity 0.4, no pointer events, cursor `not-allowed`.

### Transparency and blur
**Glass is for what floats**, not for everything. The rule:
- **Floats over content** (toolbars, popovers, modals, the agent's incident card, sticky table headers) — get translucent surface + backdrop blur.
- **Embedded in layout** (sidebars, table rows, the page body) — get solid `surface` color. No blur. Blur on static layout is wasted GPU and reads as cheap.

### Imagery
When imagery does appear (poster frames for video assets), the treatment is **neutral, cool, slightly desaturated**. No grain. No warm filters. No vignettes on the imagery itself — vignetting happens in the surrounding card, not in the asset.

### Layout rules
- Persistent left sidebar (`240px`) — never collapses on desktop.
- Persistent top bar (`56px`) — sticky, translucent glass.
- Main content max width `1440px` content area inside a `1920px` design canvas; the page background extends to viewport but rules and tables align to the 1440 column.
- A right-side **inspector panel** (`360px`) slides in for selected entities (asset detail, incident detail). It's a peer panel, not a modal — the table behind stays interactive at reduced contrast.

---

## ICONOGRAPHY

The vibe is **SF Symbols, monochrome, light weight**. No filled glyphs (except status dots), no two-tone, no colorful icons.

- **Stroke weight 1.5px**, **24×24 viewBox**, **stroke `currentColor`**, **fill none** (with a few exceptions: status dots, the agent avatar). This matches SF Symbols' default Regular weight closely enough that a viewer's eye won't fight.
- **Source**: [Lucide](https://lucide.dev) loaded from CDN. Lucide's stroke style and proportions are the closest free analog to SF Symbols Regular. **This is a substitution** — true SF Symbols are not licensable for non-Apple platforms. Flagged in `assets/ICONS-SUBSTITUTION.md`.
- Pixel icons (`.png`) — **none**. Everything is SVG, inline or via Lucide's runtime.
- **No emoji** anywhere in the UI.
- **No unicode glyphs used as icons.** Bullets in lists are `•` (U+2022) but that's typographic, not iconographic.
- **Status dots** are filled 8px circles, the only place a solid colored circle appears in the design.
- **Brand mark**: a custom-drawn `studioflow.svg` (in `assets/`) — a four-bar group + a thin horizontal flow line, monochrome, lockup with the wordmark in Inter SemiBold tracking `-0.02em`. The mark scales from 16px (favicon row) to 80px (loading splash).

### Font substitutions to flag to the reader
- **SF Pro Display + SF Pro Text** are self-hosted in `fonts/`. No substitution.
- **SF Mono → JetBrains Mono.** SF Mono is not licensable for non-Apple platforms. JetBrains Mono is close in metrics; Geist Mono is an acceptable alternative.
- **SF Symbols → Lucide.** See above.

---

## Index — files in this design system

```
/                       ← project root
├── README.md           ← this file
├── SKILL.md            ← cross-compatible agent skill manifest
├── colors_and_type.css ← CSS variables for color + type tokens
├── fonts/              ← webfonts (Inter, JetBrains Mono — Google Fonts copies)
├── assets/             ← logos, icons, brand SVGs
│   ├── studioflow-logo.svg
│   ├── studioflow-mark.svg
│   ├── ICONS-SUBSTITUTION.md
│   └── (status-dot SVGs, poster placeholders)
├── preview/            ← Design System tab cards
│   ├── colors-*.html
│   ├── type-*.html
│   ├── spacing-*.html
│   └── components-*.html
└── ui_kits/
    └── control_room/   ← Studio Control Room UI kit
        ├── README.md
        ├── index.html  ← interactive prototype
        ├── *.jsx       ← components
        └── ...
```

Browse the upstream codebase for additional context — particularly `CLAUDE.md` — at <https://github.com/alanmaizon/studioflow>. If a later snapshot ships real Next.js components in `frontend/`, treat those as the source of truth over the recreations in `ui_kits/control_room/`.
