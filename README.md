---
title: Color-UX-Access
emoji: 🔍
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 6.0.0
app_file: app.py
python_version: "3.12"
hardware: t4-small
dependencies: requirements.txt
---

# Color-UX-Access

**HF Build Small Hackathon** · Track: Backyard AI · ≤32B parameters · Gradio + HF Space

> 🔍 Test any webpage screenshot for colorblind accessibility issues — 10 CVD simulations + WCAG 2.1 report via 32B VLM.

**Live:** [salgadev-color-ux-access.hf.space](https://salgadev-color-ux-access.hf.space)
**Code:** [github.com/salgadev/color-ux-access](https://github.com/salgadev/color-ux-access)
**Built for:** [NARWALL](https://narwall.tech) — automated accessibility testing via screen-reader and keyboard simulation.

---

## Quick Start

```bash
git clone https://github.com/salgadev/color-ux-access.git
cd color-ux-access

# Isolated venv (prevents Hermes Agent environment pollution)
uv sync --python 3.12

# Local dev: file upload (default)
python app.py

# Local dev: URL capture via Playwright (optional mode)
python app.py --url

# Tests
pytest -m smoke        # fast: imports + build checks
pytest                 # full suite (smoke + pipeline, no slow)
```

---

## How It Works

```
Screenshot (file upload or URL capture)
       │
       ▼
┌─────────────────────────────────────┐
│  Stage 1: CVD Simulation (CPU)      │
│  10 variants: deuteranopia,         │
│  protanopia, tritanopia,            │
│  deuteranomaly, protanomaly,        │
│  tritanomaly, severe_deuteranopia,  │
│  severe_protanopia, achromatopsia,  │
│  achromatomaly                      │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Stage 2: VLM Inference (GPU)       │
│  CohereLabs/aya-vision-32b via      │
│  Hugging Face Router API            │
│  → WCAG 2.1 JSON findings           │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Stage 3: WCAG Report (Markdown)    │
│  Severity · WCAG criterion ·        │
│  description · remediation          │
└─────────────────────────────────────┘
```

**VLM:** [CohereLabs/aya-vision-32b](https://huggingface.co/CohereLabs/aya-vision-32b) via HF Router (OpenAI-compatible API).
**CVD:** 10 types via DaltonLens (Machado2009, Vienot1999, Brettel1997) + Rec.709 grayscale for achromatopsia.

---

## CVD Types Supported

| Type | Description | Prevalence |
|------|-------------|-----------|
| Deuteranopia | Red-green (green-deficient) | ~1% males |
| Protanopia | Red-green (red-deficient) | ~1% males |
| Tritanopia | Blue-yellow | rare |
| Deuteranomaly | Red-green (green-weak) | ~5% males |
| Protanomaly | Red-green (red-weak) | ~1% males |
| Tritanomaly | Blue-yellow (weak) | rare |
| Severe Deuteranopia | Full green-deficient | — |
| Severe Protanopia | Full red-deficient | — |
| Achromatopsia | Complete grayscale (rod monochromacy) | ~0.003% |
| Achromatomaly | Partial grayscale | rare |

---

## Documentation

| Doc | What it covers |
|-----|----------------|
| `docs/DEVELOPMENT.md` | Setup, uv venv, testing, git workflow |
| `docs/ARCHITECTURE.md` | System design, CVD pipeline, VLM prompt |
| `docs/DEPLOYMENT.md` | HF Space deploy, Modal deploy, sponsor prizes |
| `docs/TESTING.md` | Test markers, fixtures, TDD pattern |

---

## Sponsor Prize Eligibility

| Sponsor | Prize | Status |
|---------|-------|--------|
| HuggingFace | $15,000 | ✅ Eligible — top project |
| OpenBMB (MiniCPM-V 4.6 swap) | $10,000 | 🔲 One-line model swap → $5K |
| Modal | $250 credits | ✅ Deployed |
| Cohere | Prize support | ✅ Using aya-vision-32b |
| NVIDIA RTX 5080 ×2 | GPUs | ⚠️ Confirm Nemotron requirement |

**Required to qualify:** Demo video + social media post.

---

## Environment & Dependencies

**Local dev:** `uv sync --python 3.12` — manages all dependencies via `pyproject.toml`, produces `uv.lock`.

**HF Spaces deployment:** `requirements.txt` is generated from `uv.lock` via `uv export --format requirements-txt --output-file requirements.txt`. Never hand-edit it — it is a generated artifact.

```bash
# Add a new dependency → edit pyproject.toml, then regenerate:
uv add some-package          # or manually edit pyproject.toml
uv sync                      # updates uv.lock
uv export --format requirements-txt --output-file requirements.txt  # regenerate for Spaces
git commit pyproject.toml uv.lock requirements.txt
```

| Context | File | Tool |
|---------|------|------|
| Local dev / CI | `pyproject.toml` + `uv.lock` | `uv` |
| HF Spaces deployment | `requirements.txt` | `pip` (Spaces runtime) |

---

## ⚠️ Pending

- [ ] **Add HF_TOKEN to Space secrets** — Space is live but VLM won't work without it
- [ ] **Demo video + social post** — required to qualify for hackathon
- [ ] **Confirm NVIDIA Nemotron requirement** — asking organizers
- [ ] **Transfer Space to hackathon org** — must move to `build-small-hackathon/color-ux-access`
- [ ] **OpenBMB MiniCPM-V swap** — $5K prize, one-line model change in MODELS dict
