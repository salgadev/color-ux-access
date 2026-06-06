"""
Modal app definition for color-ux-access.
v2: file-upload architecture (no Playwright in container needed).

Architecture:
  - Gradio UI: @modal.asgi_app() on a single sticky container (max_containers=1)
  - Image upload: Gradio File component → bytes → vlm_inference_fn (GPU)
  - Screenshot from local: user captures screen with OS tool, uploads PNG
"""
import os
import io

import modal

# ── App & Image ────────────────────────────────────────────────────────────────

app = modal.App("color-ux-access")

_LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

web_image = (
    modal.Image.debian_slim(python_version="3.12")
    .add_local_dir(_LOCAL_DIR, remote_path="/root/color_ux_access_src", copy=True)
    .uv_pip_install(
        "fastapi[standard]",
        "gradio>=5.0",
        "python-multipart",
        "openai>=1.0",
    )
)


# ── VLM Inference Function (GPU) ───────────────────────────────────────────────

@app.function(
    image=web_image,
    gpu="A10G",
    timeout=120,
    retries=1,
    secrets=[modal.Secret.from_name("hf-token-narwall")],
)
def vlm_inference_fn(image_bytes: bytes, prompt: str = "") -> dict:
    """
    Analyze a screenshot for colorblind accessibility issues using a 32B VLM.

    Args:
        image_bytes: PNG screenshot as raw bytes
        prompt: Optional override for the VLM system prompt

    Returns:
        JSON-serializable dict with WCAG findings
    """
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HF_API_TOKEN")
    if not hf_token:
        raise RuntimeError("HF_TOKEN / HF_API_TOKEN environment variable not set")

    from openai import OpenAI

    client = OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=hf_token,
    )

    import base64
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    system_prompt = (
        "You are an accessibility expert specializing in colorblind user experience. "
        "Analyze screenshots for WCAG 2.1 compliance issues. "
        "For each finding, cite the specific success criterion (1.1.1, 1.4.1, 1.4.3, or 1.4.11). "
        "Output a JSON object with this structure:\n"
        "{"
        '  "findings": ['
        '    {'
        '      "type": "Low Contrast | Color Only Information | Missing Text Alternative | Insufficient Non-Text Contrast",'
        '      "wcag_criterion": "1.4.1 | 1.4.3 | 1.1.1 | 1.4.11",'
        '      "description": "...",'
        '      "severity": "critical | serious | moderate",'
        '      "location": "Top-left, center, etc."'
        "    }"
        "  ],"
        '  "summary": "Overall assessment",'
        '  "passes": true/false'
        "}"
    )

    response = client.chat.completions.create(
        model="CohereLabs/aya-vision-32b",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or system_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            }
        ],
        max_tokens=1024,
        temperature=0.1,
    )

    import json
    content = response.choices[0].message.content
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])
    return json.loads(content)


# ── Screenshot Upload Function (CPU → calls GPU) ───────────────────────────────

@app.function(image=web_image, timeout=120)
def upload_screenshot(image_bytes: bytes) -> dict:
    """Receives screenshot bytes, schedules VLM inference on a GPU container."""
    try:
        return vlm_inference_fn.remote(image_bytes)
    except Exception as e:
        # Return a clean error dict — Gradio can't deserialize raw exceptions
        return {"error": str(e), "findings": [], "passes": False}


# ── Gradio ASGI App ────────────────────────────────────────────────────────────

@app.function(
    image=web_image,
    max_containers=1,
    timeout=300,
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def ui():
    """
    Gradio UI served as a Modal ASGI web app.
    Sticky session (max_containers=1) required for Gradio's internal state.
    """
    from gradio.routes import mount_gradio_app
    from fastapi import FastAPI

    import sys
    sys.path.insert(0, "/root/color_ux_access_src")
    # Note: color_ux_access.capture is not needed here — file upload goes directly to upload_screenshot.remote()

    def analyze_screenshot(file_obj):
        """
        Receive uploaded image file → bytes → VLM GPU → WCAG report.
        User captures their own screenshot (browser/OS screenshot tool) and uploads.
        This avoids Playwright in the Modal container entirely.
        """
        if file_obj is None:
            return {"error": "No image uploaded", "findings": [], "passes": False}

        # Gradio File with type="binary" passes raw bytes, not a file object
        # (upload_screenshot.remote expects bytes, so forward directly)
        image_bytes = file_obj if isinstance(file_obj, bytes) else file_obj.read()

        # Call Modal GPU function
        result = upload_screenshot.remote(image_bytes)
        return result

    import gradio as gr

    demo = gr.Interface(
        fn=analyze_screenshot,
        inputs=gr.File(
            label="Screenshot",
            file_types=[".png", ".jpg", ".jpeg", ".webp"],
            type="binary",
        ),
        outputs=gr.JSON(label="WCAG Accessibility Report"),
        title="Color-UX-Access",
        description=(
            "Upload a screenshot to check for colorblind accessibility issues (WCAG 2.1). "
            "Uses a 32B vision-language model. Capture your screen using OS/browser screenshot "
            "tool, then upload the image here."
        ),
    )

    return mount_gradio_app(app=FastAPI(), blocks=demo, path="/")