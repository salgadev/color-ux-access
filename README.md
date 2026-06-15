---
title: Color-UX-Access
emoji: 🔍
colorFrom: red
colorTo: green
sdk: gradio
sdk_version: "6.17.3"
app_file: app.py
python_version: "3.12"
dependencies: requirements.txt
---

# Color-UX-Access

**HF Build Small Hackathon** · Track: Backyard AI · ≤32B parameters · Gradio + HF Space

> 🔍 Test any webpage screenshot for colorblind accessibility issues — 10 CVD simulations + WCAG 2.1 report via 32B VLM.

**Live:** [salgadev-color-ux-access.hf.space](https://salgadev-color-ux-access.hf.space)
**Code:** [github.com/salgadev/color-ux-access](https://github.com/salgadev/color-ux-access)
**Built for:** [NARWALL](https://narwall.tech) — automated accessibility testing.

---

## How It Works

```
Screenshot (file upload or URL capture)
       │
       ▼
Stage 1: CVD Simulation (CPU) — 10 variants via DaltonLens
       │
       ▼
Stage 2: VLM Inference (GPU) — CohereLabs/aya-vision-32b → WCAG 2.1 JSON
       │
       ▼
Stage 3: WCAG Report — Severity · Criterion · Description · Remediation
```

**VLM:** [CohereLabs/aya-vision-32b](https://huggingface.co/CohereLabs/aya-vision-32b) via HF Router (OpenAI-compatible API).
**CVD:** 10 types via DaltonLens (Machado2009, Vienot1999, Brettel1997) + Rec.709 grayscale for achromatopsia.

See `docs/ARCHITECTURE.md` for detailed pipeline internals.

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
| Achromatopsia | Complete grayscale | ~0.003% |
| Achromatomaly | Partial grayscale | rare |

---

## Project Structure & Constraints

- All tests under `tests/` (e.g., `tests/test_*.py`)
- No root-level fix scripts (`apply_*fixes*.py`, `*_fix*.py`, `insert_cache.py`, etc.)
- Runtime logic in `app.py`, `server_app.py`, or clearly named helper modules
- TDD mandatory: write tests first, then implementation

---

## Quick Start

```bash
git clone https://github.com/salgadev/color-ux-access.git
cd color-ux-access
uv venv --python 3.12
source .venv/Scripts/activate
uv pip install -e ".[dev]"
cp .env.example .env   # add HF_TOKEN
pytest -m smoke         # verify setup
python app/app.py       # launch locally
```

See `docs/DEVELOPMENT.md` for full setup, dependency groups, and git workflow.

---

## Development workflow (agents & humans)

**Run the app**
```bash
uv run app.py
```
Gradio does **not** auto-reload on code changes. After any edit to `app.py` or UI-affecting modules, stop the server (`Ctrl+C`) and restart with the command above.

**E2E test flow (Nous Browser)**
```bash
# 1. Start the app (see above)
# 2. In another terminal, run the browser test against the local instance
pytest -m e2e --base-url=http://127.0.0.1:7860
```
Test steps: upload `tests/fixtures/UR.webp` → click **Analyze** → verify the CVD grid renders and the WCAG report panel shows criteria rows.

> Detailed contributor rules live in `agents.md`. This section covers the mechanical loop only.

---

## Documentation

| Doc | What it covers |
|-----|----------------|
| `docs/ARCHITECTURE.md` | System design, CVD pipeline, VLM prompt, Gradio 6 compat |
| `docs/DEVELOPMENT.md` | Setup, uv venv, dep groups, git workflow, code style |
| `docs/TESTING.md` | Test markers, fixtures, TDD pattern |
| `docs/DEPLOYMENT.md` | HF Space + Modal deploy, known issues |
| `docs/EVALUATION.md` | Sponsor prize matrix (full detail) |
| `docs/CVD_USER_AUDIT_MODEL.md` | CVD audit methodology (EN/ES) |

---

## Sponsor Prize Eligibility

| Sponsor | Prize | Status |
|---------|-------|--------|
| HuggingFace | $15,000 | ✅ Eligible — top project |
| OpenBMB (MiniCPM-V 4.6 swap) | $10,000 | 🔲 One-line model swap |
| Modal | $250 credits | ✅ Already deployed |
| Cohere | Prize support | ✅ Using aya-vision-32b |
| NVIDIA RTX 5080 ×2 | GPUs | ⚠️ Confirm Nemotron req |

**Required:** Demo video + social media post. See `docs/EVALUATION.md` for full matrix and bonus quests.

---

## Environment

Use `uv` for isolated venvs — prevents Hermes Agent interference. Install via pyproject.toml groups:

```bash
uv pip install -e "."          # core only (pillow, daltonlens, numpy)
uv pip install -e ".[dev]"     # + playwright, pytest
uv pip install -e ".[space]"   # + gradio, spaces, torch (for HF Space)
uv pip install -e ".[all]"     # everything
```