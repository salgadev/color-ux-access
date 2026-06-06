# Architecture — Color-UX-Access

> How the system works: screenshot → CVD simulation → VLM → WCAG report.
> Replaces `docs/AGENTS.md`. For deployment specifics, see `docs/DEPLOYMENT.md`.

---

## Overview

**Purpose:** Simulate how any webpage screenshot looks through the eyes of a colorblind user, then use a 32B VLM to audit it as an accessibility expert would — reporting findings against WCAG 2.1 standards.

**Serves:** A person with CVD (8% of men, 0.5% of women) who encounters sites daily using color alone to convey meaning — error states, required fields, status indicators.

**Philosophy:** The app is a proxy for the user's own eyes. It captures the visual experience the way a colorblind user would encounter it — not how the DOM is structured. This mirrors how NARWALL uses NVDA as a proxy for keyboard/screen reader users, but for color vision.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER FLOW                                │
│  OS Screenshot tool ──► Upload PNG ──► CVD Gallery + WCAG Report │
└─────────────────────────────────────────────────────────────────┘

Screenshot (file upload)
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 1: CVD Simulation  (CPU — instant, no GPU needed)         │
│  10 variants via app_space.py's deficiency_config (8 DaltonLens + 2 grayscale) │
│  → Gallery: original + protanopia, deuteranopia, tritanopia,                   │
│            protanomaly, deuteranomaly, tritanomaly,                            │
│            severe_protanopia, severe_deuteranopia,                             │
│            achromatopsia, achromatomaly                                        │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 2: VLM Inference (GPU — ~90s first call, <5s cached)      │
│                                                                  │
│  Local dev:    analyze_with_vlm() → HF Router API                │
│                → CohereLabs/aya-vision-32b                       │
│                                                                  │
│  HF Space:     @spaces.GPU(duration=120) wraps entire UI         │
│                same HF Router API → same model                   │
│                                                                  │
│  Modal:        upload_screenshot() → vlm_inference_fn(A10G)      │
│                same HF Router API → same model                   │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 3: WCAG Report  (format_wcag_report())                    │
│  JSON → Markdown with severity icons, WCAG links, remediation    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Entrypoint Decision

| Context | File to run | Screenshot source |
|---------|-------------|------------------|
| Local development | `python app/app.py` | Playwright (auto-capture URL) |
| HF Space | `python app_space.py` | User uploads PNG |
| Modal | `modal_app.py` | User uploads PNG |
| CLI VLM test | `python -m vlm.vlm_inference screenshot.png` | Pre-captured PNG |

---

## Package Layout

### `color_ux_access/` — Core (no Gradio dependency)

```
color_ux_access/
├── __init__.py         from .cvd_sim import simulate_cvd, CVD_VARIANTS
├── cvd_sim.py          DaltonLens wrapper, 7 types + grayscale
│                       Public API: simulate_cvd(image, cvd_type) -> PIL Image
└── capture.py          Playwright page → full-page screenshot
                        Public API: take_screenshot(page, url, timeout=60000) -> PIL Image
```

### `vlm/` — Vision Language Model inference

```
vlm/
├── vlm_inference.py          HF Router → aya-vision-32b (CLI tool + helper fns)
│                              API: load_model_api(), analyze_image_api()
├── vlm_inference_llama.py    llama.cpp GGUF → local vision model (offline)
│                              API: load_llama_model(), analyze_image_with_llama()
└── accessibility_report.py   WCAG report generation + markdown formatting
                               API: AccessibilityReport.generate_report(),
                                   AccessibilityReport.format_report_as_markdown()
```

### `app/` — Local dev Gradio app

```
app/
├── app.py              gr.Blocks — URL input → Playwright screenshot → CVD → VLM
└── custom_theme.py     ColorUXAccessTheme (accessible blue/gray, Inter font)
```

---

## VLM Prompt System

The VLM receives a structured prompt instructing it to return WCAG-specific JSON:

```
You are an accessibility expert specializing in colorblind user experience.
Analyze screenshots for WCAG 2.1 compliance issues.
For each finding, cite the specific success criterion (1.1.1, 1.4.1, 1.4.3, or 1.4.11).
Output a JSON object with this structure:
{
  "findings": [
    {
      "type": "Low Contrast | Color Only Information | Missing Text Alternative | Insufficient Non-Text Contrast",
      "wcag_criterion": "1.4.1 | 1.4.3 | 1.1.1 | 1.4.11",
      "description": "...",
      "severity": "critical | serious | moderate",
      "location": "Top-left, center, etc."
    }
  ],
  "summary": "Overall assessment",
  "passes": true/false
}
```

Expected response fields: `type`, `wcag_criterion`, `description`, `severity`, `location`, `summary`, `passes`.

---

## CVD Simulation Internals

```python
# color_ux_access/cvd_sim.py
from daltonlens import simulate
import numpy as np
from PIL import Image

# Singleton simulator (lazy init)
_simulator = simulate.Simulator_Machado2009()

_DEFFICIENCY_MAP = {
    'deuteranopia': simulate.Deficiency.DEUTAN,
    'protanopia': simulate.Deficiency.PROTAN,
    'tritanopia': simulate.Deficiency.TRITAN,
    # ...
}

_SEVERITY_MAP = {
    'deuteranopia': 1.0,    # dichromacy — full deficiency
    'deuteranomaly': 0.6,   # anomalous trichromacy — partial
    # ...
}

def simulate_cvd(image, cvd_type='deuteranopia') -> Image.Image:
    if cvd_type == 'achromatopsia':
        return _grayscale(image)
    deficiency = _DEFFICIENCY_MAP[cvd_type]
    severity = _SEVERITY_MAP[cvd_type]
    im_np = np.array(image, dtype=np.uint8)
    result_np = _simulator.simulate_cvd(im_np, deficiency, severity)
    return Image.fromarray(result_np)
```

Achromatopsia is grayscale via Rec.709 luma coefficients, not a DaltonLens simulator.

---

## Gradio 6 Compatibility

In Gradio 6, `theme` and `css` are `launch()` parameters, NOT `Blocks()` constructor parameters.

```python
# ✅ Correct (Gradio 6)
with gr.Blocks(title='Color-UX-Access') as demo:
    ...
demo.launch(
    theme=gr.themes.Base(primary_hue='blue', secondary_hue='gray'),
    css=":root { --color-primary: #1E88E5; }",
)

# ❌ Wrong (Gradio 5 pattern — will break in Gradio 6)
with gr.Blocks(title='Color-UX-Access', theme=custom_theme, css="...") as demo:
    ...
```

Test: `pytest tests/test_app_space.py::test_blocks_theme_not_in_constructor -v`

---

## WCAG Standards Referenced

| Criterion | Name | What it covers |
|-----------|------|---------------|
| 1.4.1 | Use of Color | Color cannot be the only means of conveying information |
| 1.4.3 | Contrast (Minimum) | 4.5:1 normal text, 3:1 large text |
| 1.4.6 | Contrast (Enhanced) | 7:1 normal text, 4.5:1 large text |
| 1.4.11 | Non-text Contrast | 3:1 for UI components and graphical objects |

---

## Testing Philosophy

Tests use a layered approach:

| Category | Marker | What it tests | Duration |
|----------|--------|---------------|----------|
| Smoke | `smoke` | Import, module load, CVD config, Gradio apps loadable | <10s |
| Pipeline | `pipeline` | Full image→CVD→WCAG report with mocked VLM | <30s |
| Slow | `slow` | Real VLM calls, needs HF_TOKEN | 60-90s |

**Source inspection tests** verify structural properties that mocks miss — e.g., `isinstance(file_obj, bytes)` check for GradioFile binary type, Modal app GPU config, Gradio 6 theme placement in `launch()` not `Blocks()`.

---

## Reuse from NARWALL

|| NARWALL artifact | What it contributes |
|-----------------|---------------------|
| `narwall-selenium/AGENTS.md` | "test from perspective of assistive tech users" philosophy |
| `narwall-selenium/docs/technology-readiness/REGRESSION_GUARDS.md` | WCAG mapping approach |
| `skills/gradio-huggingface-space/SKILL.md` | Gradio 6.x deployment patterns |

---

*See also: `docs/DEPLOYMENT.md` for HF Space and Modal specifics.*