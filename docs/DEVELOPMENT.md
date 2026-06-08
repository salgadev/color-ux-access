# Development Guide — Color-UX-Access

> Part of **NARWALL** automated accessibility testing ecosystem.
> Build period: HF Build Small Hackathon, June 5–15, 2026.
> Track: Backyard AI · ≤32B parameters · Gradio app · Deployed on HF Space.

For **quick start** (clone → setup → run), see README.md. This doc covers the full development workflow.

---

## Why `uv` Is Mandatory

Hermes Agent runs in its own Python environment. Installing project dependencies without isolation modifies Hermes's own environment — as happened in an earlier session where libraries were uninstalled globally, breaking Hermes Agent.

`uv venv` creates a fully isolated environment at `.venv/` in the project root. Nothing installed here affects the system Python or Hermes Agent.

```bash
uv venv --python 3.12
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
uv pip install -e ".[all]"
```

Always use `uv run pytest` / `uv run python app.py` within the project (or activate venv first).

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

> **Note:** `playwright` is installed for local screenshot capture but is NOT used in the test suite (HF Space containers cannot run a browser). Tests are source-inspection only.

---

## Project Structure

```
color-ux-access/
├── color_ux_access/           Core package (no Gradio dependency)
│   ├── __init__.py            Exports: simulate_cvd, CVD_VARIANTS
│   ├── cvd_sim.py             DaltonLens wrapper — 10 types + grayscale
│   └── capture.py             Playwright screenshot capture (take_screenshot)
├── vlm/                       VLM inference layer
│   ├── accessibility_report.py # WCAG report class + standards reference
│   ├── vlm_inference.py        # HF Router API → CohereLabs/aya-vision-32b
│   └── vlm_inference_llama.py  # llama.cpp GGUF local fallback
├── app/                       Local dev Gradio app (URL → screenshot)
│   ├── app.py                 # Main Blocks app
│   └── custom_theme.py        # ColorUXAccessTheme (accessible blue/gray)
├── app_space.py               # HF Space entrypoint (file upload, no Playwright)
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

For entrypoint decisions (which file to run when), see `docs/ARCHITECTURE.md`.

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

Normal. The model downloads on first call and caches on subsequent calls.

---

*Maintained by: NARWALL · github.com/salgadev/color-ux-access*