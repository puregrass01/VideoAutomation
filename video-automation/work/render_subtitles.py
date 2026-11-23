"""Subtitle, logo, and guide-arrow hardsub renderer matching CapCut 「옵틱글래스 광각미러 템플릿 1」
and https://www.youtube.com/@optic_glass video & Shorts subtitle styles.

Uses bundled portable fonts (video-automation/assets/fonts/), Pillow RGBA layers cropped to tight
bounding boxes, and FFmpeg (NVENC with software fallback) so every exported .mp4 has crisp burned-in
subtitles and carries an `opticglass_subtitled_v2` metadata tag for verification.
"""
from __future__ import annotations

import hashlib
import math
import os
import pathlib
import random
import shutil
import tempfile
from collections import defaultdict

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from longform_common import FC_CENTER_ABOVE_Y, _enc_clip, run_ffmpeg
from portable_paths import ASSETS_DIR, OUTPUT_DIR, resolve_asset_path, to_fwd

RENDER_VERSION = "opticglass_subtitled_v2"
SUBTITLE_META_PREFIX = "opticglass_subtitled_v2"

_FONTS_DIR = ASSETS_DIR / "fonts"
_EMOJI_FONT = pathlib.Path(r"C:\Windows\Fonts\seguiemj.ttf")
_SHORTS_LOGO = ASSETS_DIR / "logos" / "옵틱글래스 로고.png"


def resolve_font_file(preset: str, row: dict | None = None) -> pathlib.Path:
    """Resolve the bundled portable font file for a subtitle style preset."""
    candidates_by_preset = {
        "title_translucent": ("NotoSansKR-Regular.otf", "NotoSansKR-Bold-Static.ttf", "Paperlogy-7Bold.ttf"),
        "card_sub": ("GalleryModern.otf", "NotoSansKR-Regular.otf", "Paperlogy-7Bold.ttf"),
        "card_title": ("BlackHanSans-Regular.ttf", "Paperlogy-9Black.ttf", "NotoSansKR-Bold-Static.ttf"),
        "box": ("Paperlogy-7Bold.ttf", "NotoSansKR-Bold-Static.ttf"),
        "shorts_hook": ("NotoSansKR-Bold-Static.ttf", "Paperlogy-7Bold.ttf"),
    }
    default_bold = ("NotoSansKR-Bold-Static.ttf", "Paperlogy-7Bold.ttf")
    names = candidates_by_preset.get(preset, default_bold)
    for name in names:
        p = _FONTS_DIR / name
        if p.exists():
            return p
        resolved = pathlib.Path(resolve_asset_path(p))
        if resolved.exists():
            return resolved
    return _FONTS_DIR / "Paperlogy-7Bold.ttf"


def _hex_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    h = (hex_color or "#FFFFFF").lstrip("#")
    if len(h) != 6:
        return (255, 255, 255, alpha)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def _load_font(path: pathlib.Path, size_px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), max(12, int(round(size_px))))


def _fit_font(path: pathlib.Path, text: str, size_px: int, max_w: int, stroke_w: int = 0) -> ImageFont.FreeTypeFont:
    sz = max(14, int(round(size_px)))
    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    while sz > 18:
        font = _load_font(path, sz)
        box = probe.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
        if (box[2] - box[0]) <= max_w:
            return font
        sz = max(18, int(sz * 0.93))
    return _load_font(path, sz)


def _preset_of(row: dict, preserve_template: bool) -> str:
    if row.get("style_preset"):
        return row["style_preset"]
    if not preserve_template:
        return "box" if row.get("box", True) else "split_caption"
    rid = row.get("id", "")
    if rid == "lt01":
        return "title_translucent"
    if rid == "w04a":
        return "card_sub"
    if rid == "w04b":
        return "card_title"
    if rid == "wb1":
        return "badge_before"
    if rid == "wb2":
        return "badge_after"
    if rid in ("wc1", "wc3"):
        return "glow_mono"
    if rid in ("wc2", "wc4"):
        return "glow_blue"
    if rid in ("wc5", "wc7"):
        return "glow_pink"
    if rid in ("wc6", "wc8"):
        return "glow_gold"
    if rid.startswith("ws"):
        return "split_label"
    if rid.startswith("wz"):
        return "split_caption"
    return "box" if row.get("box", False) else "split_caption"


