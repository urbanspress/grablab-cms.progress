# GrabLab CMS `v1.5.0` — Admin UI & Universal Profile Studio

### Release Type & Affected Layers
- **Release Version & SemVer Tier:** `v1.5.0` (`MINOR 1.x.0 — Backwards-Compatible Feature Release`)
- **Affected Layer(s):** `Flagship Zero-Plugin CMS` (`urbanspress/grablab-cms`)
- **Neighboring Layer Upgrade Required?** `No — 100% drop-in compatible` with frozen GRAB `v1.1.0`, Grex JS `v1.0.0`, Grex Theme Builder `v1.0.0`, and Groxy AI (`>= v0.1.0`)

| Ecosystem Layer | Repository | Required Version Range | Touched in This Release? | Neighbor Upgrade Required? |
|---|---|---|---|---|
| **Core Language, Bytecode VM & Grisp Server** | `urbanspress/grab` | `>= v1.1.0 (< v2.0.0)` | `No` | `No` |
| **Reactive Frontend Runtime & 20-Element Library** | `urbanspress/grex-js` | `>= v1.0.0 (< v2.0.0)` | `No` | `No` |
| **Flagship Zero-Plugin CMS** | `urbanspress/grablab-cms` | `>= v1.5.0 (< v2.0.0)` | `Yes` (CMS routes, admin assets and tests) | `No` |
| **Exclusive `mode: "visual"` Theme & Studio** | `urbanspress/grex-builder` | `>= v1.0.0 (< v2.0.0)` | `No` | `No` |
| **Autonomous Design, Content & SEO Agent** | `urbanspress/groxy-ai` | `>= v0.1.0` | `No` | `No` |


## What changed

Open **My Profile** from the account menu to edit your display name, choose from six local portraits, check your permissions or export account details. Security lets you change a password and sign out other devices. The header adds distinct Posts and Pages links, local Urbanist fonts and a Light/Dark toggle. All four roles use the same six-tab layout.

## Verification

Stage 4 Pre-Release Cross-Layer Security & Contract Sign-Off (`PASS`). The owner approved the live Light and Dark views. Both platform configurations passed, all 20 GRAB sources matched canonical formatting, and 20 templates passed static checks. All three DOM audits and seven Python suites passed, including concurrent checkout, stock, coupon and author import tests.

## Assets

The source ZIP includes the CMS application, templates, assets, migrations and operator documentation. The PDF walks through the new profile. SHA256SUMS.txt lists the ZIP, guide and these notes. The release uses the existing database schema.
