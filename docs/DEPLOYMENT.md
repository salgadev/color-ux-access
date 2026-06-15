# Deployment Guide — Color-UX-Access

> HF Space and Modal deployment.
> For local development, see `docs/DEVELOPMENT.md`.
> For sponsor prize eligibility and bonus quests, see `docs/EVALUATION.md`.

---

## Current Status

| Service | URL | Status |
|---------|-----|--------|
| HF Space | `salgadev-color-ux-access.hf.space` | ⚠️ BUILD_ERROR (hash mismatch — fixing) |
| Modal | `narwall-tech--color-ux-access-ui.modal.run` | ✅ LIVE (200) |

**HF Space issue:** The Space uses `sdk_version: 6.17.3` and `app_file: app.py` in README.md. HF Spaces infrastructure auto-installs `gradio[oauth,mcp]==6.17.3` matching the SDK version. The `requirements_space.txt` (now used via `dependencies` in README) provides the remaining dependencies without pinning Gradio, avoiding hash conflicts. `HF_TOKEN` secret must be added in Space Settings for VLM inference to work.

---

## HF Space Deployment

### Rebuild HF Space

After pushing to GitHub, restart the Space to pick up changes:

```bash
python -c "from huggingface_hub import HfApi; HfApi().restart_space('salgadev/color-ux-access')"
```

### Setup

1. **Push to GitHub** — HF Spaces sync from GitHub repos.
2. **Create HF Space** — huggingface.co/spaces, SDK = Gradio, Hardware = T4-small or A10G, `python_version: "3.12"`
3. **Add HF_TOKEN secret** — Space Settings → Variables and Secrets → Name: `HF_TOKEN`
4. **Link to GitHub** — Space Settings → Repository → Link to GitHub repo
5. **Add Space hardware** — t4-small (free tier) sufficient for testing; upgrade to A10G for production.

### Space Requirements File

`requirements_space.txt` is the source of truth for the Space image:

```txt
# HF Space requirements — Python 3.12, spaces GPU
--extra-index-url https://download.pytorch.org/whl/cu128
torch==2.8.0
gradio>=6.0
spaces
openai>=1.0
pillow
numpy
daltonlens
python-dotenv
modal>=1.4.3
requests>=2.34.2
colorspacious>=1.1.2
```

> **Note:** Gradio version is determined by `sdk_version` in README.md (currently 6.17.3). The Space infrastructure auto-installs `gradio[oauth,mcp]` matching that version.

### Environment Variables

| Variable | Source | Required |
|----------|--------|----------|
| `HF_TOKEN` | Space secret | ✅ Yes |
| `HF_API_TOKEN` | Space secret (fallback) | Recommended |

### Architecture on Space

```
User uploads screenshot (Gradio File component, type='binary')
       │
       ▼
run_analysis() — CPU stage
  1. Open image bytes → PIL Image
  2. generate_cvd_gallery() → 10-type CVD simulation (CPU, instant)
  3. Return (original, gallery, pending)
       │
       ▼
analyze_with_vlm() — GPU stage (@spaces.GPU in Space context)
  4. HF Router API → CohereLabs/aya-vision-32b
  5. format_wcag_report() → Markdown report
       │
       ▼
Return (original, gallery, report)
```

First inference: ~60–90s (model download + KV cache init). Subsequent: <5s (cached).

### Known Issues

| Issue | Fix |
|-------|-----|
| First call timeout | Space hardware too small → upgrade to A10G |
| Token not found | Add HF_TOKEN secret in Space Settings |
| Space not building | Check `requirements_space.txt` syntax, no comments in pip install |

---

## Modal Deployment

**Endpoint:** `narwall-tech--color-ux-access-ui.modal.run`
**Entrypoint:** `color_ux_access/modal_app.py`

### Architecture

```
User uploads screenshot → Gradio ASGI app (Modal sticky container)
       │
       ▼
upload_screenshot() — CPU function
  → vlm_inference_fn.remote(image_bytes) — calls GPU function
       │
       ▼
vlm_inference_fn — GPU (A10G)
  → HF Router API → CohereLabs/aya-vision-32b
  → returns JSON dict
       │
       ▼
Gradio UI renders JSON as WCAG report
```

Sticky session (`max_containers=1`) required because Gradio manages UI state internally.

### Deploy

```bash
modal deploy color_ux_access.modal_app
```

### Secrets

Create a Modal secret named `hf-token-narwall` with value `hf_...`.

```bash
modal secret create hf-token-narwall
# Enter your HF token when prompted
```