def _draw_glow_text(
    canvas: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont,
    cx: float,
    cy: float,
    fill_rgba: tuple[int, int, int, int],
    outline_rgba: tuple[int, int, int, int],
    glow_rgba: tuple[int, int, int, int],
    stroke_w: int = 4,
    glow_radius: int = 9,
    glow_stroke: int = 8,
    sparkles: bool = False,
    seed_key: str = "",
) -> None:
    """Draw CapCut/@optic_glass style neon-outlined glowing Korean subtitle without any black box."""
    # 1. Soft dark readability shadow behind the glow
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sh_d = ImageDraw.Draw(sh)
    sh_d.text((cx + 2, cy + 4), text, font=font, fill=(0, 0, 0, 150), anchor="mm",
              stroke_width=stroke_w + 3, stroke_fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=6))
    canvas.alpha_composite(sh)

    # 2. Outer colored glow layer (2 passes for rich CapCut bloom feel)
    gl = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gl_d = ImageDraw.Draw(gl)
    gl_d.text((cx, cy), text, font=font, fill=glow_rgba, anchor="mm",
              stroke_width=glow_stroke, stroke_fill=glow_rgba)
    gl_soft = gl.filter(ImageFilter.GaussianBlur(radius=glow_radius))
    canvas.alpha_composite(gl_soft)
    gl_tight = gl.filter(ImageFilter.GaussianBlur(radius=max(2, glow_radius // 3)))
    canvas.alpha_composite(gl_tight)

    # 3. Crisp outline + main fill
    fg = ImageDraw.Draw(canvas)
    fg.text((cx, cy), text, font=font, fill=fill_rgba, anchor="mm",
            stroke_width=stroke_w, stroke_fill=outline_rgba)

    # 4. Subtle sparkle stars for ART EN PINK GLITTER (wc5 / wc7)
    if sparkles:
        bbox = fg.textbbox((cx, cy), text, font=font, anchor="mm", stroke_width=stroke_w)
        rng = random.Random(int(hashlib.md5(seed_key.encode("utf-8")).hexdigest()[:8], 16))
        sp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sp_d = ImageDraw.Draw(sp)
        for _ in range(10):
            sx = rng.randint(max(8, int(bbox[0]) - 14), min(canvas.width - 8, int(bbox[2]) + 14))
            sy = rng.randint(max(8, int(bbox[1]) - 10), min(canvas.height - 8, int(bbox[3]) + 10))
            arm = rng.randint(4, 9)
            sp_d.line([(sx - arm, sy), (sx + arm, sy)], fill=(255, 255, 255, 220), width=1)
            sp_d.line([(sx, sy - arm), (sx, sy + arm)], fill=(255, 255, 255, 220), width=1)
            sp_d.ellipse([(sx - 2, sy - 2), (sx + 2, sy + 2)], fill=(255, 235, 248, 240))
        canvas.alpha_composite(sp)


def _draw_stroked_text(
    canvas: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont,
    cx: float,
    cy: float,
    fill_rgba: tuple[int, int, int, int],
    stroke_w: int = 5,
    shadow_alpha: int = 165,
) -> None:
    if shadow_alpha > 0:
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text(
            (cx + 2, cy + 4), text, font=font, fill=(0, 0, 0, shadow_alpha), anchor="mm",
            stroke_width=max(2, stroke_w), stroke_fill=(0, 0, 0, shadow_alpha),
        )
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(radius=4)))
    ImageDraw.Draw(canvas).text(
        (cx, cy), text, font=font, fill=fill_rgba, anchor="mm",
        stroke_width=stroke_w, stroke_fill=(0, 0, 0, 255),
    )


def _draw_red_guide_arrow(canvas: Image.Image) -> None:
    """Draw the curved red guide arrow (matching CapCut Track[4] 'Guidance EN - Arrow' at (1566, 211))."""
    pts = []
    # Smooth quadratic Bezier from top-right (1642, 132) curving down-left to (1516, 256)
    p0, p1, p2 = (1642.0, 132.0), (1628.0, 228.0), (1516.0, 256.0)
    steps = 32
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    # Tangent at tip for clean V arrowhead
    dx, dy = pts[-1][0] - pts[-4][0], pts[-1][1] - pts[-4][1]
    ang = math.atan2(dy, dx)
    head_len = 34.0
    spread = 0.56
    h1 = (p2[0] - head_len * math.cos(ang - spread), p2[1] - head_len * math.sin(ang - spread))
    h2 = (p2[0] - head_len * math.cos(ang + spread), p2[1] - head_len * math.sin(ang + spread))

    # Subtle shadow + crisp red stroke
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sh_d = ImageDraw.Draw(sh)
    sh_pts = [(x + 2, y + 3) for x, y in pts]
    sh_d.line(sh_pts, fill=(0, 0, 0, 150), width=11, joint="curve")
    sh_d.line([(h1[0] + 2, h1[1] + 3), (p2[0] + 2, p2[1] + 3), (h2[0] + 2, h2[1] + 3)],
              fill=(0, 0, 0, 150), width=11, joint="curve")
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(radius=3)))

    d = ImageDraw.Draw(canvas)
    red = (232, 22, 22, 255)
    d.line(pts, fill=red, width=8, joint="curve")
    d.line([h1, p2, h2], fill=red, width=8, joint="curve")
    for x, y in (p0, p2, h1, h2):
        d.ellipse([(x - 4, y - 4), (x + 4, y + 4)], fill=red)


