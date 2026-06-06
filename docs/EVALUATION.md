# Sponsor Prizes + Bonus Quests — Evaluation

>评估 — high impact, least effort. Not all need to be implemented.

---

## Hackathon Requirements (must meet to qualify)

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 1 | Model ≤32B parameters | ✅ Done | `CohereLabs/aya-vision-32b` (32B); also `openbmb/mini-cpm-v-4_6` (~4B) available |
| 2 | Gradio app hosted as HF Space | ⚠️ Deployed, BUILD_ERROR | `salgadev-color-ux-access.hf.space` — Gradio 5/6 compat added, rebuild triggered |
| 3 | Demo video + social post | 🔲 Not started | Deadline: this weekend |

---

## Sponsor Prizes

### 🥇 HuggingFace — $15,000 cash (top awards)

**Requirement:** Best overall projects.

**Our alignment:**
- ≤32B ✓ (aya-vision-32b)
- Gradio app ✓ (HF Space deployed)
- Real problem solved for real user ✓ (CVD accessibility)

**Verdict: PRIMARY TARGET.** Core criteria met.

---

### 🤖 OpenAI — $10,000 + $100 Codex credits (first 1,000 participants)

**Requirement:** Use OpenAI model.

**Our alignment:** ❌
- We use CohereLabs/aya-vision-32b via HF Router (not OpenAI)

**Verdict: LOW PRIORITY.** Skip unless OpenBMB awards run out.

---

### 🔬 OpenBMB — $10,000 special awards ($5K per track)

**Requirement:** Use OpenBMB model (MiniCPM-V 4.6 for vision, MiniCPM-o 4.5 for omni-modal).

**Our alignment:** ⚠️ HIGH-VALUE SWAP — $5K per track
- MiniCPM-V 4.6 is a vision VLM (~4B params, well under 32B limit)
- Swap `CohereLabs/aya-vision-32b` → `openbmb/mini-cpm-v-4_6`
- Eligible for $5K Backyard AI track prize

**Effort:** ~1 line change in `vlm/vlm_inference.py` (model name). HF Router compatible.

**Resources:**
- Model: https://huggingface.co/openbmb/MiniCPM-V-4.6
- Cookbook: https://opensqz.github.io/MiniCPM-V-CookBook/site/en/index.html
- GitHub: https://github.com/OpenBMB/MiniCPM-V-Apps
- Discord: <@1268130730509074476>, <@1379652867916566572>, <@899634493458112512>

**Verdict: SWAP FOR. $5K for minimal effort.**

---

### 🎮 NVIDIA — 2× RTX 5080 GPUs (top projects)

**Requirement:** ⚠️ **UNCONFIRMED — per Discord: Nemotron models must be used for NVIDIA prize.**
- Discord people say Nemotron models are required (not just "top project")
- Needs confirmation from organizers

**Possible models (≤32B):**
- `nvidia/Nemotron-4-2B-base` (~2B params)
- `nvidia/Nemotron-4-8B-base` (~8B params)
- `nvidia/Nemotron-4-15B-base` (~15B params)

**Our current alignment:** ❌ We use CohereLabs/aya-vision-32b (Cohere model)

**If required:** Would need to switch VLM to a Nemotron variant (e.g., `nvidia/Nemotron-4-15B-base` via HF Router) OR confirm that "any top project" qualifies.

**Verdict: CONFIRM WITH ORGANIZERS FIRST.** If Nemotron is strictly required, we need to swap. If "top project" qualifier, no action needed.

---

### 🟦 Modal — $250 credits all + $20,000 winners

**Requirement:** Use Modal for deployment.

**Our alignment:** ✅ ALREADY DEPLOYED
- `narwall-tech--color-ux-access-ui.modal.run` — LIVE (200 OK)
- $250 credits claimed from participation

**Verdict: ✅ DONE.**

---

### 🌲 Cohere — Prize support

**Requirement:** Use Cohere model.

**Our alignment:** ✅ ALREADY USING IT
- `CohereLabs/aya-vision-32b` is our VLM

