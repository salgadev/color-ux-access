# Color-UX-Access

> 🎯 **HF Build Small Hackathon** — Backyard AI track · ≤32B parameters · Deployed as a Hugging Face Space

A Gradio web app that simulates how webpages look to people with color vision deficiencies (CVD) and uses a 32B VLM to audit WCAG accessibility issues — reporting findings against WCAG standards.

**The person it serves:** Someone with CVD (8% of men, 0.5% of women). They encounter sites daily that use color alone to convey meaning — error states, required fields, status indicators — and get no feedback that something is wrong. Color-UX-Access lets them paste any URL and see both the CVD simulations and a VLM-generated WCAG accessibility report.

---

## Quick Start

```bash
cd G:/AI/HERMES/color-ux-access

# Install dependencies
pip install -r requirements.txt
playwright install --with-deps

# Run locally
python app.py
# → Opens http://localhost:7860
```

**Requirements:** Python 3.11+, internet access (for VLM inference via HF Router API).

---

## What It Does

1. **Paste any URL** — Playwright captures a full-page screenshot
2. **10 CVD simulations** — Protanopia, Deuteranopia, Tritanopia, Achromatopsia (full + partial variants)
3. **32B VLM analysis** — CohereLabs/aya-vision-32b via HF Router API identifies color-accessibility issues
4. **WCAG report** — Findings mapped to WCAG 2.1 criteria (1.4.1, 1.4.3, 1.4.6, 1.4.11)

---

## Architecture

```
URL → Playwright screenshot (PIL Image)
         ↓
┌──────────────────────────────────────┐
│  Gradio UI (single-file app.py)      │
│  Mode toggle: HF Router / llama.cpp  │
└──────────────────────────────────────┘
         ↓
CVD simulation (DaltonLens, 10 types) → Gallery of 10 images
VLM inference (HF Router, 32B VLM)    → WCAG accessibility report
```

**VLM:** CohereLabs/aya-vision-32b via `https://router.huggingface.co/v1` (OpenAI-compatible)

**Local fallback:** Any vision GGUF model via llama.cpp server at `http://localhost:8080/v1`.

---

## Approach: Testing From the Perspective of the User

Color-UX-Access tests from the perspective of a colorblind user — mirroring how NARWALL tests from the perspective of screen reader and keyboard-only users.

The screenshot is the boundary. We capture the visual experience the way a colorblind user would encounter it, then a 32B VLM acts as an accessibility expert reviewing that simulated view. Findings are reported against WCAG criteria.

This makes analysis robust against site-specific structure changes — we're testing the visual experience, not the DOM.

---

## Testing

```bash
# Smoke tests (no GPU, no network)
python -m pytest tests/test_smoke.py -v

# Pipeline tests (full URL→report with mocked VLM)
python -m pytest tests/test_pipeline.py -v

# Full suite
python -m pytest tests/ -v
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

---

## Project Structure

```
color-ux-access/
├── AGENTS.md                    ← Hackathon goals, bonus points, WCAG reference
├── README.md                    ← This file
├── app.py                       ← Gradio app (VLM currently mocked)
├── vlm_inference.py             ← HF Router API: CohereLabs/aya-vision-32b
├── vlm_inference_llama.py       ← Local llama.cpp fallback
├── accessibility_report.py      ← WCAG report generator
├── custom_theme.py              ← Gradio theme
├── requirements.txt
├── BONUS_PLAN.md                ← Bonus point strategy (5 categories)
├── scripts.py                   ← Legacy Rhymes.ai/Aria scripts (ignore)
└── tests/
    ├── test_smoke.py            ← Import + build smoke
    └── test_pipeline.py         ← Full pipeline with mocked VLM
```

---

## WCAG Standards Used

| Criterion | Name | What it covers |
|-----------|------|---------------|
| 1.4.1 | Use of Color | Color cannot be the only means of conveying information |
| 1.4.3 | Contrast (Minimum) | 4.5:1 normal text, 3:1 large text |
| 1.4.6 | Contrast (Enhanced) | 7:1 normal text, 4.5:1 large text |
| 1.4.11 | Non-text Contrast | 3:1 for UI components and graphical objects |

---

## Bonus Points (What Scores Above the Bar)

Per hackathon judging criteria:

1. **Well-Tuned** — Fine-tuned model published on Hugging Face (LoRA or adapter)
2. **Off-Brand** — Custom frontend past default Gradio (CSS, interactive CVD slider)
3. **Llama Champion** — Model runs through llama.cpp runtime (local GPU)
4. **Sharing is Caring** — Dev trace shared as HF Dataset
5. **Field Notes** — Blog post or case study about what was built

See `AGENTS.md` → Bonus Points for implementation options per category.

---

## Sponsor Prize Reference

| Sponsor | Prize | Notes |
|---------|-------|-------|
| HuggingFace | $15,000 cash | Top awards |
| OpenAI | $10,000 cash + $100 Codex credits | First 1,000 participants |
| OpenBMB | $10,000 special awards | MiniCPM model projects (MiniCPM-V 4.6, MiniCPM-o 4.5) |
| NVIDIA | 2× RTX 5080 GPUs | Physical hardware |
| Modal | $250 credits all + $20,000 winners | Every participant |

See `AGENTS.md` → Hackathon Tracks & Prizes for full details.

---

## Reuse References

- **NARWALL** (`D:\CODE\narwall-selenium\`) — "test from perspective of assistive tech users" philosophy
- **gradio-huggingface-space skill** (`G:\AI\HERMES\skills\gradio-huggingface-space\`) — Gradio patterns, CVD simulation, WCAG reporting

---

## License

MIT