def _draw_line_on_canvas(canvas: Image.Image, row: dict, preserve_template: bool) -> None:
    preset = _preset_of(row, preserve_template)
    text = row["text"]
    size_px = int(round(row["size"]))
    cx = float(row["fc_pos"][0])
    cy = float(row["fc_pos"][1]) - FC_CENTER_ABOVE_Y * float(row["size"])
    max_w = 880 if preset == "split_label" else 1820
    font_path = resolve_font_file(preset, row)

    if preset == "title_translucent":
        font = _fit_font(font_path, text, size_px, max_w=1760)
        alpha = int(round(max(0.70, float(row.get("alpha", 0.72))) * 255))
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((cx + 2, cy + 3), text, font=font, fill=(0, 0, 0, 125), anchor="mm")
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(radius=4)))
        ImageDraw.Draw(canvas).text((cx, cy), text, font=font, fill=(255, 255, 255, alpha), anchor="mm")
        return

    if preset == "card_sub":
        font = _fit_font(font_path, text, size_px, max_w=1600)
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((cx + 2, cy + 3), text, font=font, fill=(0, 0, 0, 175), anchor="mm")
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(radius=4)))
        ImageDraw.Draw(canvas).text((cx, cy), text, font=font, fill=(255, 255, 255, 245), anchor="mm")
        return

    if preset == "card_title":
        font = _fit_font(font_path, text, size_px, max_w=1720)
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((cx + 3, cy + 5), text, font=font, fill=(0, 0, 0, 195), anchor="mm",
                                stroke_width=2, stroke_fill=(0, 0, 0, 170))
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(radius=5)))
        ImageDraw.Draw(canvas).text((cx, cy), text, font=font, fill=(255, 255, 255, 255), anchor="mm")
        return

    if preset == "badge_before":
        font = _fit_font(font_path, text, size_px, max_w=760, stroke_w=5)
        _draw_stroked_text(canvas, text, font, cx, cy, _hex_rgba(row.get("color", "#FFFFFF")), stroke_w=5)
        return

    if preset == "badge_after":
        font = _fit_font(font_path, text, size_px, max_w=760, stroke_w=5)
        _draw_stroked_text(canvas, text, font, cx, cy, (255, 232, 128, 255), stroke_w=5)
        return

    if preset == "glow_mono":
        font = _fit_font(font_path, text, size_px, max_w=max_w, stroke_w=4)
        _draw_glow_text(canvas, text, font, cx, cy,
                        fill_rgba=(250, 252, 255, 255),
                        outline_rgba=(36, 52, 72, 255),
                        glow_rgba=(82, 118, 158, 215),
                        stroke_w=4, glow_radius=8, glow_stroke=7)
        return

    if preset == "glow_blue":
        font = _fit_font(font_path, text, size_px, max_w=max_w, stroke_w=4)
        _draw_glow_text(canvas, text, font, cx, cy,
                        fill_rgba=(255, 255, 255, 255),
                        outline_rgba=(26, 130, 228, 255),
                        glow_rgba=(56, 182, 255, 235),
                        stroke_w=4, glow_radius=10, glow_stroke=8)
        return

    if preset == "glow_pink":
        font = _fit_font(font_path, text, size_px, max_w=max_w, stroke_w=4)
        _draw_glow_text(canvas, text, font, cx, cy,
                        fill_rgba=(255, 245, 252, 255),
                        outline_rgba=(225, 38, 136, 255),
                        glow_rgba=(255, 72, 166, 235),
                        stroke_w=4, glow_radius=10, glow_stroke=8,
                        sparkles=True, seed_key=f"{row.get('id','')}:{text}")
        return

    if preset == "glow_gold":
        font = _fit_font(font_path, text, size_px, max_w=max_w, stroke_w=4)
        _draw_glow_text(canvas, text, font, cx, cy,
                        fill_rgba=(255, 244, 198, 255),
                        outline_rgba=(192, 110, 0, 255),
                        glow_rgba=(255, 178, 20, 230),
                        stroke_w=4, glow_radius=9, glow_stroke=8)
        return

    if preset in ("split_label", "split_caption"):
        sw = 5 if preset == "split_label" else 4
        font = _fit_font(font_path, text, size_px, max_w=max_w, stroke_w=sw)
        _draw_stroked_text(canvas, text, font, cx, cy, _hex_rgba(row.get("color", "#FFFFFF")), stroke_w=sw)
        return

    # Legacy R3 hand-made 80s box style (opaque black rounded box, no outline)
    font = _fit_font(font_path, text, size_px, max_w=1780)
    d = ImageDraw.Draw(canvas)
    bbox = d.textbbox((cx, cy), text, font=font, anchor="mm")
    pad_x, pad_y = 24, 14
    rect = (bbox[0] - pad_x, bbox[1] - pad_y, bbox[2] + pad_x, bbox[3] + pad_y)
    d.rounded_rectangle(rect, radius=14, fill=(0, 0, 0, 255))
    d.text((cx, cy), text, font=font, fill=_hex_rgba(row.get("color", "#FFFFFF")), anchor="mm")


