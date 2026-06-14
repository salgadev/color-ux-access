"""
server_app.py — gr.Server entrypoint with carousel front page and API endpoints.

Serves:
  GET  /                → HTML carousel (first slide embeds /access via iframe)
  GET  /access          → Mounted Color-UX-Access Gradio app (same as app.py)
  POST /api/generate_gallery  → api_generate_gallery_from_bytes → JSON
  POST /api/analyze_vlm       → api_analyze_cvd_grid_from_bytes → JSON
  POST /api/wcag_report       → api_report_from_json → Markdown
"""

# GUARDRAIL: Do not add self-modifying or patch scripts.
# Implement changes directly in this file or in helper modules with tests.
# Root-level *fix*.py / apply_*.py files are prohibited.

from __future__ import annotations

import os
import base64
from typing import List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

import gradio as gr

# Import the existing Gradio Blocks app from app.py (must not modify app.py)
from app import demo

# Import backend wrappers
from backend_api import (
    api_generate_gallery_from_bytes,
    api_analyze_cvd_grid_from_bytes,
    api_report_from_json,
)

# ── Carousel HTML ─────────────────────────────────────────────────────────────

_CAROUSEL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>NARWALL Tech — Accessibility Suite</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background: #0f1117;
      color: #e8eaf0;
      font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }

    header {
      text-align: center;
      margin-bottom: 1.5rem;
    }

    header h1 {
      font-size: 1.6rem;
      font-weight: 700;
      color: #ffffff;
      letter-spacing: -0.02em;
    }

    header p {
      font-size: 0.85rem;
      color: #8b9099;
      margin-top: 0.3rem;
    }

    .carousel-wrapper {
      width: 80vw;
      max-width: 1200px;
      overflow: hidden;
      border-radius: 16px;
      position: relative;
    }

    .carousel {
      display: flex;
      transition: transform 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    }

    .slide {
      min-width: 100%;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      padding: 0.5rem;
    }

    .slide-heading {
      font-size: 1rem;
      font-weight: 600;
      color: #c8cdd6;
      padding-left: 0.25rem;
    }

    .slide-description {
      font-size: 0.8rem;
      color: #6b7280;
      padding-left: 0.25rem;
    }

    iframe {
      width: 100%;
      height: 70vh;
      border: none;
      border-radius: 12px;
      display: block;
    }

    .controls {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 0.75rem;
      padding: 0 0.5rem;
    }

    .btn {
      background: #1e2433;
      color: #e8eaf0;
      border: 1px solid #2d3548;
      border-radius: 8px;
      padding: 0.45rem 1.2rem;
      font-size: 0.85rem;
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s;
      font-family: inherit;
    }

    .btn:hover { background: #2a3245; border-color: #3d4a66; }
    .btn:active { background: #151a27; }

    .dots {
      display: flex;
      gap: 0.5rem;
      align-items: center;
    }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #2d3548;
      cursor: pointer;
      transition: background 0.2s;
    }

    .dot.active { background: #3b82f6; }
  </style>
</head>
<body>

<header>
  <h1>NARWALL Tech — Accessibility Suite</h1>
  <p>Multi-tool testing platform powered by AI</p>
</header>

<div class="carousel-wrapper">
  <div class="carousel" id="carousel">
    <div class="slide">
      <div class="slide-heading">Color-UX-Access</div>
      <div class="slide-description">Colorblind accessibility testing — screenshot → CVD simulation → WCAG report</div>
      <iframe src="/access" title="Color-UX-Access"></iframe>
    </div>
    <div class="slide">
      <div class="slide-heading">Tool Slide 2</div>
      <div class="slide-description">Coming soon — additional accessibility testing tools</div>
      <iframe srcdoc="<div style='display:flex;align-items:center;justify-content:center;height:70vh;color:#444;font-family:Inter,sans-serif;font-size:1.2rem;'>🚧 More tools coming soon</div>" title="Placeholder tool"></iframe>
    </div>
  </div>
</div>

<div class="controls">
  <button class="btn" id="prev-btn" onclick="moveSlide(-1)">&#8592; Prev</button>
  <div class="dots" id="dots"></div>
  <button class="btn" id="next-btn" onclick="moveSlide(1)">Next &#8594;</button>
</div>

<script>
  const totalSlides = 2;
  let index = 0;

  function updateCarousel() {
    const carousel = document.getElementById('carousel');
    carousel.style.transform = 'translateX(-' + (index * 100) + '%)';
    // Update dots
    const dots = document.getElementById('dots').children;
    for (let i = 0; i < dots.length; i++) {
      dots[i].classList.toggle('active', i === index);
    }
  }

  function moveSlide(delta) {
    index = (index + delta + totalSlides) % totalSlides;
    updateCarousel();
  }

  // Build dots
  const dotsContainer = document.getElementById('dots');
  for (let i = 0; i < totalSlides; i++) {
    const dot = document.createElement('div');
    dot.className = 'dot' + (i === 0 ? ' active' : '');
    dot.onclick = () => { index = i; updateCarousel(); };
    dotsContainer.appendChild(dot);
  }

  // Keyboard navigation
  document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowRight') moveSlide(1);
    if (e.key === 'ArrowLeft') moveSlide(-1);
  });
