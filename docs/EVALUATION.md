# Sponsor Prizes + Bonus Quests — Evaluation

>评估 — high impact, least effort. Not all need to be implemented.

---

## Hackathon Requirements (must meet to qualify)

1. Model ≤32B parameters ✓ (aya-vision-32b = 32B)
2. Gradio app hosted as HF Space 🔲 (**primary gap — currently on Modal**)
3. Demo video + social post 🔲 (not started)

---

## Sponsor Prizes

### 🥇 HuggingFace — $15,000 cash (top awards)

**Requirement:** Best overall projects.

**Our alignment:**
- ≤32B ✓ (aya-vision-32b)
- Gradio app ✓ (local `app/app.py`)
- HF Space 🔲 (not deployed yet — primary blocker)
- Real problem solved for real user ✓ (CVD accessibility)

**Verdict: PRIMARY TARGET.** We already meet the core criteria. HF Space deploy is the only gap.

---

### 🤖 OpenAI — $10,000 + $100 Codex credits (first 1,000 participants)

**Requirement:** Use OpenAI model.

**Our alignment:** ❌
- We use CohereLabs/aya-vision-32b via HF Router (not OpenAI)
- Would require switching VLM to GPT-4o-mini or similar
- Worth considering ONLY if OpenAI has special award category that rewards this

**Verdict: LOW PRIORITY.** Not our model choice. Skip unless OpenBMB awards run out.

---

### 🔬 OpenBMB — $10,000 special awards ($5K per track)

**Requirement:** Use OpenBMB model (MiniCPM-V 4.6 for vision, MiniCPM-o 4.5 for omni-modal).

**Our alignment:** ⚠️ HIGH-VALUE SWAP — $5K per track
- MiniCPM-V 4.6 is a vision VLM (~4B params, well under 32B limit)
- Swap `CohereLabs/aya-vision-32b` → `openbmb/mini-cpm-v-4_6`
- Eligible for $5K Backyard AI track prize
- Discord: <@1268130730509074476>, <@1379652867916566572>, <@899634493458112512>

**Effort:** ~1 line change in `vlm/vlm_inference.py` (model name). HF Router compatible.

**Resources:**
- Model: https://huggingface.co/openbmb/MiniCPM-V-4.6
- Cookbook: https://opensqz.github.io/MiniCPM-V-CookBook/site/en/index.html
- GitHub: https://github.com/OpenBMB/MiniCPM-V-Apps

**Verdict: WORTH SWAPPING FOR.** $5K for minimal effort. **Evaluate after T5 (HF Space deploy).**

---

### 🎮 NVIDIA — 2× RTX 5080 GPUs (top projects)

**Requirement:** Top projects.

**Our alignment:** ✅ via HF Space deploy
- RTX 5080 goes to top projects overall
- No NVIDIA-specific integration needed
- Already on Modal which has NVIDIA GPUs

**Verdict: WIN BY DEFAULT.** No extra work — just build the best project.

---

### 🟦 Modal — $250 credits all + $20,000 winners

**Requirement:** Use Modal for deployment.

**Our alignment:** ✅ ALREADY DEPLOYED
- `narwall-tech--color-ux-access-ui.modal.run` is live
- We have $250 credits from participation

**Verdict: ✅ DONE.** Already deployed and working.

---

### 🌲 Cohere — Prize support

**Requirement:** Use Cohere model.

**Our alignment:** ✅ ALREADY USING IT
- `CohereLabs/aya-vision-32b` is our VLM
- Already aligned

**Verdict: ✅ DONE.** No extra work.

---

### 🖼️ Black Forest Labs — Prize support

**Models:** FLUX.2 [klein] — 4B text-to-image model (distilled 4-step inference).

**Our alignment:** ❌ NOT RELEVANT
- Klein is a text-to-image generation model, not a VLM
- Our task is accessibility analysis (VLM), not image generation
- No logical integration path for CVD simulation using BFL Klein

**Exception:** Could generate synthetic "before/after" accessibility remediation images — but that's a stretch and low-value for the hackathon demo.

**Verdict: SKIP.** Image generation doesn't serve our VLM accessibility analysis use case.

---

## Bonus Quests

### 🥇 Bonus 1: Well-Tuned — Fine-tuned model on HF

