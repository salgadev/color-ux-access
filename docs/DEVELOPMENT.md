# Development Guide — Color-UX-Access

> Part of **NARWALL** automated accessibility testing ecosystem.
> Build period: HF Build Small Hackathon, June 5–15, 2026.
> Track: Backyard AI · ≤32B parameters · Gradio app · Deployed on HF Space.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/salgadev/color-ux-access.git
cd color-ux-access

# 2. Create isolated venv with uv (REQUIRED — prevents Hermes Agent global pollution)
uv venv --python 3.12
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate

# 3. Install all dependencies (default + dev + space + modal)
uv pip install -e ".[all]"

# 4. Set up env variables
cp .env.example .env
# Edit .env: add your HF_TOKEN=hf_... from huggingface.co/settings/tokens

# 5. Run tests
pytest -m smoke    # fast: imports only, no network, no GPU
pytest             # full suite (smoke + pipeline)
```

---

## Why `uv` Is Mandatory

Hermes Agent runs in its own Python environment. Installing project dependencies
without isolation modifies Hermes's own environment — as happened in an earlier
session where libraries were uninstalled globally, breaking Hermes Agent.

`uv venv` creates a fully isolated environment at `.venv/` in the project root.
Nothing installed here affects the system Python or Hermes Agent.

```bash
# Create venv (one-time)
uv venv --python 3.12

# Activate
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate

# Install package + all extras
uv pip install -e ".[all]"

# Check what's installed
uv pip list

# Freeze lock file (commit this for reproducible CI)
uv pip freeze > requirements.lock
```

---

## Environment Files

| File | Purpose | Committed? |
|------|---------|------------|
| `.env` | Local secrets (HF_TOKEN) | ❌ No |
| `.env.example` | Template for collaborators | ✅ Yes |
| `.venv/` | Virtual environment | ❌ No (in .gitignore) |
| `requirements.lock` | Locked dependency versions | ✅ Yes (after `uv pip freeze`) |

---

## Dependency Groups

Defined in `pyproject.toml`:

| Group | Contents | When to use |
|-------|----------|-------------|
| `default` | pillow, daltonlens, numpy | Always |
| `dev` | playwright, pytest, colorspacious | Local testing |
| `space` | gradio, spaces, torch, openai, huggingface_hub==0.25.2 | HF Space deployment |
| `modal` | modal, fastapi, gradio | Modal deployment |
| `all` | `dev` + `space` + `modal` | Full local development |

> **Note:** `playwright` is installed for local screenshot capture but is NOT used
> in the test suite (HF Space containers cannot run a browser). Tests are
> source-inspection only.

---

## Project Structure

```
color-ux-access/
├── color_ux_access/           Core package (no Gradio dependency)
│   ├── __init__.py            Exports: simulate_cvd, CVD_VARIANTS
│   ├── cvd_sim.py             DaltonLens wrapper — 7 CVD types + grayscale
│   └── capture.py             Playwright screenshot capture (take_screenshot)
├── vlm/                       VLM inference layer
│   ├── accessibility_report.py # WCAG report class + standards reference
│   ├── vlm_inference.py        # HF Router API → CohereLabs/aya-vision-32b
│   └── vlm_inference_llama.py  # llama.cpp GGUF local fallback
├── app/                       Local development Gradio app (URL → screenshot)
│   ├── app.py                 # Main Blocks app
│   └── custom_theme.py        # ColorUXAccessTheme (accessible blue/gray)
├── app_space.py               # HF Space entrypoint (file upload, no Playwright in container)
├── modal_app.py               # Modal deployment (ASGI, GPU inference)
├── tests/
│   ├── conftest.py            # Shared fixtures: img_factory, cvd_img_factory, mock_vlm_factory
│   ├── fixtures/              # Generated synthetic UI screenshots (PIL, no browser)
│   │   ├── *.png              # Original clean versions
│   │   └── *_cvdtype.png      # CVD-simulated variants
│   ├── test_smoke.py          # All core imports work, CVD config correct, apps loadable
│   ├── test_capture.py        # capture module contract: take_screenshot signature
│   ├── test_app_space.py      # CVD gallery, WCAG report, Gradio 6 theme launch
│   ├── test_gradio_binary.py  # Source inspection: GradioFile bytes handling
│   └── test_modal_app.py      # Source inspection: Modal app structure
├── pyproject.toml             # Package config, dep groups, pytest config
├── pytest.ini                 # Marker definitions, testpaths, pythonpath
├── conftest.py                # Shared pytest fixtures
├── .env.example               # Env variable template
├── requirements.txt           # Legacy fallback (use uv + pyproject.toml)
└── requirements_space.txt     # HF Space hardware image deps
```

### Which Entrypoint to Use

| Context | Entrypoint | Why |
|---------|-----------|-----|
| Local development | `python app/app.py` | URL input, auto-screenshot |
| HF Space | `app_space.py` | File upload, no Playwright in container |
| Modal (GPU inference) | `modal_app.py` | ASGI app, sticky session |
| CLI VLM test | `python -m vlm.vlm_inference screenshot.png` | Test VLM without Gradio |

---

## Running Tests

```bash
pytest -m smoke    # Fast: imports only, no network (<10s)
pytest -m pipeline # Full pipeline with mocked VLM (<30s)
pytest -m slow     # Real VLM calls — needs HF_TOKEN set (60–90s)
pytest             # Default: smoke + pipeline (no slow)
```

### TDD Pattern (RED → GREEN → REFACTOR)

```bash
# 1. Write a failing test
pytest tests/test_capture.py::test_take_screenshot_signature -v

