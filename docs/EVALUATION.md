# Sponsor Prizes + Bonus Quests — Evaluation

> 评估 — high impact, least effort.

For the **model-swappable VLM backend** (MODELS dict, UI dropdown, provider abstraction), see `docs/ARCHITECTURE.md`. For deployment specifics, see `docs/DEPLOYMENT.md`.

---

## Hackathon Requirements (must meet to qualify)

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 1 | Model ≤32B parameters | ✅ Done | `CohereLabs/aya-vision-32b` (32B); also `openbmb/mini-cpm-v-4_6` (~4B) available |
| 2 | Gradio app hosted as HF Space | ⚠️ Deployed, BUILD_ERROR | Gradio 5/6 compat added, rebuild triggered |
| 3 | Demo video + social post | 🔲 Not started | Required to qualify |

---

## Sponsor Prizes

### 🥇 HuggingFace — $15,000 cash (top awards)

**Requirement:** Best overall projects.

**Our alignment:** ✅ Core criteria met. ≤32B ✓, Gradio ✓, real problem ✓.

**Verdict: PRIMARY TARGET.**

---

### 🤖 OpenAI — $10,000 + $100 Codex credits

**Requirement:** Use OpenAI model.

**Our alignment:** ❌ We use CohereLabs/aya-vision-32b via HF Router (not OpenAI).

**Verdict: SKIP.**

---

### 🔬 OpenBMB — $10,000 special awards ($5K per track)

**Requirement:** Use OpenBMB model (MiniCPM-V 4.6 for vision).

**Our alignment:** ⚠️ HIGH-VALUE SWAP — $5K for one-line model name change.
- Already in MODELS dict as `minicpm-v-4.6` → `openbmb/mini-cpm-v-4_6`
- HF Router compatible, ~4B params

**Resources:**
- Model: https://huggingface.co/openbmb/MiniCPM-V-4.6
- Cookbook: https://opensqz.github.io/MiniCPM-V-CookBook/site/en/index.html
- GitHub: https://github.com/OpenBMB/MiniCPM-V-Apps

**Verdict: SWAP FOR. $5K for minimal effort.**

---

### 🎮 NVIDIA — 2× RTX 5080 GPUs (top projects)

**Requirement:** ⚠️ **UNCONFIRMED** — per Discord: Nemotron models may be strictly required.

**Possible models (≤32B):** `nvidia/Nemotron-4-2B-base`, `nvidia/Nemotron-4-8B-base`, `nvidia/Nemotron-4-15B-base`

**Our alignment:** ❌ Currently using CohereLabs/aya-vision-32b.

**If required:** Already in MODELS dict as `nemotron-15b`. Would need to switch VLM or confirm "top project" qualifier.

**Verdict: CONFIRM WITH ORGANIZERS FIRST.**

---

### 🟦 Modal — $250 credits all + $20,000 winners

**Requirement:** Use Modal for deployment.

**Our alignment:** ✅ ALREADY DEPLOYED — `narwall-tech--color-ux-access-ui.modal.run` live.

**Verdict: ✅ DONE.**

---

### 🌲 Cohere — Prize support

**Requirement:** Use Cohere model.

**Our alignment:** ✅ Already using `CohereLabs/aya-vision-32b`.

**Verdict: ✅ DONE.**

---

### 🖼️ Black Forest Labs — Prize support

**Requirement:** Use FLUX.2 [klein] — 4B text-to-image model.

**Our alignment:** ❌ Not relevant (image generation, not VLM).

**Verdict: SKIP.**

---

## Bonus Quests

### 🥇 Bonus 1: Well-Tuned — Fine-tuned model on HF

**Effort: HIGH. Impact: HIGH** if judges value model work. LoRA fine-tune on accessibility dataset. Risk: time-consuming.

**Verdict: SKIP FOR NOW.**

### 🥈 Bonus 2: Off-Brand — Custom frontend past Gradio defaults

**Effort: LOW-MEDIUM. Impact: HIGH** (first impression in demo).
- Custom CSS for accessibility theme
- CVD comparison slider (original vs simulated side-by-side)
- JavaScript for smooth transitions

**Verdict: WORTH DOING** after MVP is functional.

### 🥉 Bonus 3: Llama Champion — llama.cpp runtime

**Effort: MEDIUM. Impact: MEDIUM.** Hybrid: VLM for image + llama.cpp for text. GGUF model (e.g., Qwen2-VL-7B-Instruct-GGUF) for local inference.

**Verdict: MEDIUM PRIORITY.**

### 🎁 Bonus 4: Sharing is Caring — Shared agent trace on HF

**Effort: LOW. Impact: MEDIUM.** Save dev conversation logs as HF Dataset, organized by phase.

**Verdict: DO THIS.** Low effort, process quality signal.

### 📝 Bonus 5: Field Notes — Blog post on huggingface.co/blog

**Effort: LOW-MEDIUM. Impact: MEDIUM-HIGH.** Technical blog about colorblind accessibility testing methodology.

**Verdict: DO THIS.** Low effort, high hackathon + NARWALL brand impact.

---

## Priority Order

| Priority | Task | Reason |
|----------|------|--------|
| 🔴 P0 | **Confirm NVIDIA Nemotron requirement** | May require VLM swap |
| 🔴 P0 | **Add HF_TOKEN secret to Space** | VLM won't work without it |
| 🔴 P0 | **Test first Space inference** | Verify end-to-end works |
| 🟡 P1 | **Implement model swappable backend** | ✅ Done — see ARCHITECTURE.md |
| 🟡 P1 | **Blog post (Bonus 5)** | Low effort, high impact |
| 🟡 P1 | **OpenBMB MiniCPM-V swap** | $5K for one-line change |
| 🟢 P2 | **Off-brand Gradio theme (Bonus 2)** | Custom CSS, CVD slider |
| 🟢 P2 | **Agent trace (Bonus 4)** | Low effort |
| 🟢 P2 | **Demo video + social post** | Required to qualify |
| 🔵 SKIP | BFL Klein | Not relevant to VLM task |
| 🔵 SKIP | Fine-tune (Bonus 1) | High effort, time risk |

---

*Last updated: 2026-06-07*