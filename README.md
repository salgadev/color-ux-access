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
dependencies: requirements_space.txt
---

# Color-UX-Access — HF Space

**Track:** Backyard AI · ≤32B parameters · Gradio app

> 🔍 Test any webpage screenshot for colorblind accessibility issues — 10 CVD simulations + WCAG 2.1 report via 32B VLM.

---

## Development Workflow

**Branch → PR, never push to main directly.**

```
git checkout -b fix/your-fix-name
# make changes, commit
git push origin fix/your-fix-name
gh pr create --fill --base main
```

All changes go through pull requests for review. TDD required: write failing tests first, verify GREEN before merging.

---

## Setup

### 1. Add your HF token

Go to **Settings → Variables and Secrets** and add:

| Variable | Value |
|----------|-------|
| `HF_TOKEN` | Your HF token (`hf_...`) from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

> First inference takes ~60–90s (model downloads + KV cache init). Subsequent calls are fast.

---

## Usage

1. **Capture** a screenshot of any webpage (OS screenshot tool, browser capture, etc.)
2. **Upload** the image file in the Space
3. **Get** CVD simulations + WCAG 2.1 accessibility report

---

## Architecture

```
Screenshot (file upload)
       ↓
┌──────────────────────────────────┐
│  Gradio app (Space GPU, T4)      │
│  @spaces.GPU(duration=120)       │
└──────────────────────────────────┘
       ↓
HF Router API → CohereLabs/aya-vision-32b
       ↓
WCAG JSON → Markdown report + CVD gallery
```

**VLM:** [CohereLabs/aya-vision-32b](https://huggingface.co/CohereLabs/aya-vision-32b) via HF Router (OpenAI-compatible).

**CVD:** 10 types via DaltonLens (Machado2009, Vienot1999, Brettel1997) + grayscale for Achromatopsia.

**Sponsor prize eligibility:**
- HuggingFace $15K (top project)
- OpenBMB $5K track (MiniCPM-V 4.6 swap planned)
- Modal $250 credits (all participants)
- NVIDIA RTX 5080 ×2 ⚠️ _requirement unconfirmed — asking organizers_

---

## ⚠️ Pending

- [ ] **Transfer Space to hackathon org** — `salgadev/color-ux-access` must move to `build-small-hackathon/color-ux-access`. Requires org admin to add pre-paid credits for t4-small hardware billing. Asked organizers on Discord 2026-06-06.

---

## CVD Types

| Type | Description |
|------|-------------|
| Protanopia | Red-blind (1% of males) |
| Deuteranopia | Green-blind (1% of males) |
| Tritanopia | Blue-blind (rare) |
| Protanomaly | Red-weak |
| Deuteranomaly | Green-weak |
| Tritanomaly | Blue-weak |
| Severe Protanopia | Full red-blind |
| Severe Deuteranopia | Full green-blind |
| Achromatopsia | Complete color blindness |
| Achromatomaly | Partial monochromacy |

---

## Project

Code + full docs: [github.com/salgadev/color-ux-access](https://github.com/salgadev/color-ux-access)

Built for **NARWALL** — automated accessibility testing via screen-reader and keyboard simulation.