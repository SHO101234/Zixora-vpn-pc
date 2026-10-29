"""zixora VPN for Windows — brand constants and logo handling.

Brand palette ONLY (no gold):
  navy #091f5b, primary #334dae, mid #6f96d1,
  light #d0e4fd, glass #e8f2fe, white #fafbff

Logo rule: the user's original Z mark, exactly as-is, never redrawn,
never resized non-uniformly. The clean asset is 448x250 (non-square);
fit_logo() scales it to fit a box while PRESERVING aspect ratio and
centres it, with letterbox padding if needed. Never force it square.
"""

NAVY = "#091f5b"
PRIMARY = "#334dae"
MID = "#6f96d1"
LIGHT = "#d0e4fd"
GLASS = "#e8f2fe"
WHITE = "#fafbff"

LOGO_PATH = "assets/z_logo_clean.png"
LOGO_NATIVE_W = 448
LOGO_NATIVE_H = 250


def fit_logo(box_w: int, box_h: int) -> tuple:
    """Return (width, height) for the logo inside box_w x box_h,
    preserving aspect ratio. Never stretches."""
    if box_w <= 0 or box_h <= 0:
        return (LOGO_NATIVE_W, LOG_NATIVE_H)
    scale = min(box_w / LOGO_NATIVE_W, box_h / LOGO_NATIVE_H)
    return (max(1, int(LOGO_NATIVE_W * scale)),
            max(1, int(LOGO_NATIVE_H * scale)))
