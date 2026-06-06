# Deployment Guide — Color-UX-Access

> HF Space and Modal deployment. Sponsor prize eligibility matrix.
> For local development, see `docs/DEVELOPMENT.md`.

---

## Current Status

| Service | URL | Status |
|---------|-----|--------|
| HF Space | `salgadev-color-ux-access.hf.space` | ⚠️ BUILD_ERROR (sdk_version mismatch) |
| Modal | `narwall-tech--color-ux-access-ui.modal.run` | ✅ LIVE (200) |

**HF Space issue:** The Space was originally created with `sdk_version: 5.0.0` and `app_file: app.py`.
README.md now has `sdk_version: 6.0.0` and `app_file: app_space.py` — these take effect on next rebuild.
Additionally, HF Spaces infrastructure installs `gradio[oauth]==5.0.0` as a default dependency.
`app_space.py` now has Gradio 5/6 backward compat (try/except version detection) so it works with both.
`HF_TOKEN` secret must be added in Space Settings → Variables and Secrets for VLM inference to work.

### Rebuild HF Space

After pushing to GitHub, restart the Space to pick up changes:

```bash
python -c "from huggingface_hub import HfApi; HfApi().restart_space('salgadev/color-ux-access')"
```

### Setup

1. **Push to GitHub** — HF Spaces sync from GitHub repos.

2. **Create HF Space**
   - Go to huggingface.co/spaces
   - Create new Space: SDK = Gradio, Hardware = T4-small or A10G
   - Set `python_version: "3.12"` in the Space metadata

3. **Add HF_TOKEN secret**
   - Space Settings → Variables and Secrets → Add secret
   - Name: `HF_TOKEN`, Value: `hf_...` from huggingface.co/settings/tokens

4. **Link to GitHub** — Space Settings → Repository → Link to GitHub repo

5. **Add Space hardware** — t4-small (free tier) is sufficient for testing; upgrade to A10G for production.

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
huggingface_hub==0.25.2   # Must be <0.26 (HfFolder removed in 0.26)
```

> **Critical:** `huggingface_hub<0.26` is required. Gradio 5.x depends on `HfFolder` which was removed in huggingface_hub 0.26.

### Environment Variables on Space

| Variable | Source | Required |
|----------|--------|----------|
| `HF_TOKEN` | Space secret | ✅ Yes |
| `HF_API_TOKEN` | Space secret (fallback for some deps) | Recommended |

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

First inference: ~60–90s (model download + KV cache init).
Subsequent: <5s (cached).

### Known Issues

| Issue | Fix |
|-------|-----|
| `HfFolder` not found | Downgrade huggingface_hub to 0.25.2 |
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

---

## Sponsor Prize Eligibility

| Sponsor | Prize | Requirement | Status | Action |
|---------|-------|-------------|--------|--------|
| **HuggingFace** | $15,000 cash | Top overall project | ✅ Eligible | Submit demo + blog |
| **OpenBMB** | $10,000 special awards | Use MiniCPM-V 4.6 | 🔲 One-line swap | Swap model in `vlm_inference.py` → `openbmb/mini-cpm-v-4_6` |
| **Modal** | $250 all + $20,000 winners | Use Modal | ✅ Already deployed | $250 credited |
| **Cohere** | Prize support | Use Cohere model | ✅ Already using aya-vision-32b | No action needed |
| **NVIDIA** | 2× RTX 5080 GPUs | Top project + ⚠️ Nemotron? | ⚠️ Unconfirmed | Ask organizers if Nemotron is strictly required |
| **OpenAI** | $10K + $100 Codex | Use OpenAI model | ❌ Not using | Skip |
| **Black Forest Labs** | Prize support | Use FLUX.2 klein | ❌ Not relevant | Skip |

### OpenBMB MiniCPM-V Swap ($5K for one-line change)

In `app_space.py` and `color_ux_access/modal_app.py`, change the model name:

```python
# Before
model='CohereLabs/aya-vision-32b'

# After
model='openbmb/mini-cpm-v-4_6'
```

Resources:
- Model: huggingface.co/openbmb/MiniCPM-V-4.6
- Cookbook: opensqz.github.io/MiniCPM-V-CookBook/site/en/index.html

### NVIDIA RTX 5080 ⚠️

Per Discord discussion, Nemotron models may be strictly required, not just "top project."
If required, swap VLM to `nvidia/Nemotron-4-15B-base` via HF Router.

Available: Nemotron-4-2B, Nemotron-4-8B, Nemotron-4-15B (all under 32B limit).

**Action:** Confirm with hackathon organizers before making any changes.

---

## Hackathon Requirements

| Requirement | Status |
|-------------|--------|
| Model ≤32B parameters | ✅ aya-vision-32b (32B) |
| Gradio app hosted as HF Space | ✅ salgadev-color-ux-access.hf.space |
| Demo video + social post | 🔲 Not started |
| Blog post (bonus) | 🔲 Not started |

### Qualifying for the Hackathon

1. ✅ Working Gradio app on HF Space
2. 🔲 Record demo video (60-90s, show real URL → CVD → WCAG report)
3. 🔲 Post on social media (Twitter/X, LinkedIn, or LinkedIn company page)

---

## Bonus Points

For full descriptions and implementation options, see `docs/BONUS_PLAN.md`.

| Bonus | Effort | Impact | Status |
|-------|--------|--------|--------|
| **Well-Tuned** — Fine-tune model on HF | High | High | 🔲 Skip for now |
| **Off-Brand** — Custom Gradio theme | Low-Medium | High | 🔲 P2 — custom CSS, CVD slider |
| **Llama Champion** — llama.cpp GGUF runtime | Medium | Medium | 🔲 Offline fallback only |
| **Sharing is Caring** — Agent trace on HF | Low | Medium | 🔲 Low effort, do it |
| **Field Notes** — Blog post | Low-Medium | Medium-High | 🔲 P1 — do this |

### Priority Order

1. **P0:** Demo video + social post (required to qualify)
2. **P1:** Blog post on huggingface.co/blog
3. **P1:** OpenBMB MiniCPM-V swap ($5K for one line)
4. **P1:** Confirm NVIDIA Nemotron requirement
5. **P2:** Off-brand Gradio theme (custom CSS + CVD slider)
6. **P2:** Agent trace (Sharing is Caring)