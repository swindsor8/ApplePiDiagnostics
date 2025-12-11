"""Generate PNG icon files (256x256, 128x128, 48x48) from project logo.

Usage:
    python3 scripts/generate_icons.py --outdir=assets/icons

By default it will try to reuse the project's logo discovery at
`full-linux-gui/app/gui/splash.py` (the `LOGO_PATH` value). Requires Pillow.
"""
from pathlib import Path
import argparse
import sys

# Try to import the project's logo discovery
try:
    # adjust import path if running from repo root
    from full_linux_gui_app_gui_splash_import_helper import _importable
except Exception:
    pass

try:
    from gui.splash import LOGO_PATH
except Exception:
    LOGO_PATH = None


def find_logo():
    if LOGO_PATH:
        p = Path(LOGO_PATH)
        if p.exists():
            return p
    # fallback: look for top-level assets/apple_pi_logo.*
    root = Path(__file__).resolve().parents[1]
    for ext in ("png", "ppm", "jpg", "jpeg"):
        candidate = root / "assets" / f"apple_pi_logo.{ext}"
        if candidate.exists():
            return candidate
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="assets/icons", help="Output directory for icons")
    args = parser.parse_args()

    logo = find_logo()
    if not logo:
        print("No logo found in repo (looked for gui.splash.LOGO_PATH and assets/apple_pi_logo.*).", file=sys.stderr)
        sys.exit(2)

    try:
        from PIL import Image
    except Exception as e:
        print("Pillow is required to run this script. Install with: pip install Pillow", file=sys.stderr)
        sys.exit(2)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    sizes = [(256, "apple_pi_256.png"), (128, "apple_pi_128.png"), (48, "apple_pi_48.png")]
    img = Image.open(str(logo)).convert("RGBA")
    for size, name in sizes:
        out = outdir / name
        resized = img.copy()
        resized.thumbnail((size, size), Image.LANCZOS)
        # create a square canvas and paste centered
        canvas_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        w, h = resized.size
        canvas_img.paste(resized, ((size - w) // 2, (size - h) // 2), resized)
        canvas_img.save(out)
        print("Wrote", out)

    print("Icons generated in:", outdir)


if __name__ == "__main__":
    main()
