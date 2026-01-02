# Assets Policy (PR9)

This repository is public. Binary assets increase license, size, and compliance
risk. This policy defines strict guardrails for assets and placeholders.

## Fonts (Hard Policy)

- Allowed: Google Fonts via CDN only (HTML `<link>` or CSS `@import`).
- Forbidden: any font files in the repo, even samples.
- Forbidden extensions: `.ttf`, `.otf`, `.woff`, `.woff2`, `.eot`, `.ttc`.
- `assets/fonts/` is locked to `README.md` only.

## Assets Directory Rules

- `assets/` must exist with the baseline skeleton.
- Max per-file size under `assets/`: 1MB (hard fail).
- Max total size under `assets/`: 5MB (hard fail).
- No symlinks under `assets/` (hard fail).
- Placeholder README guidance: keep `README.md` files <= 10KB and text only (UTF-8; no null bytes).

## Deterministic Paths Only

- Use relative paths for any asset references.
- No path traversal allowed (no `..` components).
