#!/usr/bin/env python3
"""
Generate Color-UX-Access hackathon demo video from fixture images.

Usage:
  python scripts/generate_demo_video.py

Requires: Pillow (in .venv), ffmpeg in PATH.
Output: demo_video_raw.mp4 (video only), then combine with TTS audio.
"""

import pathlib
import subprocess
import tempfile
import shutil

from PIL import Image, ImageDraw, ImageFont

FIXTURES_DIR = pathlib.Path("tests/fixtures")
OUTPUT_DIR = pathlib.Path("demo_output")
FRAME_DIR = OUTPUT_DIR / "frames"
VIDEO_RAW = OUTPUT_DIR / "demo_video_raw.mp4"

FPS = 24
FRAME_W, FRAME_H = 1280, 720

# Color scheme
BG_COLOR = (15, 17, 23)           # dark charcoal
ACCENT_COLOR = (30, 136, 229)     # blue (#1E88E5)
TEXT_COLOR = (255, 255, 255)
RED_COLOR = (239, 83, 80)         # issue highlight
GREEN_COLOR = (76, 175, 80)       # passed highlight

FONT_TITLE = None  # loaded lazily
FONT_BODY = None

def load_fonts():
    global FONT_TITLE, FONT_BODY
    if FONT_TITLE is None:
        # Try Segoe UI on Windows, fallback to default
        try:
            FONT_TITLE = ImageFont.truetype("C:/Windows/Fonts/seguiuli.ttf", 36)
            FONT_BODY = ImageFont.truetype("C:/Windows/Fonts/seguiuli.ttf", 22)
        except Exception:
            FONT_TITLE = ImageFont.load_default()
            FONT_BODY = ImageFont.load_default()


def load_fixture(name: str) -> Image.Image:
    path = FIXTURES_DIR / name
    img = Image.open(path).convert("RGB")
    # Scale to fit within 1280x720 while preserving aspect ratio
    img.thumbnail((FRAME_W - 80, FRAME_H - 160), Image.LANCZOS)
    return img


def create_frame(bg_color=BG_COLOR) -> Image.Image:
    frame = Image.new("RGB", (FRAME_W, FRAME_H), bg_color)
    return frame


def paste_center(target: Image.Image, img: Image.Image, x_offset=0, y_offset=0):
    w, h = img.size
    tw, th = target.size
    x = (tw - w) // 2 + x_offset
    y = (th - h) // 2 + y_offset
    target.paste(img, (x, y))


def draw_centered_text(draw: ImageDraw.Draw, text: str, y: int,
                       font=None, color=TEXT_COLOR, max_width=None):
    if font is None:
        font = FONT_BODY
    if max_width is None:
        max_width = FRAME_W - 80
    # Word wrap
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_h = font.getbbox("A")[3] - font.getbbox("A")[1] + 8
    total_h = len(lines) * line_h
    start_y = y - total_h // 2
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (FRAME_W - lw) // 2
        draw.text((x, start_y + i * line_h), line, font=font, fill=color)


def add_title_bar(frame: Image.Image, title: str):
    draw = ImageDraw.Draw(frame)
    # Top bar
    draw.rectangle([(0, 0), (FRAME_W, 50)], fill=ACCENT_COLOR)
    draw.text((20, 8), title, font=FONT_TITLE, fill=TEXT_COLOR)


def add_watermark(frame: Image.Image, text: str = "Color-UX-Access | HF Build Small Hackathon"):
    draw = ImageDraw.Draw(frame)
    bbox = draw.textbbox((0, 0), text, font=FONT_BODY)
    w = bbox[2] - bbox[0]
    draw.text((FRAME_W - w - 16, FRAME_H - 30), text, font=FONT_BODY, fill=(120, 130, 145))


def make_title_frame(title: str, subtitle: str = "", duration_frames=48) -> list[Image.Image]:
    """Create a centered title frame."""
    frames = []
    for i in range(duration_frames):
        frame = create_frame()
        draw = ImageDraw.Draw(frame)
        # Fade in
        alpha = min(255, (i + 1) * 12)
        alpha_color = (ACCENT_COLOR[0], ACCENT_COLOR[1], ACCENT_COLOR[2], alpha)

        # Title
        bbox = draw.textbbox((0, 0), title, font=FONT_TITLE)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (FRAME_W - tw) // 2
        ty = FRAME_H // 2 - 40
        if i < 24:
            fade_alpha = max(0, 255 - (24 - i) * 16)
            title_color = (255, 255, 255)
        else:
            title_color = TEXT_COLOR
        draw.text((tx, ty), title, font=FONT_TITLE, fill=title_color)

        if subtitle:
            bbox2 = draw.textbbox((0, 0), subtitle, font=FONT_BODY)
            sw = bbox2[2] - bbox2[0]
            sx = (FRAME_W - sw) // 2
            sy = ty + th + 16
            draw.text((sx, sy), subtitle, font=FONT_BODY, fill=(180, 190, 200))

        add_watermark(frame)
        frames.append(frame)
    return frames


