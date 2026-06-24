# Aurora — Premium SaaS Landing Page Template

A modern, conversion-optimized landing page for SaaS products, startups, and apps.
Dark, premium aesthetic with a glassmorphic UI, built to convert visitors into trials.

![Aurora preview](preview.png)

## What's included

- ✅ **Single-file `index.html`** — drop it anywhere, it just works
- ✅ **11 conversion sections** — announcement bar, sticky nav, hero with product mockup, logo cloud, features grid, how-it-works, testimonials, pricing (with monthly/annual toggle), FAQ, final CTA, footer
- ✅ **Fully responsive** — tested at 375 / 768 / 1024 / 1440px
- ✅ **Accessible** — keyboard focus states, semantic HTML, `prefers-reduced-motion` support, SVG icons (no emoji)
- ✅ **Zero build step** — Tailwind via CDN + Google Fonts; no install required
- ✅ **Easy to customize** — colors and fonts are defined in one config block

## Quick start

1. Open `index.html` in any browser — that's it.
2. To customize, edit the `tailwind.config` block in `<head>`:
   - **Colors** → `theme.extend.colors` (`ink` = neutrals, `accent` = brand)
   - **Fonts** → `theme.extend.fontFamily`
3. Replace the copy, links, and logo (the inline SVG in the nav).

## Customizing the brand color

Change the two accent hex values in the `accent` palette and the `grad-btn` /
`grad-text` gradients in the `<style>` block. Everything else inherits from those.

## Production build (optional)

The Play CDN is perfect for previews and small sites. For production, install
Tailwind locally so unused styles are purged and the page loads faster:

```bash
npm create vite@latest my-site
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Then move the `<style>` rules into your CSS entry and the config into `tailwind.config.js`.

## License

Commercial use permitted under the included license (`LICENSE.md`). You may use
this template for unlimited personal and client projects.

---

Made with the **ui-ux-pro-max** design system. Questions or custom work? Get in touch.