</script>

</body>
</html>
"""


# ── gr.Server setup ────────────────────────────────────────────────────────────

# Create the Server — this is a FastAPI subclass with Gradio's API engine
app = gr.Server(title="NARWALL Tech — Accessibility Suite")

# Mount the existing Color-UX-Access Blocks app at /access
# This serves the same UI as `uv run app.py`
app.mount("/access", demo, name="color_ux_access")


# ── Custom routes ─────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve the HTML carousel page at /."""
    return HTMLResponse(content=_CAROUSEL_HTML, media_type="text/html")


# ── API endpoints ─────────────────────────────────────────────────────────────

async def _generate_gallery_handler(data: dict) -> dict:
    """Handler shared by @app.api and FastAPI POST /api/generate_gallery."""
    b64 = data.get("image", "")
    if not b64:
        return {"error": "Missing 'image' field in request body", "items": []}
    try:
        image_bytes = base64.b64decode(b64)
    except Exception as e:
        return {"error": f"Could not decode base64 image: {e}", "items": []}
    try:
        gallery = api_generate_gallery_from_bytes(image_bytes)
    except ValueError as e:
        return {"error": str(e), "items": []}
    items = []
    for img_bytes, label in gallery:
        items.append({
            "image": base64.b64encode(img_bytes).decode("utf-8"),
            "label": label,
        })
    return {"items": items}


async def _analyze_vlm_handler(data: dict) -> dict:
    """Handler shared by @app.api and FastAPI POST /api/analyze_vlm."""
    items = data.get("items", [])
    if not items:
        return {"error": "Empty gallery — upload an image first.", "findings": [], "passes": False}
    gallery = []
    for item in items:
        try:
            img_bytes = base64.b64decode(item.get("image", ""))
            label = item.get("label", "Unknown")
            gallery.append((img_bytes, label))
        except Exception:
            continue
    if not gallery:
        return {"error": "No valid images in gallery", "findings": [], "passes": False}
    return api_analyze_cvd_grid_from_bytes(gallery)


# @app.api — Gradio client API (for programmatic callers via gradio_client)
@app.api(name="generate_gallery")
async def generate_gallery_endpoint(data: dict) -> dict:
    return await _generate_gallery_handler(data)


@app.api(name="analyze_vlm")
async def analyze_vlm_endpoint(data: dict) -> dict:
    return await _analyze_vlm_handler(data)


@app.api(name="wcag_report")
async def wcag_report_endpoint(data: dict) -> str:
    return api_report_from_json(data)


# FastAPI routes — accessible via HTTP/TestClient at /api/*
@app.post("/api/generate_gallery")
async def fastapi_generate_gallery(data: dict) -> dict:
    """POST /api/generate_gallery — same as @app.api generate_gallery for HTTP clients."""
    return await _generate_gallery_handler(data)


@app.post("/api/analyze_vlm")
async def fastapi_analyze_vlm(data: dict) -> dict:
    """POST /api/analyze_vlm — same as @app.api analyze_vlm for HTTP clients."""
    return await _analyze_vlm_handler(data)


@app.post("/api/wcag_report")
async def fastapi_wcag_report(data: dict) -> str:
    """POST /api/wcag_report — same as @app.api wcag_report for HTTP clients."""
    return api_report_from_json(data)


# ── Local development entrypoint ──────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    app.launch(server_name="0.0.0.0", server_port=port)