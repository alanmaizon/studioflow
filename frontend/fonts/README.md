# fonts/

Self-hosted webfonts for the StudioFlow design system.

## What's here

**SF Pro** — Apple's system font family, supplied by the project owner. Full set of weights (Ultralight → Black) for both optical sizes (Display ≥ 20px, Text < 20px) plus Rounded.

The system actually loads only four weights from each optical size: **400 Regular, 500 Medium, 600 Semibold, 700 Bold**. The rest are available if you need them — extend the `@font-face` block at the top of `../colors_and_type.css`.

## What's deliberately *not* here

- **SF Mono** — not licensable for non-Apple platforms. The system uses **JetBrains Mono** (currently loaded from Google Fonts CDN). To self-host, grab the woff2s from <https://fonts.google.com/specimen/JetBrains+Mono> and update the mono `@font-face` rule in `../colors_and_type.css`.
- **SF Symbols** — replaced with [Lucide](https://lucide.dev). See `../assets/ICONS-SUBSTITUTION.md`.

## Licensing reminder

SF Pro is provided by Apple under their font usage terms. Make sure the deployment context (internal demo, Apple-employed developers, etc.) complies — see <https://developer.apple.com/fonts/>.