def make_fixture_frame(original_name: str, cvd_names: list[str],
                       analysis_text: str,
                       title_text: str = "Colorblind Accessibility Analysis",
                       hold_frames=72) -> list[Image.Image]:
    """
    Create a sequence of frames: original → CVD simulations → WCAG report.
    """
    load_fonts()
    original = load_fixture(original_name)

    frames = []

    # Frame 1: Original image with label
    for _ in range(8):
        frame = create_frame()
        add_title_bar(frame, title_text)
        draw = ImageDraw.Draw(frame)
        paste_center(frame, original, y_offset=-40)
        # Label
        label = "ORIGINAL"
        bbox = draw.textbbox((0, 0), label, font=FONT_TITLE)
        lw = bbox[2] - bbox[0]
        lx = (FRAME_W - lw) // 2
        draw.rectangle([(lx - 8, FRAME_H // 2 + original.size[1] // 2 + 4),
                        (lx + lw + 8, FRAME_H // 2 + original.size[1] // 2 + 36)],
                       fill=ACCENT_COLOR)
        draw.text((lx, FRAME_H // 2 + original.size[1] // 2 + 8), label, font=FONT_TITLE, fill=TEXT_COLOR)
        add_watermark(frame)
        frames.append(frame)

    # Frames 2-N: CVD simulations with labels
    cvd_labels = {
        "deuteranopia": "Deuteranopia (Green-Blind)",
        "protanopia": "Protanopia (Red-Blind)",
        "tritanopia": "Tritanopia (Blue-Blind)",
    }
    for cvd_name in cvd_names:
        cvd_img = load_fixture(cvd_name)
        base_cvd_type = cvd_name.replace(original_name.replace(".png", "") + "_", "")
        label = cvd_labels.get(base_cvd_type, base_cvd_type.upper())

        for i in range(8):
            frame = create_frame()
            add_title_bar(frame, title_text)
            draw = ImageDraw.Draw(frame)
            paste_center(frame, cvd_img, y_offset=-40)

            # CVD label with colored border
            bbox = draw.textbbox((0, 0), label, font=FONT_TITLE)
            lw = bbox[2] - bbox[0]
            lx = (FRAME_W - lw) // 2
            border_color = (239, 83, 80)  # red to indicate issue
            draw.rectangle([(lx - 8, FRAME_H // 2 + cvd_img.size[1] // 2 + 4),
                            (lx + lw + 8, FRAME_H // 2 + cvd_img.size[1] // 2 + 36)],
                           fill=border_color)
            draw.text((lx, FRAME_H // 2 + cvd_img.size[1] // 2 + 8), label, font=FONT_TITLE, fill=TEXT_COLOR)
            add_watermark(frame)
            frames.append(frame)

    # WCAG Report frame (hold)
    for _ in range(hold_frames):
        frame = create_frame()
        add_title_bar(frame, "WCAG 2.1 Accessibility Report")
        draw = ImageDraw.Draw(frame)

        # Report panel
        draw.rectangle([(60, 70), (FRAME_W - 60, FRAME_H - 60)], fill=(22, 25, 32))
        draw.rectangle([(60, 70), (FRAME_W - 60, FRAME_H - 60)], outline=ACCENT_COLOR, width=2)

        # Report title
        draw.text((80, 84), "WCAG 2.1 Colorblind Accessibility Report", font=FONT_TITLE, fill=ACCENT_COLOR)

        # Issues
        y = 140
        issues = [
            ("ISSUE", "Low contrast text on form fields", "WCAG 1.4.3 — Contrast ≥ 4.5:1"),
            ("ISSUE", "Color-dependent validation (red/green only)", "WCAG 1.4.1 — Color not sole means"),
            ("RECOMMENDATION", "Add icons + text labels to status badges", "WCAG 1.3.3 — Sensory characteristics"),
        ]
        for sev, desc, ref in issues:
            color = RED_COLOR if sev == "ISSUE" else ACCENT_COLOR
            draw.text((80, y), f"[{sev}]", font=FONT_BODY, fill=color)
            draw.text((80, y + 28), desc, font=FONT_BODY, fill=TEXT_COLOR)
            draw.text((80, y + 54), ref, font=FONT_BODY, fill=(140, 150, 165))
            y += 90

        # Pass rate badge
        draw.rectangle([(FRAME_W - 260, FRAME_H - 120), (FRAME_W - 80, FRAME_H - 76)], fill=GREEN_COLOR)
        draw.text((FRAME_W - 250, FRAME_H - 115), "3 FINDINGS — ACTIONABLE", font=FONT_BODY, fill=TEXT_COLOR)
        add_watermark(frame)
        frames.append(frame)

    return frames


def make_accessible_frame(original_name: str, accessible_name: str,
                          hold_frames=48) -> list[Image.Image]:
    """Show original → accessible fix."""
    load_fonts()
    original = load_fixture(original_name)
    accessible = load_fixture(accessible_name)

    frames = []
    for i in range(8):
        frame = create_frame()
        add_title_bar(frame, "Fix Applied — Accessible Version")
        paste_center(frame, accessible, y_offset=-40)
        draw = ImageDraw.Draw(frame)
        label = "NOW ACCESSIBLE"
        bbox = draw.textbbox((0, 0), label, font=FONT_TITLE)
        lw = bbox[2] - bbox[0]
        lx = (FRAME_W - lw) // 2
        draw.rectangle([(lx - 8, FRAME_H // 2 + accessible.size[1] // 2 + 4),
                        (lx + lw + 8, FRAME_H // 2 + accessible.size[1] // 2 + 36)],
                       fill=GREEN_COLOR)
        draw.text((lx, FRAME_H // 2 + accessible.size[1] // 2 + 8), label, font=FONT_TITLE, fill=TEXT_COLOR)
        add_watermark(frame)
        frames.append(frame)

    for _ in range(hold_frames):
        frame = create_frame()
        add_title_bar(frame, "Fix Applied — Accessible Version")
        draw = ImageDraw.Draw(frame)
        paste_center(frame, accessible, y_offset=-40)
        draw.rectangle([(lx - 8, FRAME_H // 2 + accessible.size[1] // 2 + 4),
                        (lx + lw + 8, FRAME_H // 2 + accessible.size[1] // 2 + 36)],
                       fill=GREEN_COLOR)
        draw.text((lx, FRAME_H // 2 + accessible.size[1] // 2 + 8), label, font=FONT_TITLE, fill=TEXT_COLOR)
        # Checkmark
        draw.text((lx + lw + 20, FRAME_H // 2 + accessible.size[1] // 2 + 4),
                  "✓ FIXED", font=FONT_TITLE, fill=GREEN_COLOR)
        add_watermark(frame)
        frames.append(frame)

    return frames


def frames_to_video(frames: list[Image.Image], output_path: pathlib.Path, fps=FPS):
    """Write frames as a lossless AVI, then re-encode to MP4."""
    temp_dir = OUTPUT_DIR / "raw_frames"
    temp_dir.mkdir(parents=True, exist_ok=True)

    print(f"Writing {len(frames)} frames...")
    for i, frame in enumerate(frames):
        frame.save(temp_dir / f"frame_{i:04d}.png")
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(frames)}")

    print("Encoding video...")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(temp_dir / "frame_%04d.png"),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg stderr:", result.stderr[-1000:])
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-300:]}")
    print(f"Video saved: {output_path}")
    # Cleanup temp frames
    shutil.rmtree(temp_dir)


def build_demo():
    load_fonts()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FRAME_DIR.mkdir(parents=True, exist_ok=True)

    all_frames: list[Image.Image] = []

    # === SEQUENCE ===
    # 1. Title
    all_frames.extend(make_title_frame(
        "Color-UX-Access",
        "Automated Colorblind Accessibility Testing with 32B Vision-Language Models",
        duration_frames=48
    ))

    # 2. What is CVD?
    all_frames.extend(make_title_frame(
        "What is Color Vision Deficiency?",
        "1 in 12 men, 1 in 200 women — affects 350M+ people globally",
        duration_frames=48
    ))

    # 3. Form validation — original → CVD → report → accessible
    all_frames.extend(make_fixture_frame(
        "form_validation_color_only.png",
        [
            "form_validation_color_only_deuteranopia.png",
            "form_validation_color_only_protanopia.png",
            "form_validation_color_only_tritanopia.png",
        ],
        analysis_text="Low contrast + color-only validation",
        title_text="Form Validation — Colorblind Simulation",
        hold_frames=72
    ))
    all_frames.extend(make_accessible_frame(
        "form_validation_color_only.png",
        "form_validation_accessible.png",
        hold_frames=48
    ))

    # 4. Status badges
    all_frames.extend(make_fixture_frame(
        "status_badges_color_only.png",
        [
            "status_badges_color_only_deuteranopia.png",
            "status_badges_color_only_protanopia.png",
            "status_badges_color_only_tritanopia.png",
        ],
        analysis_text="",
        title_text="Status Badges — Colorblind Simulation",
        hold_frames=72
    ))
    all_frames.extend(make_accessible_frame(
        "status_badges_color_only.png",
        "status_badges_accessible.png",
        hold_frames=48
    ))

    # 5. Button panel
    all_frames.extend(make_fixture_frame(
        "button_panel_color_only.png",
        [
            "button_panel_color_only_deuteranopia.png",
            "button_panel_color_only_protanopia.png",
            "button_panel_color_only_tritanopia.png",
        ],
        analysis_text="",
        title_text="Button Panel — Colorblind Simulation",
        hold_frames=72
    ))
    all_frames.extend(make_accessible_frame(
        "button_panel_color_only.png",
        "button_panel_accessible.png",
        hold_frames=48
    ))

    # 6. Closing title
    all_frames.extend(make_title_frame(
        "Try it now — salgadev-color-ux-access.hf.space",
        "Built with CohereLabs aya-vision-32B + HuggingFace Spaces",
        duration_frames=96
    ))

    print(f"Total frames: {len(all_frames)}")
    frames_to_video(all_frames, VIDEO_RAW)
    duration = len(all_frames) / FPS
    print(f"Video duration: {duration:.1f}s ({len(all_frames)} frames @ {FPS}fps)")
    return VIDEO_RAW


if __name__ == "__main__":
    build_demo()