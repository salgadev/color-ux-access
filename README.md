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
tags:
  - track:backyard
  - sponsor:openbmb
  - sponsor:modal
  - achievement:offgrid
---

# Color-UX-Access

**HF Build Small Hackathon** · Track: Backyard AI · ≤32B parameters · Gradio + HF Space

[![HF Space](https://img.shields.io/badge/%F0%9F%A4%97-Space-blue)](https://huggingface.co/spaces/build-small-hackathon/color-ux-access)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)

> 🔍 Test any webpage screenshot for colorblind accessibility issues — 8 CVD simulations + WCAG 2.1 report via MiniCPM-v-4.6.

**Live:** [salgadev-color-ux-access.hf.space](https://salgadev-color-ux-access.hf.space)
**Code:** [github.com/salgadev/color-ux-access](https://github.com/salgadev/color-ux-access)
**Built for:** [NARWALL](https://narwall.tech) — automated accessibility testing.

---

## How It Works

```
Screenshot (file upload or URL capture)
       │
       ▼
Stage 1: CVD Simulation (CPU) — 8 variants via DaltonLens
       │
       ▼
Stage 2: VLM Inference (GPU) — MiniCPM-v-4.6 via Modal → WCAG 2.1 JSON
       │
       ▼
Stage 3: WCAG Report — Severity · Criterion · Description · Remediation
```

**VLM:** [MiniCPM-v-4.6](https://huggingface.co/openbmb/MiniCPM-V-4_6) (~4B params) served via Modal GPU endpoint.
**Endpoint:** Configured via `MODAL_INFERENCE_URL` environment variable.
**CVD:** 10 types via DaltonLens (Machado2009, Vienot1999, Brettel1997) + Rec.709 grayscale for achromatopsia.

See `docs/ARCHITECTURE.md` for detailed pipeline internals.

---

## CVD Types Supported

<details>
<summary><b>10 variants — click to expand</b></summary>

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

</details>

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
uv run app.py           # launch locally
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

## Prize Eligibility

| Sponsor / Category       | Prize                         | Status                             |
|--------------------------|-------------------------------|------------------------------------|
| HuggingFace              | $15,000 cash prize pool       | ✅ Eligible — top project           |
| OpenBMB (MiniCPM-V 4.6)  | $2,500               | ✅ Already deployed                 |
| Modal                    | $10,000 credits               | ✅ Already deployed                 |
| 🐜 Tiny Titan            |  (1500)  | ✅ Eligible (≤ 4B parameters model) |
| 🎴 Judges' Wildcard      | $1,000                        | ✅ Eligible                         |
| 🎬 Best Demo             | $1,000                        | ✅ Eligible                         |

**Required**
- ✅ Gradio App: (Space)[https://huggingface.co/spaces/build-small-hackathon/color-ux-access]
- ✅ Demo video: (YouTube)[https://www.youtube.com/watch?v=ynwuZNcqRtY] 
- ✅ Social Media Post: [LinkedIn](https://www.linkedin.com/posts/salgadev_build-small-hackathon-build-small-hackathon-share-7472421346992476161--5sG/)
---

## Environment

<details>
<summary><b>uv install groups</b></summary>

Use `uv` for isolated venvs — prevents Hermes Agent interference. Install via pyproject.toml groups:

```bash
uv pip install -e "."          # core only (pillow, daltonlens, numpy)
uv pip install -e ".[dev]"     # + playwright, pytest
uv pip install -e ".[space]"   # + gradio, spaces, torch (for HF Space)
uv pip install -e ".[all]"     # everything
```

</details>

## Examples

### Form Validation (`form_validation.png`)

Errors being conveyed using color alone:

Any page with form fields uses validation to check if input meets requirements. When it doesn't, the fields must display errors so the user is given context to correct and resubmit. If color is the only indicator, colorblind users miss these cues entirely.

[Source: deque.com](https://deque.com)

### Among Us UI (`amongos.jpg`)

The standard palette is fundamentally unplayable without color-blind mode — critical distinctions like red/green, blue/purple, and cyan/white vanish under specific vision conditions. Without inclusive design features like the available color-blind mode, the core social deduction mechanics fail for a substantial portion of the global audience.

[Source: uxdesign.cc](https://uxdesign.cc/the-importance-of-colorblind-friendly-design-case-study-among-us-dcd042c87b9)

### Status Indicators (`online_users.webp`)

If color is the only thing changing, it's inaccessible. These indicators look the same to many colorblind people, making them virtually useless.

[Source: Medium / Queer Design Club](https://medium.com/queer-design-club/going-beyond-color-9d3830559e10)

## Resources

- [Smashing Magazine: Designing for Colorblindness](https://www.smashingmagazine.com/2024/02/designing-for-colorblindness/)


