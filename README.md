# Color-UX-Access

> 🎯 **HF Build Small Hackathon** — Backyard AI track · ≤32B parameters · Deployed as a Hugging Face Space

A Gradio web app that uses a 32B vision-language model (VLM) to audit webpages for colorblind accessibility issues — simulating 10 types of color vision deficiency (CVD) and reporting WCAG 2.1 findings.

**The person it serves:** Someone with CVD (8% of men, 0.5% of women). They encounter sites daily that use color alone to convey meaning — error states, required fields, status indicators. Color-UX-Access lets them upload a screenshot and see both CVD simulations and a VLM-generated WCAG accessibility report.

---

## Quick Start

```bash
git clone https://github.com/salgadev/color-ux-access.git
cd color-ux-access

# Install dependencies
pip install -r requirements.txt

# Run locally (Modal deployment for production)
python app/app.py
# → Opens http://localhost:7860
```

**Requirements:** Python 3.11+, `HF_TOKEN` environment variable (get yours at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)).

---

## What It Does

1. **Upload a screenshot** — capture any webpage with your OS screenshot tool, upload the image
2. **10 CVD simulations** — Protanopia, Deuteranopia, Tritanopia, Achromatopsia (full + partial variants) via DaltonLens + colorspacious
3. **32B VLM analysis** — CohereLabs/aya-vision-32b via HF Router API identifies color-accessibility issues
4. **WCAG report** — Findings mapped to WCAG 2.1 criteria (1.1.1, 1.4.1, 1.4.3, 1.4.11)

---

## Architecture

```
User screenshot (OS capture tool)
         ↓
gr.File (type="binary") → bytes
         ↓
┌──────────────────────────────────────┐
│  Gradio UI (Modal @asgi_app)         │
│  Single sticky container             │
└──────────────────────────────────────┘
         ↓
upload_screenshot (CPU) → vlm_inference_fn (A10G GPU)
         ↓
HF Router API → CohereLabs/aya-vision-32b
         ↓
WCAG JSON report → Gradio JSON output
```

**VLM:** CohereLabs/aya-vision-32b via `https://router.huggingface.co/v1` (OpenAI-compatible).

**Local fallback:** Any vision GGUF model via llama.cpp server at `http://localhost:8080/v1` (see `vlm/vlm_inference_llama.py`).

---

## Approach: Testing From the Perspective of the User

Color-UX-Access tests from the perspective of a colorblind user — mirroring how NARWALL tests from the perspective of screen reader and keyboard-only users.

The screenshot is the boundary. We capture the visual experience the way a colorblind user would encounter it, then a 32B VLM acts as an accessibility expert reviewing that simulated view. Findings are reported against WCAG criteria.

This makes analysis robust against site-specific structure changes — we're testing the visual experience, not the DOM.

---

## Testing

```bash
# Full TDD suite (14 passing tests)
python -m pytest tests/ -v

# Smoke tests only
python -m pytest tests/test_smoke.py -v
```

---

## Deployment

### Hugging Face Space (hackathon target)

1. Push this repo to GitHub
2. Create a new HF Space: [huggingface.co/new-space](https://huggingface.co/new-space)
3. Select **Gradio** as the SDK
4. Link your GitHub repo
5. Set `HF_TOKEN` in Space secrets (Settings → Variables and Secrets)
6. Wait for build (~5 min) — app is live at `https://<space-name>.hf.space`

### Modal (alternative)

```bash
modal deploy color_ux_access/modal_app.py
```

---

## Project Structure

```
color-ux-access/
├── app/                        ← Gradio app + theme
│   ├── app.py
│   └── custom_theme.py
├── color_ux_access/            ← Core package
│   ├── capture.py              ← Screenshot capture (Playwright + PIL)
│   └── modal_app.py            ← Modal ASGI deployment
├── vlm/                        ← VLM inference backends
│   ├── vlm_inference.py        ← HF Router: CohereLabs/aya-vision-32b
│   ├── vlm_inference_llama.py  ← llama.cpp fallback
│   └── accessibility_report.py ← WCAG report generator
├── tests/                      ← TDD suite
│   ├── test_smoke.py           ← Import + build smoke
│   ├── test_capture.py         ← Screenshot capture
│   ├── test_modal_app.py       ← Modal app structure
│   └── test_gradio_binary.py   ← Gradio bytes/file regression
├── docs/
│   ├── AGENTS.md               ← Hackathon goals, WCAG reference
│   └── BONUS_PLAN.md           ← Bonus point strategy
├── .env.example                ← Environment variable template
├── requirements.txt
└── README.md
```

---

## WCAG Standards Used

| Criterion | Name | What it covers |
|-----------|------|---------------|
| 1.1.1 | Non-text Content | Images, icons must have text alternatives |
| 1.4.1 | Use of Color | Color cannot be the only means of conveying information |
| 1.4.3 | Contrast (Minimum) | 4.5:1 normal text, 3:1 large text |
| 1.4.11 | Non-text Contrast | 3:1 for UI components and graphical objects |

---

## Bonus Points (What Scores Above the Bar)

Per hackathon judging criteria:

1. **Well-Tuned** — Fine-tuned model published on Hugging Face (LoRA or adapter)
2. **Off-Brand** — Custom frontend past default Gradio (CSS, interactive CVD slider)
3. **Llama Champion** — Model runs through llama.cpp runtime (local GPU)
4. **Sharing is Caring** — Dev trace shared as HF Dataset
5. **Field Notes** — Blog post or case study about what was built

See `docs/AGENTS.md` → Bonus Points for implementation options per category.

---

## Sponsor Prize Reference

| Sponsor | Prize | Notes |
|---------|-------|-------|
| HuggingFace | $15,000 cash | Top awards |
| OpenAI | $10,000 cash + $100 Codex credits | First 1,000 participants |
| OpenBMB | $10,000 special awards | MiniCPM model projects |
| NVIDIA | 2× RTX 5080 GPUs | Physical hardware |
| Modal | $250 credits all + $20,000 winners | Every participant |

See `docs/AGENTS.md` → Hackathon Tracks & Prizes for full details.

---

## License

MIT