**Verdict: ✅ DONE.**

---

### 🖼️ Black Forest Labs — Prize support

**Models:** FLUX.2 [klein] — 4B text-to-image model.

**Our alignment:** ❌ NOT RELEVANT
- Klein is a text-to-image generation model, not a VLM
- No logical integration path for CVD accessibility analysis

**Verdict: SKIP.**

---

## Bonus Quests

### 🥇 Bonus 1: Well-Tuned — Fine-tuned model on HF

**Effort: HIGH. Impact: HIGH if judges value model work.**

- Option A: LoRA fine-tune on accessibility dataset
- Risk: Time-consuming, may not converge in hackathon window

**Verdict: SKIP FOR NOW.**

---

### 🥈 Bonus 2: Off-Brand — Custom frontend past Gradio defaults

**Effort: LOW-MEDIUM. Impact: HIGH (first impression in demo).**

- Custom CSS for accessibility theme
- CVD comparison slider (original vs simulated side-by-side)
- JavaScript for smooth transitions

**Verdict: WORTH DOING.** Target after MVP is functional.

---

### 🥉 Bonus 3: Llama Champion — llama.cpp runtime

**Effort: MEDIUM. Impact: MEDIUM.**

- Zerogpu on HF Space: `llama-cpp-python` with CUDA whl
- Hybrid: VLM for image + llama.cpp for text report generation
- Could use GGUF model (e.g., Qwen2-VL-7B-Instruct-GGUF) for local inference

**Verdict: MEDIUM PRIORITY.**

---

### 🎁 Bonus 4: Sharing is Caring — Shared agent trace on HF

**Effort: LOW. Impact: MEDIUM.**

- Save dev conversation logs as HF Dataset
- Organize by phase: screenshot → CVD → VLM → report

**Verdict: DO THIS.** Low effort, process quality signal.

---

### 📝 Bonus 5: Field Notes — Blog post on huggingface.co/blog

**Effort: LOW-MEDIUM. Impact: MEDIUM-HIGH.**

- Technical blog post about colorblind accessibility testing methodology
- Case study: problem → approach → WCAG findings → lessons

**Verdict: DO THIS.** Low effort, high hackathon + NARWALL brand impact.

---

## Architecture: Model-Swappable VLM

> CARLOS: "we can make models swappable in our app"

**Goal:** Support multiple VLM backends for different sponsor prizes (no code duplication).

**Pattern:** Abstract VLM backend behind a `vlm/analyzer.py` interface:

```
screenshot_bytes
      ↓
analyzer.analyze(image_bytes, model="aya-vision-32b")  ← single call
      ↓
[backend: HF Router → CohereLabs/aya-vision-32b]
[backend: HF Router → openbmb/mini-cpm-v-4_6]          ← OpenBMB prize
[backend: HF Router → nvidia/Nemotron-4-15B]           ← NVIDIA prize (if required)
[backend: llama.cpp → local GGUF]                      ← Llama Champion bonus
      ↓
WCAG JSON (normalized format)
```

**Implementation:**
```python
# vlm/analyzer.py — swappable VLM backend
MODELS = {
    "aya-vision-32b":    {"provider": "cohere",  "model_id": "CohereLabs/aya-vision-32b"},
    "minicpm-v-4.6":     {"provider": "openbmb", "model_id": "openbmb/mini-cpm-v-4_6"},
    "nemotron-15b":      {"provider": "nvidia",  "model_id": "nvidia/Nemotron-4-15B-base"},
    "qwen2-vl-7b-gguf":  {"provider": "llama",   "model_path": ".../qwen2-vl-7b-q4_k_m.gguf"},
}

def analyze(image_bytes, model="aya-vision-32b"):
    config = MODELS[model]
    if config["provider"] == "llama":
        return analyze_with_llama(image_bytes, config["model_path"])
    else:
        return analyze_with_hf_router(image_bytes, config["model_id"])
```

