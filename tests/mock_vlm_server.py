"""Mock VLM server for E2E testing - returns deterministic WCAG responses."""
import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class VLMRequest(BaseModel):
    prompt: str
    image_base64: str

# Deterministic mock responses based on CVD type in prompt
MOCK_RESPONSES = {
    "Normal vision (original design)": {
        "findings": [
            {
                "type": "Low Contrast",
                "wcag_criterion": "1.4.3",
                "severity": "moderate",
                "description": "Body text contrast ratio is 3.8:1 — below the 4.5:1 AA minimum",
                "location": "Main content area"
            }
        ],
        "summary": "1 moderate contrast issue found in original design",
        "passes": False
    },
    "Protanopia (red-blind)": {
        "findings": [
            {
                "type": "Color Only Information",
                "wcag_criterion": "1.4.1",
                "severity": "critical",
                "description": "Error state relies solely on red color with no icon or text indicator",
                "location": "Form validation, top-right"
            },
            {
                "type": "Low Contrast",
                "wcag_criterion": "1.4.3",
                "severity": "serious",
                "description": "Red button text on dark background drops to 2.1:1 for protanopes",
                "location": "Primary CTA button"
            }
        ],
        "summary": "Critical color-only information and serious contrast issues for protanopia",
        "passes": False
    },
    "Deuteranopia (green-blind)": {
        "findings": [
            {
                "type": "Color Only Information",
                "wcag_criterion": "1.4.1",
                "severity": "critical",
                "description": "Success state relies solely on green color with no secondary indicator",
                "location": "Form validation, center"
            }
        ],
        "summary": "Critical color-only information issue for deuteranopia",
        "passes": False
    },
    "Tritanopia (blue-blind)": {
        "findings": [
            {
                "type": "Low Contrast",
                "wcag_criterion": "1.4.3",
                "severity": "moderate",
                "description": "Blue link text on white background drops to 3.2:1 for tritanopes",
                "location": "Navigation links"
            }
        ],
        "summary": "Moderate contrast issue for tritanopia",
        "passes": False
    },
    "Severe Protanopia (red-blind)": {
        "findings": [
            {
                "type": "Color Only Information",
                "wcag_criterion": "1.4.1",
                "severity": "critical",
                "description": "All red/green distinctions lost; error/success states indistinguishable",
                "location": "Form validation throughout"
            },
            {
                "type": "Insufficient Non-Text Contrast",
                "wcag_criterion": "1.4.11",
                "severity": "serious",
                "description": "Chart segments using red/green become invisible",
                "location": "Dashboard charts"
            }
        ],
        "summary": "Severe protanopia: multiple critical and serious issues",
        "passes": False
    },
    "Severe Deuteranopia (green-blind)": {
        "findings": [
            {
                "type": "Color Only Information",
                "wcag_criterion": "1.4.1",
                "severity": "critical",
                "description": "All red/green distinctions lost; error/success states indistinguishable",
                "location": "Form validation throughout"
            }
        ],
        "summary": "Severe deuteranopia: critical color-only information issues",
        "passes": False
    },
    "Protanomaly (red-weak)": {
        "findings": [
            {
                "type": "Low Contrast",
                "wcag_criterion": "1.4.3",
                "severity": "moderate",
                "description": "Red elements appear dimmer; contrast reduced for orange/red text",
                "location": "Warning banners"
            }
        ],
        "summary": "Mild contrast issues for protanomaly",
        "passes": False
    },
    "Deuteranomaly (green-weak)": {
        "findings": [
            {
                "type": "Low Contrast",
                "wcag_criterion": "1.4.3",
                "severity": "moderate",
                "description": "Green elements less distinguishable; yellow/green confusion",
                "location": "Status indicators"
            }
        ],
        "summary": "Mild contrast issues for deuteranomaly (most common CVD)",
        "passes": False
    },
    "Tritanomaly (blue-weak)": {
        "findings": [
            {
                "type": "Low Contrast",
                "wcag_criterion": "1.4.3",
                "severity": "moderate",
                "description": "Blue/violet hues shift; blue buttons harder to distinguish",
                "location": "Action buttons"
            }
        ],
        "summary": "Mild contrast issues for tritanomaly",
        "passes": False
    },
}

@app.post("/")
async def vlm_endpoint(request: VLMRequest):
    """Mock VLM endpoint that returns deterministic responses based on prompt content."""
    prompt = request.prompt
    
    # Find which CVD type this prompt is for
    cvd_type = "Normal vision (original design)"  # default
    for label in MOCK_RESPONSES.keys():
        if label in prompt:
            cvd_type = label
            break
    
    response = MOCK_RESPONSES.get(cvd_type, MOCK_RESPONSES["Normal vision (original design)"])
    return {"response": json.dumps(response)}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)