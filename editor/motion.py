"""Motion graphics builders: lower thirds, progress bars, timers, subscribe
overlays, intro/outro sequences — rendered with PIL (available) composited
via ffmpeg, so everything is reproducible without a GUI.

Emoji/caption animation for short-form is handled via the subtitles karaoke
ASS path (editor/subtitles.py); these builders cover persistent graphic
elements and branded open/close cards.
"""

import json
import os

from video import ffmpeg as vff

try:
    from PIL import Image, ImageDraw, ImageFont
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


def _font(size):
    if not HAVE_PIL:
        raise RuntimeError("PIL is required for motion graphics (pip install pillow)")
    for cand in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(cand, size)
        except OSError:
            continue
    return ImageFont.load_default()


def lower_third(text, subtext="", output="lower_third.png", width=1080,
                height=220, bg=(10, 14, 18, 200), accent=(255, 140, 40, 255),
                fg=(255, 255, 255, 255)):
    """Render a lower-third PNG with accent bar."""
    _font(10)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, width - 1, height - 1], radius=28, fill=bg)
    d.rectangle([0, 0, 14, height], fill=accent)
    f1, f2 = _font(56), _font(38)
    d.text((48, 34), text, font=f1, fill=fg)
    if subtext:
        d.text((50, 112), subtext, font=f2, fill=(200, 210, 215, 255))
    img.save(output)
    return output


def progress_bar(output="progress.png", width=1080, height=24,
                bg=(30, 34, 38, 180), fg=(255, 140, 40, 255)):
    """Static bar shell; animate fill with ffmpeg crop+overlay over time."""
    _font(10)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, width - 1, height - 1], radius=12, fill=bg)
    img.save(output)
    # ffmpeg expression to reveal the bar left->right over the video duration:
    expr = (f"drawbox=x=0:y=H-{height + 40}:w=W*t/DURATION:h={height}:"
            f"c=0xFF8C28:t=fill")
    return output, expr


def text_card(text, output="card.png", width=1080, height=1920,
              bg=(8, 12, 16, 255), fg=(255, 255, 255, 255),
              accent=(45, 200, 190, 255)):
    """Full-screen title card (intro/outro base)."""
    _font(10)
    img = Image.new("RGBA", (width, height), bg)
    d = ImageDraw.Draw(img)
    f = _font(96)
    # simple word-wrap
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f) > width - 160:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    y = height // 2 - len(lines) * 70
    for ln in lines:
        tw = d.textlength(ln, font=f)
        d.text(((width - tw) / 2, y), ln, font=f, fill=fg)
        y += 140
    d.rectangle([width // 2 - 120, y + 20, width // 2 + 120, y + 30], fill=accent)
    img.save(output)
    return output


def intro_outro(brand, out_dir, style="card"):
    """Generate intro.mp4 + outro.mp4 from a brand kit dict.

    brand: {"name", "tagline", "colors": {"bg": (r,g,b), "fg":..., "accent":...},
            "intro_text", "outro_text", "duration": 2.5}
    """
    os.makedirs(out_dir, exist_ok=True)
    colors = brand.get("colors", {})
    bg = tuple(colors.get("bg", (8, 12, 16))) + (255,)
    fg = tuple(colors.get("fg", (255, 255, 255))) + (255,)
    accent = tuple(colors.get("accent", (45, 200, 190))) + (255,)
    dur = float(brand.get("duration", 2.5))
    intro_png = os.path.join(out_dir, "intro_card.png")
    outro_png = os.path.join(out_dir, "outro_card.png")
    text_card(brand.get("intro_text", brand.get("name", "Intro")),
              intro_png, bg=bg, fg=fg, accent=accent)
    text_card(brand.get("outro_text", "Thanks for watching"),
              outro_png, bg=bg, fg=fg, accent=accent)
    outs = {}
    for name, png in (("intro", intro_png), ("outro", outro_png)):
        mp4 = os.path.join(out_dir, f"{name}.mp4")
        # still -> video with a slow zoompan (Ken Burns) for motion feel
        argv = [vff.FFMPEG, "-y", "-loop", "1", "-i", png,
                "-vf", f"zoompan=z='min(zoom+0.0015,1.15)':d={int(dur*30)}:"
                       f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,"
                       "format=yuv420p",
                "-t", str(dur), "-c:v", "libx264", "-preset", "fast",
                "-crf", "19", mp4]
        outs[name] = {"png": png, "mp4": mp4, "argv": argv}
    return outs


def overlay_filter(png_path, at, duration, x="(W-w)/2", y="H-h-160"):
    """ffmpeg overlay snippet for stamping a graphic during [at, at+duration)."""
    return (f"overlay=x='{x}':y='{y}':"
            f"enable='between(t,{at},{at + duration})'")


def animated_caption_emoji(text, emoji="🔥"):
    """Caption text with emoji bookends, safe for drawtext/subtitles."""
    t = text.strip()
    return f"{emoji} {t} {emoji}" if t else t
