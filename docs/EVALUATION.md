# Sponsor Prizes + Bonus Quests — Evaluation

> High impact, least effort. Not all bonus quests need to be implemented.

---

## Hackathon Requirements (must meet to qualify)

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 1 | Model ≤32B parameters | ✅ Done | `CohereLabs/aya-vision-32b` (32B); also `openbmb/mini-cpm-v-4_6` (~4B) available |
| 2 | Gradio app hosted as HF Space | ✅ Done | `salgadev-color-ux-access.hf.space` — Gradio 5/6 compat, deployed |
| 3 | Demo video + social post | 🔲 Not started | Deadline: this weekend |

---

## Sponsor Prize Alignment

### HuggingFace — $15,000 cash (top awards)

**Requirement:** Best overall projects.

**Our alignment:**
- ≤32B ✓ (aya-vision-32b)
- Gradio app ✓ (HF Space deployed)
- Real problem solved for real user ✓ (CVD accessibility)

**Verdict: PRIMARY TARGET.** Core criteria met.

---

### OpenBMB — $10,000 ($5K per track)

**Requirement:** Use OpenBMB model (MiniCPM-V 4.6 for vision).

**Our alignment:** ⚠️ HIGH-VALUE SWAP — $5K per track
- MiniCPM-V 4.6 is a vision VLM (~4B params, well under 32B limit)
- Swap `CohereLabs/aya-vision-32b` → `openbmb/mini-cpm-v-4_6`
- Eligible for $5K Backyard AI track prize

**Effort:** ~1 line change in `vlm/vlm_inference.py` (model name). HF Router compatible.

**Resources:**
- Model: https://huggingface.co/openbmb/MiniCPM-V-4.6
- Cookbook: https://opensqz.github.io/MiniCPM-V-CookBook/site/en/index.html
- GitHub: https://github.com/OpenBMB/MiniCPM-V-Apps

**Verdict: SWAP FOR. $5K for minimal effort.**

---

### NVIDIA — 2× RTX 5080 GPUs (top projects)

**Requirement:** ⚠️ **UNCONFIRMED — per Discord: Nemotron models must be used for NVIDIA prize.**
- Discord people say Nemotron models are required (not just "top project")
- Needs confirmation from organizers

**Possible models (≤32B):**
- `nvidia/Nemotron-4-2B-base` (~2B params)
- `nvidia/Nemotron-4-8B-base` (~8B params)
- `nvidia/Nemotron-4-15B-base` (~15B params)

**Our current alignment:** ❌ We use CohereLabs/aya-vision-32b (Cohere model)

**If required:** Would need to switch VLM to a Nemotron variant via HF Router.

**Verdict: CONFIRM WITH ORGANIZERS FIRST.**

---

### Modal — $250 credits all + $20,000 winners

**Requirement:** Use Modal for deployment.

**Our alignment:** ✅ ALREADY DEPLOYED
- `narwall-tech--color-ux-access-ui.modal.run` — LIVE (200 OK)
- $250 credits claimed from participation

**Verdict: ✅ DONE.**

---

### Cohere — Prize support

**Requirement:** Use Cohere model.

**Our alignment:** ✅ ALREADY USING IT
- `CohereLabs/aya-vision-32b` is our VLM

**Verdict: ✅ DONE.**

---

### Black Forest Labs — Prize support

**Models:** FLUX.2 [klein] — 4B text-to-image model.

**Our alignment:** ❌ NOT RELEVANT
- Klein is a text-to-image generation model, not a VLM
- No logical integration path for CVD accessibility analysis

**Verdict: SKIP.**

---

## Bonus Quests

### Bonus 1: Well-Tuned — Fine-tuned model on HF

**Effort: HIGH. Impact: HIGH if judges value model work.**

- Option A: LoRA fine-tune on accessibility dataset
- Risk: Time-consuming, may not converge in hackathon window

**Verdict: SKIP FOR NOW.**

---

### Bonus 2: Off-Brand — Custom frontend past Gradio defaults

**Effort: LOW-MEDIUM. Impact: HIGH (first impression in demo).**

- Custom CSS for accessibility theme
- CVD comparison slider (original vs simulated side-by-side)
- JavaScript for smooth transitions

