"""Thumbnails: frame extract + branded text overlay + contrast safety check.

`make()` extracts a frame, overlays title text in brand colors, and verifies
the text region has enough contrast to be readable at small sizes.
"""

import os

from video import ffmpeg as vff
from editor import motion as motion_mod

try:
    from PIL import Image, ImageDraw, ImageFont, ImageStat
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


def _luminance(rgb):
    r, g, b = [c / 255 for c in rgb[:3]]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ok(bg_rgb, fg_rgb=(255, 255, 255), min_ratio=3.0):
    """WCAG-style contrast ratio check for thumbnail text legibility."""
    l1, l2 = _luminance(bg_rgb), _luminance(fg_rgb)
    ratio = (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)
    return ratio >= min_ratio, round(ratio, 2)


def make(input_video, output, at=3.0, text="", brand=None,
         width=1280, height=720, dry_run=False):
    """Build a thumbnail: best frame near `at` + title text + brand accent.

    brand: {"colors": {"bg","fg","accent"}} tuples. Returns {"path", "contrast"}.
    """
    if not HAVE_PIL:
        raise RuntimeError("PIL is required for thumbnails (pip install pillow)")
    tmp = output + ".frame.png"
    argv = vff.build_frame(input_video, tmp, at=at, strict=not dry_run)
    vff.run_cmd(argv, dry_run=dry_run)
    if dry_run:
        return {"path": output, "contrast": None, "dry_run": True}
    img = Image.open(tmp).convert("RGB")
    img = img.resize((width, height))
    d = ImageDraw.Draw(img)
    colors = (brand or {}).get("colors", {})
    fg = tuple(colors.get("fg", (255, 255, 255)))
    accent = tuple(colors.get("accent", (255, 140, 40)))
    if text:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 110)
        except OSError:
            font = ImageFont.load_default()
        # word wrap to <= 3 words per line style (thumbnail rule: <= 3 words)
        words = text.split()
        lines, cur = [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if d.textlength(trial, font=font) > width - 120:
                lines.append(cur); cur = w
            else:
                cur = trial
        lines.append(cur)
        # sample background luminance behind the text block
        band = img.crop((0, height - (len(lines) * 130) - 160, width, height))
        bg_avg = tuple(int(v) for v in ImageStat.Stat(band).mean)
        ok, ratio = contrast_ok(bg_avg, fg)
        if not ok:
            # scrim: darken the text band for legibility
            scrim = Image.new("RGB", (width, (len(lines) * 130) + 120), (0, 0, 0))
            img.paste(scrim, (0, height - scrim.height))
            bg_avg = (0, 0, 0)
            ok, ratio = contrast_ok(bg_avg, fg)
        y = height - (len(lines) * 130) - 80
        for ln in lines:
            d.text((60, y), ln.upper(), font=font, fill=fg,
                   stroke_width=4, stroke_fill=(0, 0, 0))
            y += 130
        d.rectangle([60, y + 10, 260, y + 26], fill=accent)
    else:
        ok, ratio = True, None
    img.save(output)
    os.remove(tmp)
    return {"path": output, "contrast": {"ok": ok, "ratio": ratio}}
