# CVD User-Centric Audit Model
# Understanding accessibility auditing from the colorblind user's perspective

## The Core Problem

The colorblind user does not see "incorrect colors" — they see **functional ambiguity**. When a design relies on color to convey state, action, or meaning, the colorblind user faces real-time uncertainty.

**Real example:**
- Form field with red border (error) vs green border (valid) → for deuteranopes both look identical (both brownish-gray)
- The user does not know if their form was accepted or has errors until they read the helper text or rely on another indicator

## What the Colorblind User Actually Does on a Page

Typical mental flow:

1. **Sees an interface** → intends an action (e.g., "submit")
2. **Evaluates visible elements** → looks for buttons, fields, indicators
3. **Elements that depend on color do not convey their state** → requires additional inference or trial-and-error
4. **If there is no text label, dedicated icon, or brightness contrast, the element is inaccessible**

### Typically Failing Elements

| Element | How it fails for CVD | What the user must rely on |
|---------|----------------------|---------------------------|
| Form validation borders | Error (red) vs success (green) confuse | Error text, icon with label, or brightness contrast |
| Nav active state | Active vs inactive color identical | Shape, border, text, position |
| Primary/secondary buttons | Green vs red indistinguishable | Text label, icon, brightness |
| Status badges | Online (green) vs offline (red) confuse | Icon + text, not color alone |
| Charts/data | Color-coded series indistinguishable | Patterns, data labels |
| Links | Blue vs black text both dark | Underline, hover state |
| Required field markers | Red asterisk not visible | Text "required", different border |

## The Proposed Audit Model

### Concept: "Confusion as an Inaccessibility Signal"

```
Screenshot → Simulate CVD → Ask the model to describe specific elements
                                              ↓
                          If the model is confused = the design is inaccessible
                          for real colorblind users
```

**Analogy:** The vision model acts as a "user proxy" under CVD simulation. When the model cannot distinguish one button from another, the colorblind user cannot either.

### Lightweight Implementation (Region-Based Analysis)

Instead of analyzing the entire image with a large VLM:

1. **Crop** the region of interest (a form, a button group, a data table)
2. **Specific prompt:** "Describe this form: which fields are required? Which button is 'submit' vs 'cancel'? Are there error indicators?"
3. **Model responds with inference** — incorrect inference = a finding

### Example Regional Prompt

```
You are viewing this page as a person with deuteranopia (red-green color blindness).
Describe the form below. Specifically:
- Which button is the primary action (submit/continue)?
- Which button is the secondary/cancel action?
- Are there any visible error states on the fields?
- Is there a "required" indicator on any field?
- Can you tell which fields have validation errors vs success?
```

### Response → CVD Finding

| Model Response | Finding |
|---------------|---------|
| "Both buttons look the same to me" | Buttons are indistinguishable without color |
| "I can't tell which field has an error" | Validation states invisible |
| "No required markers visible" | Required indicators inaccessible |
| "The submit button appears disabled" | Insufficient contrast for active state |

## Why This Works Better Than Automated WCAG

Traditional WCAG verifies contrast ratios, color requirements, and heuristics. But:

1. **WCAG can pass** (sufficient contrast) and still be **unusable for CVD** if color-coding is the only differentiator
2. **A human colorblind reviewer** could identify the problem, but it is slow and expensive
3. **Simulation + VLM** captures the real colorblind user experience at scale

## CVD Variants and Their Specific Confusions

| CVD | What confuses | Typical UI impact |
|-----|---------------|-------------------|
| Deuteranopia (most common) | Red=green, brown=dark green | Form validation, status badges, buttons |
| Protanopia | Red=black, green=brown | Errors, red alerts invisible |
| Tritanopia | Blue=green, yellow=orange | Charts, temperature/color indicators |
| Achromatopsia | Everything in grayscale | Entirely dependent on brightness/shape |

## Audit Flow (Implemented)

```
Screenshot → CVD Simulation (10 variants) → VLM analyzes all variants
                                              ↓
                     VLM identifies problem regions across all CVD types
                     → WCAG 2.1 findings per type → Markdown report
```

**Current implementation:** `app.py` → `generate_cvd_gallery()` produces all 10 CVD variants → `analyze_with_vlm()` sends the original screenshot to Modal endpoint → VLM returns structured WCAG JSON → `format_wcag_report()` renders as Markdown.

**Design reference:** `vlm/analyzer.py` can implement `audit_region()` for targeted region-based analysis (future enhancement).

---

*Last updated: 2026-06-08*
*Open questions (design reference, not blocking):*
- Q2: Should the lighter model describe a region or explicitly evaluate if it's "accessible"?
- Q3: Are there elements beyond forms/buttons to prioritize first?