# 2. Verify RED — test fails because function doesn't exist

# 3. Implement the feature

# 4. Run again — verify GREEN
pytest tests/test_capture.py -v

# 5. Refactor if needed
```

---

## CVD Simulation Reference

### Supported Types

| Variant | Deficiency | Severity | Population |
|---------|-----------|----------|-----------|
| deuteranopia | DEUTAN | 1.0 (dichromacy) | ~1% males |
| protanopia | PROTAN | 1.0 (dichromacy) | ~1% males |
| tritanopia | TRITAN | 1.0 (dichromacy) | rare |
| achromatopsia | grayscale | 1.0 (rod monochromacy) | ~0.003% |
| deuteranomaly | DEUTAN | 0.6 (anomalous) | ~5% males |
| protanomaly | PROTAN | 0.6 (anomalous) | ~1% males |
| tritanomaly | TRITAN | 0.6 (anomalous) | rare |

### Usage

```python
from color_ux_access.cvd_sim import simulate_cvd, CVD_VARIANTS

# Simulate single variant
img = Image.open("screenshot.png")
deuteranopia_view = simulate_cvd(img, "deuteranopia")
deuteranopia_view.save("deuteranopia_view.png")

# Iterate all variants
for cvd_type in CVD_VARIANTS:
    result = simulate_cvd(img, cvd_type)
```

DaltonLens simulators: Machado2009 (default), Vienot1999 (severe), Brettel1997 (tritanopia).

---

## WCAG Standards Reference

| Criterion | Name | Ratio Required |
|-----------|------|---------------|
| 1.4.1 | Use of Color | Color cannot be the only means |
| 1.4.3 | Contrast (Minimum) | 4.5:1 normal text, 3:1 large text |
| 1.4.6 | Contrast (Enhanced) | 7:1 normal text, 4.5:1 large text |
| 1.4.11 | Non-text Contrast | 3:1 for UI components |

---

## Git Workflow

**Branch → PR, never push to main directly.**

```bash
git checkout -b fix/your-fix-name
# make changes, commit
git push origin fix/your-fix-name
gh pr create --fill --base main
```

All changes go through pull requests for review.

---

## Code Style

- Python 3.12+
- `ruff` for linting + formatting (configured in pyproject.toml)
- Run `ruff check . --fix` before committing
- Docstrings: Google style (Args, Returns, Raises)
- Type hints on public functions

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'color_ux_access'`

Activate the virtual environment:
```bash
source .venv/Scripts/activate
uv pip install -e .
```

### HF_TOKEN not set

Copy `.env.example` → `.env` and add your token from huggingface.co/settings/tokens.

### First VLM inference takes 90s

Normal. The model downloads on first call and caches in the Space's GPU memory.

---

*Maintained by: NARWALL · github.com/salgadev/color-ux-access*