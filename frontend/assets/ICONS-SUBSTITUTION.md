# Icon and font substitutions

The StudioFlow brief specifies an Apple/Cupertino aesthetic. SF Pro now ships in `fonts/` (full family, OTF). The other Apple-proprietary assets are not licensable for non-Apple platforms, so we substitute the closest free analogs:

| Apple asset | What's used here | Why |
|---|---|---|
| SF Pro Display / SF Pro Text | **SF Pro (self-hosted in `fonts/`)** — Regular/Medium/Semibold/Bold, both optical sizes | No substitution. Apple's own files. |
| SF Mono | **JetBrains Mono** (Google Fonts CDN) | SF Mono is not licensable for non-Apple platforms. JetBrains Mono has the closest proportions, designed for code, ligatures available. Geist Mono is an acceptable alternative. |
| SF Symbols | **[Lucide](https://lucide.dev)** loaded from CDN | Closest free icon system in stroke style, weight, and grid (24×24, 1.5px stroke). Used inline via `<i data-lucide="name">` or imported as SVG. |

## Iconography rules in this system

- 24×24 viewBox, 1.5px stroke, `stroke="currentColor"`, `fill="none"`.
- No filled glyphs except **status dots** (8px solid circles) and the **agent avatar** mark.
- No PNG icons, no emoji, no unicode glyphs as icons.
- Brand mark `studioflow-mark.svg` and logo lockup `studioflow-logo.svg` live in `assets/`.
- Status dots: `assets/dot-green.svg`, `dot-amber.svg`, `dot-red.svg`, `dot-indigo.svg`, `dot-neutral.svg`.

## Loading Lucide via CDN

```html
<script src="https://unpkg.com/lucide@latest"></script>
<i data-lucide="zap"></i>
<script>lucide.createIcons();</script>
```

Or import individual SVGs from <https://lucide.dev/icons/> if avoiding the runtime.
