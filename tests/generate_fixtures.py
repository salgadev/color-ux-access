"""
Generate synthetic UI screenshots for local CVD testing.
Each fixture pair: [clean] vs [cvd_problematic] version of same UI.
"""
from PIL import Image, ImageDraw, ImageFont
import os
from color_ux_access.cvd_sim import simulate_cvd

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
os.makedirs(FIXTURE_DIR, exist_ok=True)

# Colors (RGB)
CLEAN_BLUE = (59, 130, 246)
CLEAN_GRAY = (100, 100, 100)
CLEAN_WHITE = (255, 255, 255)
BG_LIGHT = (248, 249, 250)

# CVD-problematic colors (red/green that confuse CVD users)
ERROR_RED = (220, 53, 69)
SUCCESS_GREEN = (40, 167, 69)
ERROR_RED_HEX = '#DC3545'
SUCCESS_GREEN_HEX = '#28A745'

# ---------------------------------------------------------------------------
# Fixture 1: Form validation — BAD (color-only) vs GOOD (icon+text)
# ---------------------------------------------------------------------------
def make_form_validation():
    """Form with red/green validation borders — indistinguishable for CVD."""
    w, h = 400, 220
    img = Image.new('RGB', (w, h), BG_LIGHT)
    d = ImageDraw.Draw(img)

    # Draw form container
    d.rectangle([20, 20, w-20, h-20], fill=CLEAN_WHITE, outline=(200,200,200), width=1)

    # Email label + field
    d.text((30, 35), 'Email', fill=(50,50,50))
    d.rectangle([30, 55, 370, 80], outline=ERROR_RED, width=2)  # error state border

    # Password label + field
    d.text((30, 95), 'Password', fill=(50,50,50))
    d.rectangle([30, 115, 370, 140], outline=SUCCESS_GREEN, width=2)  # valid state border

    # Submit button (green background — CVD confusing)
    d.rectangle([30, 160, 180, 195], fill=SUCCESS_GREEN)
    d.text((60, 170), 'SUBMIT', fill=CLEAN_WHITE)

    # Cancel button (red outline — CVD confusing with submit)
    d.rectangle([195, 160, 370, 195], outline=ERROR_RED, width=2)
    d.text((240, 170), 'CANCEL', fill=ERROR_RED)

    path = os.path.join(FIXTURE_DIR, 'form_validation_color_only.png')
    img.save(path)
    return path


def make_form_validation_accessible():
    """Same form with icon+text redundancy — CVD accessible."""
    w, h = 400, 260
    img = Image.new('RGB', (w, h), BG_LIGHT)
    d = ImageDraw.Draw(img)

    # Form container
    d.rectangle([20, 20, w-20, h-20], fill=CLEAN_WHITE, outline=(200,200,200), width=1)

    # Email with error indicator (icon + text + border style)
    d.text((30, 35), 'Email *', fill=(50,50,50))
    d.rectangle([30, 55, 370, 80], outline=(180,180,180), width=2)  # gray border
    d.text((35, 60), '✗ Invalid email', fill=ERROR_RED)  # icon + text

    # Password with valid indicator
    d.text((30, 95), 'Password *', fill=(50,50,50))
    d.rectangle([30, 115, 370, 140], outline=(180,180,180), width=2)
    d.text((35, 120), '✓ Password looks good', fill=(0, 120, 50))  # icon + text

    # Submit with clear label
    d.rectangle([30, 160, 180, 195], fill=CLEAN_BLUE)
    d.text((60, 170), '▶ SUBMIT', fill=CLEAN_WHITE)

    # Cancel with clear label
    d.rectangle([195, 160, 370, 195], outline=CLEAN_GRAY, width=2)
    d.text((240, 170), '○ CANCEL', fill=CLEAN_GRAY)

    path = os.path.join(FIXTURE_DIR, 'form_validation_accessible.png')
    img.save(path)
    return path


# ---------------------------------------------------------------------------
# Fixture 2: Status badges — BAD (color-only) vs GOOD (icon+text)
# ---------------------------------------------------------------------------
def make_status_badges_color_only():
    """Row of status badges using only color — CVD invisible distinctions."""
    w, h = 500, 100
    img = Image.new('RGB', (w, h), BG_LIGHT)
    d = ImageDraw.Draw(img)

    labels = ['Online', 'Offline', 'Warning', 'Error']
    colors = [(40, 167, 69), (108, 117, 125), (255, 193, 7), (220, 53, 69)]

    for i, (label, color) in enumerate(zip(labels, colors)):
        x = 20 + i * 120
        d.ellipse([x, 25, x+90, 75], fill=color)
        d.text((x+15, 42), label, fill=(255,255,255))

    path = os.path.join(FIXTURE_DIR, 'status_badges_color_only.png')
    img.save(path)
    return path


