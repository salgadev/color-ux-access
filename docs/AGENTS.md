# AGENTS.md — Color-UX-Access

> **HF Build Small Hackathon** · Track: Backyard AI · ≤32B parameters · Gradio + HF Space

---

## What This Project Is

A Gradio web app that simulates how any webpage looks through the eyes of a colorblind user, then uses a 32B VLM to audit it as an accessibility expert would — and reports findings against WCAG standards.

**Serves:** A person with CVD (8% of men, 0.5% of women) who encounters sites daily using color alone to convey meaning — error states, required fields, status indicators. They need to know if a site works for them before trusting it.

**Philosophy:** The app is a proxy for the user's own eyes. It does not navigate or interact with the page — it captures how the page looks and what a sighted accessibility expert (the VLM) would conclude from that view. This mirrors how NARWALL uses NVDA as a proxy for keyboard/screen reader users, but for color vision.

**Hackathon goal:** Deployed HF Space + real demo + social post. Everything works end-to-end. Nothing mocked in the demo.

---

## Hackathon Tracks & Prizes

### Tracks

| Track | Theme |
|-------|-------|
| **Backyard AI** (primary) | Solve a real problem for someone specific. Measurable improvement. |
| **Thousand Token Wood** | Creative, playful, delightful AI experiences. Joyful is the bar. |

### Sponsor Prize Pool

| Sponsor | Prize | Condition |
|---------|-------|-----------|
| **HuggingFace** | $15,000 cash | Top awards |
| **OpenAI** | $10,000 cash + $100 Codex credits | First 1,000 participants |
| **OpenBMB** | $10,000 special awards | MiniCPM model usage (MiniCPM-V 4.6, MiniCPM-o 4.5) |
| **NVIDIA** | 2× RTX 5080 GPUs | Top projects |
| **Modal** | $250 credits all + $20,000 winners | Every participant |
| **Cohere** | Prize support | |
| **Black Forest Labs** | Prize support | |

### Hackathon Rules

- Model ≤32B total parameters
- Must be a Gradio app hosted as a HF Space
- Demo video + social media post required to qualify
- Build period: June 5–15, 2026

---

## Bonus Points (Hackathon Scoring Above the Bar)

These are what gets judged above a working baseline. Per `BONUS_PLAN.md`:

### Bonus 1: Well-Tuned — Fine-tuned model published on Hugging Face

- Publish a LoRA or fine-tuned adapter on HF Hub
- Train on accessibility-issue examples from known inaccessible sites
- E.g. `salgadev/color-ux-access-vlm` — a specialized accessibility analysis adapter

**Effort:** High. **Impact:** High (impressive demo + judges love model work).

### Bonus 2: Off-Brand — Custom frontend past default Gradio look

- Custom CSS + HTML in Gradio Blocks
- Interactive CVD comparison slider
- Custom color palette matching accessibility theme
- JavaScript for smooth image gallery transitions

**Effort:** Medium. **Impact:** High (first impression matters in demos).

### Bonus 3: Llama Champion — Model runs through llama.cpp runtime

- llama.cpp server serving a vision GGUF locally
- AMD GPU Vulkan support
- 4-bit quantization for speed
- Hybrid: vision on transformers, text on llama.cpp

**Effort:** Medium. **Impact:** Medium (impressive but HF API is simpler for demo).

### Bonus 4: Sharing is Caring — Shared agent trace on Hub

- Save development conversation logs to HF Dataset
- Organize by phase: screenshot capture → CVD sim → VLM analysis → report
- Include code snippets, decisions, and lessons learned

**Effort:** Low. **Impact:** Medium (low effort, shows process).

### Bonus 5: Field Notes — Blog post or report about what you built

- Technical blog on huggingface.co/blog
- Case study: problem → approach → WCAG findings → lessons
- Video walkthrough of the analysis pipeline

**Effort:** Medium. **Impact:** Medium (amplifies social reach).

---

## Approach: Testing From the Perspective of the User

This mirrors the NARWALL philosophy of testing from the perspective of assistive technology users — but for color vision.

**NARWALL pattern:** NVDA captures what a screen reader user experiences → agent reasons about it → findings reported against WCAG.