def _paste_brand_logo(canvas: Image.Image, car) -> None:
    logo_p = car.logo_shadow if car.logo_shadow.exists() else car.logo
    if not logo_p or not logo_p.exists():
        return
    logo = Image.open(logo_p).convert("RGBA")
    # Match CapCut logo placement above lt01 (transform_y=+0.28 -> y=389) without touching lt01 (y≈540)
    target_h = 150
    ratio = target_h / max(1, logo.height)
    new_w = max(1, int(round(logo.width * ratio)))
    logo = logo.resize((new_w, target_h), Image.Resampling.LANCZOS)
    x0 = (canvas.width - new_w) // 2
    y0 = max(40, 389 - target_h // 2)
    canvas.alpha_composite(logo, (x0, y0))


def render_longform_mp4(car, prepared: list, part_mp4: pathlib.Path, dur_s: float) -> None:
    """Render a full 1920x1080@30fps MP4 with all scenario subtitles, brand logo, guide arrows, and BGM burned in."""
    if not car.lines:
        raise ValueError(f"{car.slug}: car.lines is empty — refusing to render a subtitle-less video")
    preserve_template = bool(car.tpl.get("preserve_template_style"))
    keep_stickers = bool(car.tpl.get("keep_stickers"))

    # Group overlays by identical (start, end) time span so fewer FFmpeg overlay nodes run per frame
    span_rows: dict[tuple[float, float], list[dict]] = defaultdict(list)
    for row in car.lines:
        t0 = round(float(row["start"]), 3)
        t1 = round(float(row["start"]) + float(row["dur"]), 3)
        span_rows[(t0, t1)].append(row)

    with tempfile.TemporaryDirectory(prefix=f"og_sub_{car.slug}_") as tmp_s:
        tmp = pathlib.Path(tmp_s)
        concat_txt = tmp / "concat.txt"
        concat_txt.write_text(
            "".join("file '" + to_fwd(c["path"].resolve()).replace("'", r"'\''") + "'\n" for c in prepared),
            encoding="utf-8",
        )

        overlays: list[tuple[pathlib.Path, int, int, float, float]] = []
        for idx, ((t0, t1), rows) in enumerate(sorted(span_rows.items())):
            canvas = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
            for row in rows:
                _draw_line_on_canvas(canvas, row, preserve_template)
                if row.get("id") == "lt01":
                    _paste_brand_logo(canvas, car)
                if keep_stickers and row.get("id") in ("wb1", "wb2"):
                    _draw_red_guide_arrow(canvas)
            bbox = canvas.getbbox()
            if not bbox:
                continue
            cropped = canvas.crop(bbox)
            png_p = tmp / f"ov_{idx:02d}.png"
            cropped.save(png_p, optimize=False)
            overlays.append((png_p, bbox[0], bbox[1], t0, t1))

        if not overlays:
            raise RuntimeError(f"{car.slug}: no visible subtitle overlays rendered")

        cmd = ["-f", "concat", "-safe", "0", "-i", str(concat_txt), "-i", str(car.bgm)]
        for png_p, *_ in overlays:
            cmd.extend(["-loop", "1", "-framerate", "2", "-i", str(png_p)])

        filters = ["[0:v]fps=30,format=yuv420p[v0]"]
        prev = "v0"
        for i, (_, ox, oy, t0, t1) in enumerate(overlays):
            inp = i + 2
            nxt = f"v{i + 1}"
            filters.append(f"[{prev}][{inp}:v]overlay=x={ox}:y={oy}:shortest=1:enable='between(t,{t0:.3f},{t1:.3f})'[{nxt}]")
            prev = nxt

        meta_comment = f"{SUBTITLE_META_PREFIX}:{'wide1' if preserve_template else 'legacy'}:{len(car.lines)}"
        cmd.extend([
            "-filter_complex", ";".join(filters),
            "-map", f"[{prev}]",
            "-map", "1:a",
            *_enc_clip(), "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-metadata", f"comment={meta_comment}",
            "-t", f"{dur_s:.3f}",
            str(part_mp4),
        ])
        run_ffmpeg(cmd)


def sync_longform_output(car) -> pathlib.Path:
    """Copy the subtitled longform/wide1 MP4 to output/<slug>/<slug>_optic_<variant>.mp4."""
    out_dir = OUTPUT_DIR / car.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"{car.slug}_optic_{car.variant}.mp4"
    tmp = dst.with_name(f".{dst.name}.{os.getpid()}.tmp")
    shutil.copy2(car.preview_mp4, tmp)
    os.replace(tmp, dst)
    return dst


# --- Shorts 9:16 renderer (@optic_glass/shorts style) --------------------------------------------------------------
def _is_emoji_char(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x1F300 <= cp <= 0x1FAFF
        or 0x2600 <= cp <= 0x27BF
        or cp in (0xFE0F, 0x200D)
    )


def _split_emoji_runs(line: str) -> list[tuple[str, bool]]:
    runs: list[tuple[str, bool]] = []
    buf = ""
    cur_emoji = None
    for ch in line:
        em = _is_emoji_char(ch)
        if cur_emoji is None:
            cur_emoji = em
            buf = ch
        elif em == cur_emoji:
            buf += ch
        else:
            runs.append((buf, cur_emoji))
            buf = ch
            cur_emoji = em
    if buf:
        runs.append((buf, bool(cur_emoji)))
    return runs


def _measure_runs(draw: ImageDraw.ImageDraw, runs: list[tuple[str, bool]],
                  text_font: ImageFont.FreeTypeFont, emoji_font: ImageFont.FreeTypeFont | None) -> tuple[int, int]:
    total_w = 0
    max_h = 0
    for seg, is_em in runs:
        f = emoji_font if (is_em and emoji_font is not None) else text_font
        box = draw.textbbox((0, 0), seg, font=f)
        total_w += max(0, box[2] - box[0]) + (4 if is_em else 0)
        max_h = max(max_h, box[3] - box[1])
    return total_w, max_h


def _render_shorts_overlay(hook_lines: list[str], logo_path: pathlib.Path) -> Image.Image:
    """Create a 1080x1920 RGBA overlay matching @optic_glass/shorts:
    pure crisp bold white 2-line hook centered in the top black band + Optic-Glass logo in the bottom black band."""
    canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = resolve_font_file("shorts_hook")
    has_emoji_font = _EMOJI_FONT.exists()

    # Fit font size so both lines stay comfortably inside 960px width (matches @optic_glass/shorts ~72-82px bold)
    sz = 78
    while sz > 36:
        tf = _load_font(font_path, sz)
        ef = _load_font(_EMOJI_FONT, sz) if has_emoji_font else None
        widths = [_measure_runs(draw, _split_emoji_runs(ln), tf, ef)[0] for ln in hook_lines]
        if max(widths, default=0) <= 960:
            break
        sz = max(36, int(sz * 0.92))
    tf = _load_font(font_path, sz)
    ef = _load_font(_EMOJI_FONT, sz) if has_emoji_font else None

    line_gap = int(round(sz * 1.36))
    center_y = 328  # matches CapCut shorts transform_y = +0.658 -> 960 * (1 - 0.658) = 328
    start_y = center_y - ((len(hook_lines) - 1) * line_gap) // 2

    for i, ln in enumerate(hook_lines):
        runs = _split_emoji_runs(ln)
        total_w, _ = _measure_runs(draw, runs, tf, ef)
        x = (1080 - total_w) / 2.0
        y = start_y + i * line_gap
        for seg, is_em in runs:
            if is_em and ef is not None:
                box = draw.textbbox((0, 0), seg, font=ef)
                seg_w = max(0, box[2] - box[0])
                draw.text((x, y), seg, font=ef, fill=(255, 255, 255, 255), anchor="lm", embedded_color=True)
                x += seg_w + 4
            else:
                box = draw.textbbox((0, 0), seg, font=tf)
                seg_w = max(0, box[2] - box[0])
                draw.text((x, y), seg, font=tf, fill=(255, 255, 255, 255), anchor="lm")
                x += seg_w

    # Bottom Optic-Glass logo centered at y=1592 (matches transform_y = -0.658 -> 960 * 1.658 = 1592)
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        target_w = 720
        ratio = target_w / max(1, logo.width)
        new_h = max(1, int(round(logo.height * ratio)))
        logo = logo.resize((target_w, new_h), Image.Resampling.LANCZOS)
        canvas.alpha_composite(logo, ((1080 - target_w) // 2, 1592 - new_h // 2))

    return canvas


def short_mp4_name(idx: int, slug: str, chapter: str) -> str:
    safe_ch = chapter.replace(" ", "")
    return f"{idx:02d}_{slug}_{safe_ch}.mp4"


def render_shorts_mp4s(car, source: pathlib.Path, parts: list, hook: dict,
                       out_dir: pathlib.Path | None = None) -> list[pathlib.Path]:
    """Render all 5 subtitled 1080x1920 Shorts MP4s into output/<slug>/shorts/."""
    dest_dir = out_dir or (OUTPUT_DIR / car.slug / "shorts")
    dest_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[pathlib.Path] = []
    with tempfile.TemporaryDirectory(prefix=f"og_shorts_{car.slug}_") as tmp_s:
        tmp = pathlib.Path(tmp_s)
        for idx, (chapter, start_s, dur_s) in enumerate(parts, start=1):
            lines = hook.get(chapter)
            if not lines or not any(str(x).strip() for x in lines):
                raise ValueError(f"{car.slug} shorts '{chapter}': missing hook subtitle lines")
            ov = _render_shorts_overlay(lines, _SHORTS_LOGO)
            ov_png = tmp / f"short_{idx:02d}.png"
            ov.save(ov_png, optimize=False)
            out_mp4 = dest_dir / short_mp4_name(idx, car.slug, chapter)
            part_mp4 = dest_dir / f".{out_mp4.stem}.{os.getpid()}.part.mp4"
            meta_comment = f"{SUBTITLE_META_PREFIX}:shorts:{chapter}"
            try:
                run_ffmpeg([
                    "-ss", f"{start_s:.3f}", "-t", f"{dur_s:.3f}", "-i", str(source),
                    "-i", str(ov_png),
                    "-filter_complex",
                    "[0:v]scale=1080:608:force_original_aspect_ratio=decrease,"
                    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,fps=30,setsar=1[bg];"
                    "[bg][1:v]overlay=0:0[outv]",
                    "-map", "[outv]", "-map", "0:a",
                    *_enc_clip(), "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    "-metadata", f"comment={meta_comment}",
                    str(part_mp4),
                ])
                os.replace(part_mp4, out_mp4)
            finally:
                part_mp4.unlink(missing_ok=True)
            outputs.append(out_mp4)
    return outputs