def make_status_badges_accessible():
    """Same badges with icon+text — CVD distinguishable."""
    w, h = 500, 120
    img = Image.new('RGB', (w, h), BG_LIGHT)
    d = ImageDraw.Draw(img)

    badges = [
        ('✓', 'Online', (40, 167, 69)),
        ('○', 'Offline', (108, 117, 125)),
        ('⚠', 'Warning', (255, 193, 7)),
        ('✗', 'Error', (220, 53, 69)),
    ]

    for i, (icon, label, color) in enumerate(badges):
        x = 20 + i * 120
        d.ellipse([x, 25, x+90, 75], fill=color)
        d.text((x+5, 30), f'{icon} {label}', fill=(255,255,255))

    path = os.path.join(FIXTURE_DIR, 'status_badges_accessible.png')
    img.save(path)
    return path


# ---------------------------------------------------------------------------
# Fixture 3: Buttons panel — BAD (color-only primary/secondary) vs GOOD
# ---------------------------------------------------------------------------
def make_button_panel_color_only():
    """Primary (green) and secondary (red) buttons — CVD confusing."""
    w, h = 400, 150
    img = Image.new('RGB', (w, h), BG_LIGHT)
    d = ImageDraw.Draw(img)

    d.rectangle([20, 30, 190, 80], fill=SUCCESS_GREEN)
    d.text((60, 47), 'CONFIRM', fill=(255,255,255))

    d.rectangle([210, 30, 380, 80], outline=ERROR_RED, width=2)
    d.text((240, 47), 'CANCEL', fill=ERROR_RED)

    d.rectangle([20, 100, 190, 130], fill=ERROR_RED)
    d.text((50, 107), 'DELETE', fill=(255,255,255))

    path = os.path.join(FIXTURE_DIR, 'button_panel_color_only.png')
    img.save(path)
    return path


def make_button_panel_accessible():
    """Same buttons with text labels and shape distinction."""
    w, h = 400, 150
    img = Image.new('RGB', (w, h), BG_LIGHT)
    d = ImageDraw.Draw(img)

    d.rectangle([20, 30, 190, 80], fill=CLEAN_BLUE)
    d.text((40, 47), '▶ CONFIRM', fill=(255,255,255))

    d.rectangle([210, 30, 380, 80], outline=CLEAN_GRAY, width=2)
    d.text((235, 47), '○ CANCEL', fill=CLEAN_GRAY)

    d.rectangle([20, 100, 190, 130], outline=(180, 30, 30), width=2)
    d.text((45, 107), '✗ DELETE', fill=(180,30,30))

    path = os.path.join(FIXTURE_DIR, 'button_panel_accessible.png')
    img.save(path)
    return path


# ---------------------------------------------------------------------------
# Generate CVD-simulated versions for each fixture
# ---------------------------------------------------------------------------
CVD_TYPES = ['deuteranopia', 'protanopia', 'tritanopia']


def generate_cvd_versions(original_path):
    """Generate CVD-simulated versions of a fixture."""
    img = Image.open(original_path)
    base = os.path.splitext(os.path.basename(original_path))[0]

    for cvd in CVD_TYPES:
        simulated = simulate_cvd(img, cvd_type=cvd)
        out_path = os.path.join(FIXTURE_DIR, f'{base}_{cvd}.png')
        simulated.save(out_path)
        print(f'  Generated: {out_path}')


def main():
    fixtures = [
        make_form_validation(),
        make_form_validation_accessible(),
        make_status_badges_color_only(),
        make_status_badges_accessible(),
        make_button_panel_color_only(),
        make_button_panel_accessible(),
    ]

    print(f'Generated {len(fixtures)} original fixtures')

    print('\nGenerating CVD-simulated versions...')
    for fp in fixtures:
        generate_cvd_versions(fp)

    print(f'\nAll fixtures in: {FIXTURE_DIR}')
    print('Run with: python tests/generate_fixtures.py')


if __name__ == '__main__':
    main()