**Color-UX-Access pattern:**
1. Playwright captures what the page looks like (not how it's structured)
2. DaltonLens simulates how colorblind users see it (10 variants)
3. VLM acts as an accessibility expert reviewing the simulated view
4. Report maps findings to WCAG criteria

The screenshot is the boundary. We don't read the DOM — we capture the visual experience the way a colorblind user would encounter it. This makes the analysis robust against site-specific structure changes.

---

## What Makes a Good Demo

1. **Real URL, real analysis** — no mocks, no stubs, no "example.com"
2. **Specific CVD type named** — "this site is failing protanopia users because the error state is red-only"
3. **WCAG criterion cited** — "1.4.1 Use of Color: color cannot be the only means"
4. **Remediation shown** — VLM report includes what to fix
5. **Before/after CVD comparison** — interactive slider showing original vs simulated view

---

## Testing (Simple, No TRL)

Two test categories for a POC:

### A. Smoke Tests (`tests/test_smoke.py`)

No network, no GPU. Import + build checks:
```python
def test_imports():
    import color_ux_access.app  # full app imports
    from daltonlens import simulate
    from playwright.sync_api import sync_playwright

def test_cvd_simulators():
    from color_ux_access.app import deficiency_config
    assert len(deficiency_config) == 8
    # plus achromatopsia variants
```

### B. Pipeline Tests (`tests/test_pipeline.py`)

Test the full URL→report pipeline with mocked VLM:
```python
def test_url_to_report_pipeline(mocked_vlm):
    img, gallery, report = create_accessibility_report("https://example.com")
    assert img is not None
    assert len(gallery) == 10
    assert "WCAG" in report or "accessibility" in report.lower()
```

No source inspection — this is a single-file Gradio app, not a framework. The risk surface is different from narwall-selenium.

---

## Active Tasks

- [x] **T1:** Screenshot capture → `color_ux_access/capture.py` (Playwright + PIL) — working locally
- [x] **T2:** Wire VLM into `color_ux_access/modal_app.py` — `upload_screenshot.remote()` → `vlm_inference_fn` (A10G GPU) → HF Router API → aya-vision-32b — deployed and returning JSON
- [ ] **T3:** Verify real VLM response quality — confirm WCAG findings are meaningful, not generic
- [ ] **T4:** CVD simulation — 10-type colorblind simulation in UI (DaltonLens + colorspacious)
- [ ] **T5:** HF Space deploy — primary hackathon target
- [ ] **T6:** Bonus 2 (Off-Brand) — custom Gradio theme past default, CVD comparison slider
- [ ] **T7:** Bonus 5 (Field Notes) — blog post on huggingface.co/blog
- [ ] **T8:** Demo video + social post (required to qualify)

---

## WCAG Standards Referenced

| Criterion | Name | What it covers |
|-----------|------|---------------|
| 1.4.1 | Use of Color | Color cannot be the only means of conveying information |
| 1.4.3 | Contrast (Minimum) | 4.5:1 normal text, 3:1 large text |
| 1.4.6 | Contrast (Enhanced) | 7:1 normal text, 4.5:1 large text |
| 1.4.11 | Non-text Contrast | 3:1 for UI components and graphical objects |

These are mapped by `accessibility_report.py` from VLM findings. The VLM prompt should instruct it to cite WCAG criteria in its response.

---

## VLM Prompt (for reference)

From `vlm_inference.py` — the prompt sent to the VLM:

> "Analyze this webpage screenshot for color accessibility issues. Describe any problems with contrast, color-dependent elements, and readability for users with color vision deficiency. Provide specific remediation suggestions."

The VLM should return a JSON array of issues, each with:
- `description` — what was found
- `type` — low contrast / color-dependent element / etc.
- `remediation` — how to fix it
- `bbox` — approximate region (optional)

---

## Inference Modes

| Mode | Implementation | Status |
|------|---------------|--------|
| **HF Router API** (default) | `vlm/vlm_inference.py` → CohereLabs/aya-vision-32b via `router.huggingface.co/v1` | ✅ Deployed on Modal — returning WCAG JSON |
| **Local llama.cpp** | `vlm/vlm_inference_llama.py` → any vision GGUF via localhost:8080 | ⚙️ Exists, not wired to UI |

---

## Reuse from NARWALL

| Source | What to reuse |
|--------|--------------|
| `narwall-selenium/AGENTS.md` | "test from perspective of assistive tech users" philosophy |
| `narwall-selenium/docs/skills/narwall-tdd.md` | TDD patterns (source inspection NOT ported — different risk model) |
| `narwall-selenium/docs/technology-readiness/REGRESSION_GUARDS.md` | WCAG mapping approach |
| `skills/gradio-huggingface-space/SKILL.md` | Gradio 6.x patterns |
| `skills/gradio-huggingface-space/references/daltonlens-cvd-api.md` | 10-type CVD simulation reference |

---

## Open Questions

1. **OpenBMB MiniCPM special award?** $10K for MiniCPM model usage. Swap `aya-vision-32b` for `openbmb/mini-cpm-v-4_6` in `vlm_inference.py`?
2. **Fine-tune worth it?** Bonus 1 (Well-Tuned) requires training. LoRA on accessibility images could be impressive but time-consuming.
3. **Which CVD type to highlight in demo?** Protanopia/deuteranopia are most common (~8% of men combined). Lead with those.