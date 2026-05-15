---
name: studioflow-design
description: Use this skill to generate well-branded interfaces and assets for StudioFlow — an Apple/Cupertino-style internal SRE control room for a high-volume media production pipeline. Contains color + type tokens, fonts, brand assets, iconography rules, and a working UI kit recreation of the Studio Control Room (pipeline overview, asset table, agent incident card, approval gate). Use either for production designs or for throwaway prototypes/mocks/decks.
user-invocable: true
---

Read the `README.md` file within this skill first — it carries the full content + visual + iconography foundations. Then explore:

- `colors_and_type.css` — CSS variables (color tokens, type scale, radii, spacing, elevation, motion). Import or copy into new work.
- `assets/` — brand mark, logo lockup, status dots, icon substitution notes (`ICONS-SUBSTITUTION.md`).
- `fonts/` — webfont files (currently linked via Google Fonts CDN inside `colors_and_type.css`; drop SF Pro woff2 here if licensed).
- `preview/` — design-system specimen cards (one concept per file: surfaces, foreground ladder, accent, status, type, spacing, radii, elevation, buttons, pills, inputs, glass panel, asset row, incident card, tool stream, pipeline summary, approval gate).
- `ui_kits/control_room/` — a working click-thru recreation of the Studio Control Room. Read its `README.md` for what's interactive. Components are React/JSX, loaded via Babel in the browser; reuse `ui.jsx` primitives (`Button`, `StatusPill`, `Pill`, `Dot`, `Icon`, `GlassPanel`, `Card`, `Kbd`) and copy whole screens or rows when prototyping new flows.

## When acting on this skill

- If creating visual artifacts (slides, mocks, throwaway prototypes), copy the assets you need out into a new working folder and write static HTML files that link `colors_and_type.css`. Do not invent new colors — the palette is fixed (true-black background, Apple system colors for status, macOS Blue accent).
- If working on production code: pull tokens from `colors_and_type.css`, lift component shapes from `ui_kits/control_room/`, and keep the content rules from the README's CONTENT FUNDAMENTALS section (terse SRE voice, sentence case, uppercase only on status pills, no emoji, every agent claim cites a trace ID or commit SHA).
- The aesthetic register is **operational, not marketing.** No hero gradients, no decorative imagery, no playful microcopy. If in doubt, make it terser and more legible at small sizes.
- When you don't have an asset, use a placeholder — do not draw your own SF-Symbols-style icons from scratch. Pull from Lucide via CDN (`https://unpkg.com/lucide@latest`) and follow the 1.5-stroke / 24-viewBox / `currentColor` rules.

## If the user invokes this skill without specific guidance

Ask what they want to build — a new control-room screen, a deck describing the system, a marketing landing for the agent, or a feature spec UI. Ask whether they want options/variations, what scale they need (dashboard panel vs. full screen vs. slide), and whether the deliverable is throwaway or shippable. Then act as an expert designer who outputs HTML artifacts (or production code) grounded in this design system.

## Upstream sources

- Product spec, architecture, demo script: <https://github.com/alanmaizon/studioflow> — particularly `CLAUDE.md` and `docs/demo-script.md`. Browse if you need ground truth on services, state machine, or agent tool list before designing new flows.