**Verdict: WORTH DOING.** Target after MVP is functional.

---

### Bonus 3: Llama Champion — llama.cpp runtime

**Effort: MEDIUM. Impact: MEDIUM.**

- Zerogpu on HF Space: `llama-cpp-python` with CUDA whl
- Hybrid: VLM for image + llama.cpp for text report generation
- Could use GGUF model (e.g., Qwen2-VL-7B-Instruct-GGUF) for local inference

**Verdict: MEDIUM PRIORITY.**

---

### Bonus 4: Sharing is Caring — Shared agent trace on HF

**Effort: LOW. Impact: MEDIUM.**

- Save dev conversation logs as HF Dataset
- Organize by phase: screenshot → CVD → VLM → report

**Verdict: DO THIS.** Low effort, process quality signal.

---

### Bonus 5: Field Notes — Blog post on huggingface.co/blog

**Effort: LOW-MEDIUM. Impact: MEDIUM-HIGH.**

- Technical blog post about colorblind accessibility testing methodology
- Case study: problem → approach → WCAG findings → lessons

**Verdict: DO THIS.** Low effort, high hackathon + NARWALL brand impact.

---

## Implementation Priority

| Priority | Task | Reason |
|----------|------|--------|
| 🔴 **P0** | **Confirm NVIDIA Nemotron requirement** | May require VLM swap |
| 🔴 **P0** | **Add HF_TOKEN secret to Space** | Space is live but VLM won't work without token |
| 🔴 **P0** | **Test first Space inference** | Verify end-to-end works |
| 🟡 **P1** | **OpenBMB MiniCPM-V swap** | $5K for one-line change |
| 🟡 **P1** | **Blog post (Bonus 5)** | Low effort, high impact |
| 🟢 **P2** | **Off-brand Gradio theme (Bonus 2)** | Custom CSS, CVD slider |
| 🟢 **P2** | **Agent trace (Bonus 4)** | Low effort |
| 🟢 **P2** | **Demo video + social post** | Required to qualify |
| 🔵 SKIP | BFL Klein | Not relevant to VLM task |
| 🔵 SKIP | Fine-tune (Bonus 1) | High effort, time risk |

---

## Current Task Status

| # | Task | Status | Notes |
|---|------|--------|-------|
| T1 | CVD simulation (10 types, daltonlens) | ✅ Done | Full 10-type simulation in `app.py` |
| T2 | VLM pipeline (HF Router → WCAG JSON) | ✅ Done | Modal endpoint for GPU inference |
| T3 | Architecture (screenshot → CVD → VLM → report) | ✅ Done | File upload + VLM via Modal, Space deployable |
| T4 | CDP CVD simulation | ✅ Done | 10-type daltonlens sufficient for MVP |
| T5 | HF Space deploy | ✅ Done | `salgadev-color-ux-access.hf.space` live |
| T6 | Model swappable backend | ✅ Done | MODELS dict + gr.Dropdown + model= param |
| T7 | Demo video + social post | 🔲 | **Required to qualify** — deadline this weekend |
| T8 | Blog post (Bonus 5) | 🔲 | P1 — low effort, high impact |
| T9 | NVIDIA Nemotron confirmation | 🔲 | P0 — confirm if Nemotron strictly required |
| T10 | OpenBMB MiniCPM-V swap | 🔲 | P1 — $5K for one-line change, already in MODELS |
| T11 | Off-brand Gradio theme (Bonus 2) | 🔲 | P2 — custom CSS, CVD slider |
| T12 | Agent trace (Bonus 4) | 🔲 | P2 — process quality signal |
| T13 | Gradio 5/6 backward compat | ✅ Done | `_is_gradio6` flag in `app.py` |
| T14 | HF_TOKEN secret in Space | 🔲 | P0 — needed for VLM inference to work |

**Focus: MVP functional → polish → sponsor-specific optimizations**

---

*Last updated: 2026-06-08*
*Notes: Gradio 5/6 compat via `_is_gradio6` flag in app.py. Model swappable backend implemented (aya-vision-32b, minicpm-v-4.6, nemotron-15b). Llama.cpp GGUF Zerogpu path not yet wired (Bonus 3). HF Space deployed + HF_TOKEN secret needed.*