**Effort: HIGH. Impact: HIGH if judges value model work.**

- Option A: LoRA fine-tune on accessibility dataset
- Option B: Publish a specialized adapter for colorblind accessibility
- Risk: Time-consuming, may not converge in hackathon window

**Verdict: SKIP FOR NOW.** Only attempt if T3-T5 done and time remains.

---

### 🥈 Bonus 2: Off-Brand — Custom frontend past Gradio defaults

**Effort: LOW-MEDIUM. Impact: HIGH (first impression in demo).**

- Custom CSS for accessibility theme
- CVD comparison slider (original vs simulated side-by-side)
- Custom color palette matching colorblind-awareness theme
- JavaScript for smooth transitions

**Verdict: WORTH DOING.** Low effort, high demo impact. **Target after HF Space deploy (T5).**

---

### 🥉 Bonus 3: Llama Champion — llama.cpp runtime

**Effort: MEDIUM. Impact: MEDIUM.**

Two paths:
1. **Zerogpu on HF Space** — use `llama-cpp-python` with CUDA support via the whl index from the BFL guide. Text generation only (not vision).
2. **Hybrid vision** — VLM for image analysis + llama.cpp for text report generation.
3. **Modal fallback** — our current `vlm/vlm_inference_llama.py` for local GGUF.

**Integration with current architecture:**
- Current pipeline: screenshot → VLM (HF Router) → WCAG text report
- llama.cpp could generate the text report from structured data (not the vision part)
- Zerogpu path: tricky — need Python 3.12 + specific index URLs + Spaces GPU

**Verdict: MEDIUM PRIORITY.** Worth evaluating after HF Space deploy. The Zerogpu path is interesting for Bonus 3 (Llama Champion) + demonstrating hybrid architecture.

---

### 🎁 Bonus 4: Sharing is Caring — Shared agent trace on HF

**Effort: LOW. Impact: MEDIUM.**

- Save development conversation logs as HF Dataset
- Organize by phase: screenshot → CVD → VLM → report
- Include code snippets and lessons learned

**Verdict: WORTH DOING.** Low effort, demonstrates process quality. **Do alongside T7 (blog).**

---

### 📝 Bonus 5: Field Notes — Blog post on huggingface.co/blog

**Effort: LOW-MEDIUM. Impact: MEDIUM-HIGH.**

- Technical blog post about colorblind accessibility testing methodology
- Case study: problem → approach → WCAG findings → lessons
- Amplifies social reach for NARWALL too

**Verdict: DO THIS.** Low effort, high impact for hackathon scoring and NARWALL brand.

---

## Implementation Priority (High Impact, Least Effort)

| Priority | Task | Reason |
|----------|------|--------|
| 🔴 P0 | **HF Space deploy** | Required to qualify + compete for $15K + $250 Modal credits |
| 🔴 P0 | **Demo video + social post** | Required to qualify |
| 🟡 P1 | **Blog post (Bonus 5)** | Low effort, high impact |
| 🟡 P1 | **Off-brand Gradio theme (Bonus 2)** | Low effort, high demo impression |
| 🟡 P1 | **OpenBMB MiniCPM-V swap** | $10K special award for one-line model change |
| 🟢 P2 | **Agent trace (Bonus 4)** | Low effort, medium impact |
| 🟢 P2 | **Zerogpu/llama.cpp evaluation** | Medium effort, Bonus 3 credit |
| 🔵 SKIP | BFL Klein | Not relevant to VLM accessibility analysis |
| 🔵 SKIP | OpenAI models | Not our VLM choice |
| 🔵 SKIP | Fine-tune (Bonus 1) | High effort, time risk |

---

## Next: T5 — HF Space Deploy

Current blocker: our app uses Modal-specific `@modal.asgi_app()` decorator. Need to create a separate `app_space.py` that uses standard Gradio with `@spaces.GPU()` for VLM inference.

Steps:
1. Create `app_space.py` — standard Gradio, same UI as `app/app.py`
2. Replace `upload_screenshot` modal function with `@spaces.GPU(duration=120)` function
3. Use HF Router API for VLM (same as current `vlm/vlm_inference.py`)
4. Create HF Space: `color-ux-access` in `salgadev` org
5. Update README with Space URL
6. Deploy and verify