**On HF Space UI:** Add a `gr.Dropdown` to let user select model:
```python
model_select = gr.Dropdown(
    choices=list(MODELS.keys()),
    value="aya-vision-32b",
    label="VLM Backend"
)
```

**Use cases (notes):**
- Default: CohereLabs/aya-vision-32b (general WCAG analysis)
- OpenBMB award: MiniCPM-V 4.6 (swap one line, submit for $5K) — already in MODELS
- NVIDIA award: Nemotron (swap if required) — already in MODELS
- Llama Champion: GGUF local model (offline, no API cost) — model dropdown exists, GGUF path not yet wired
- NARWALL production: specific model fine-tuned on accessibility (future)

---

## Implementation Priority

| Priority | Task | Reason |
|----------|------|--------|
| 🔴 **P0** | **Confirm NVIDIA Nemotron requirement** | May require VLM swap |
| 🔴 **P0** | **Add HF_TOKEN secret to Space** | Space is live but VLM won't work without token |
| 🔴 **P0** | **Test first Space inference** | Verify end-to-end works |
| 🟡 **P1** | **Implement model swappable backend** | Enables OpenBMB + NVIDIA prize eligibility |
| 🟡 **P1** | **Blog post (Bonus 5)** | Low effort, high impact |
| 🟡 **P1** | **OpenBMB MiniCPM-V swap** | $5K for one-line change |
| 🟢 **P2** | **Off-brand Gradio theme (Bonus 2)** | Custom CSS, CVD slider |
| 🟢 **P2** | **Agent trace (Bonus 4)** | Low effort |
| 🟢 **P2** | **Demo video + social post** | Required to qualify |
| 🔵 SKIP | BFL Klein | Not relevant to VLM task |
| 🔵 SKIP | Fine-tune (Bonus 1) | High effort, time risk |

---

## Hackathon Tasks

| # | Task | Status | Notes |
|---|------|--------|-------|
| T1 | CVD simulation (10 types, daltonlens) | ✅ Done | `app/app.py` has full 10-type simulation |
| T2 | VLM pipeline (HF Router → WCAG JSON) | ✅ Done | Mock returning correct JSON, real via Router |
| T3 | Architecture (screenshot → CVD → VLM → report) | ✅ Done | File upload + VLM via HF Router, Space deployable |
| T4 | CDP CVD simulation | 🔲 | 10-type daltonlens is sufficient for MVP |
| T5 | HF Space deploy | ⚠️ Deployed, BUILD_ERROR | `salgadev-color-ux-access.hf.space` — Gradio 5/6 compat added, rebuilding |
| T6 | Model swappable backend | ✅ Done | MODELS dict + gr.Dropdown + model= param in `analyze_with_vlm` |
| T7 | Demo video + social post | 🔲 | **Required to qualify** — deadline this weekend |
| T8 | Blog post (Bonus 5) | 🔲 | P1 — low effort, high impact |
| T9 | NVIDIA Nemotron confirmation | 🔲 | P0 — may need VLM swap if Nemotron strictly required |
| T10 | OpenBMB MiniCPM-V swap | 🔲 | P1 — $5K for one-line change, already in MODELS |
| T11 | Off-brand Gradio theme (Bonus 2) | 🔲 | P2 — custom CSS, CVD slider, Bonus 2 |
| T12 | Agent trace (Bonus 4) | 🔲 | P2 — process quality signal, Bonus 4 |
| T13 | Gradio 5/6 backward compat | ✅ Done | try/except version detection in `app_space.py` |
| T14 | HF_TOKEN secret in Space | 🔲 | P0 — needed for VLM inference to work |

**Focus: MVP functional → polish → sponsor-specific optimizations**

---

*Last updated: 2026-06-07*
*Notes: Gradio 5/6 compat via try/except `_is_gradio6` flag in app_space.py. Model swappable backend implemented (aya-vision-32b, minicpm-v-4.6, nemotron-15b). Llama.cpp GGUF Zerogpu path not yet wired (Bonus 3 / T6 GGUF). HF Space needs rebuild + HF_TOKEN secret.*