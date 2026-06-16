# TRIBE v2 in-silico findings

Static GitHub Pages site publishing three in-silico neuroscience experiments on
[`facebook/tribev2`](https://huggingface.co/facebook/tribev2) — Meta's tri-modal
(video + audio + text) foundation model that predicts human fMRI responses.

**Live:** https://tinycrops.github.io/tribev2-findings-pages/

## Contents (`frontend/`)

- `index.html` — landing page; summarizes all three findings.
- `experiment.html` — *Does an ASCII-cat LoRA finetune change TRIBE's brain maps?*
  Uniform ~8% drift into the language network — not cat-specific, not visual. Two
  hypotheses refuted; null-swap control passed.
- `showcase.html` — *Reading ASCII art with a brain model.* The img2ascii realism
  ladder holds; the cross-modal convergence hint (finetune pulls ASCII-text toward
  visual cortex) was refuted at scale.

Reports are fully self-contained — figures are embedded as `data:` URIs, every number
is recomputed from saved `.npz` maps, and each cross-modal effect is guarded by a
null-swap control.

## Deployment

Plain HTML/CSS/JS, no build step. `frontend/` is deployed to GitHub Pages by
`.github/workflows/pages.yml` (Actions artifact upload). The pages are static, so no
backend is involved.
