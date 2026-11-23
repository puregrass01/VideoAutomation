import argparse
import json
import pathlib
from typing import Dict, Any, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TEMPLATE_DIR = pathlib.Path(__file__).resolve().parent
THUMBNAIL_ROOT_DIR = TEMPLATE_DIR.parent
REPO_ROOT_DIR = THUMBNAIL_ROOT_DIR.parent
BUNDLED_FONTS_DIR = REPO_ROOT_DIR / "video-automation" / "assets" / "fonts"
USER_FONTS_DIR = pathlib.Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts"
CATALOG_PATH = TEMPLATE_DIR / "catalog_0002_0043.json"

FONT_CANDIDATES_DISPLAY = [
    str(USER_FONTS_DIR / "Paperlogy-9Black.ttf"),
    str(BUNDLED_FONTS_DIR / "Paperlogy-9Black.ttf"),
    str(USER_FONTS_DIR / "GmarketSansTTFBold.ttf"),
    str(USER_FONTS_DIR / "강원교육튼튼.ttf"),
    str(BUNDLED_FONTS_DIR / "강원교육튼튼.ttf"),
    str(USER_FONTS_DIR / "Pretendard-Black.ttf"),
    str(USER_FONTS_DIR / "NotoSansKR-Bold-Static.ttf"),
    str(BUNDLED_FONTS_DIR / "NotoSansKR-Bold-Static.ttf"),
    r"C:\Windows\Fonts\malgunbd.ttf",
]

FONT_CANDIDATES_UI = [
    str(USER_FONTS_DIR / "Pretendard-ExtraBold.otf"),
    str(USER_FONTS_DIR / "Paperlogy-7Bold.ttf"),
    str(BUNDLED_FONTS_DIR / "Paperlogy-7Bold.ttf"),
    str(USER_FONTS_DIR / "NotoSansKR-Bold-Static.ttf"),
    str(BUNDLED_FONTS_DIR / "NotoSansKR-Bold-Static.ttf"),
    r"C:\Windows\Fonts\malgunbd.ttf",
]


def get_font(size: int, display: bool = True) -> ImageFont.FreeTypeFont:
    candidates = FONT_CANDIDATES_DISPLAY if display else FONT_CANDIDATES_UI
    for path in candidates:
        if pathlib.Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def resize_cover(im: Image.Image, target_w: int, target_h: int, align_x: float = 0.5, align_y: float = 0.5) -> Image.Image:
    im = im.convert("RGB")
    scale = max(target_w / im.width, target_h / im.height)
    nw, nh = max(1, int(round(im.width * scale))), max(1, int(round(im.height * scale)))
    resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = int(round((nw - target_w) * align_x))
    top = int(round((nh - target_h) * align_y))
    return resized.crop((left, top, left + target_w, top + target_h))


def render_slanted_gradient_text(
    text: str,
    font_size: int,
    top_color: Tuple[int, int, int],
    bottom_color: Tuple[int, int, int],
    stroke_width: int = 8,
    stroke_color: Tuple[int, int, int] = (0, 0, 0),
    shear: float = 0.16,
    shadow_offset: Tuple[int, int] = (4, 6),
) -> Image.Image:
    """
    Renders crisp Korean display typography (zero blur):
    - Vertical metallic/gold gradient fill
    - Thick black outer stroke
    - Crisp hard drop shadow (no GaussianBlur)
    - Slight italic/forward slant (affine shear)
    """
    font = get_font(font_size, display=True)
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    d_dummy = ImageDraw.Draw(dummy)
    bbox = d_dummy.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad = stroke_width * 2 + 20
    w, h = tw + pad * 2, th + pad * 2

    txt_mask = Image.new("L", (w, h), 0)
    d_mask = ImageDraw.Draw(txt_mask)
    ox, oy = pad - bbox[0], pad - bbox[1]
    d_mask.text((ox, oy), text, font=font, fill=255)

    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d_grad = ImageDraw.Draw(grad)
    y_top = pad
    y_bot = pad + th
    span = max(1, y_bot - y_top)
    for y in range(h):
        t = min(1.0, max(0.0, (y - y_top) / span))
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        d_grad.line([(0, y), (w, y)], fill=(r, g, b, 255))

    filled_txt = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    filled_txt.paste(grad, (0, 0), mask=txt_mask)

    st_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d_st = ImageDraw.Draw(st_layer)
    d_st.text(
        (ox, oy),
        text,
        font=font,
        fill=(*stroke_color, 255),
        stroke_width=stroke_width,
        stroke_fill=(*stroke_color, 255),
    )

    base_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow_offset != (0, 0):
        sh_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d_sh = ImageDraw.Draw(sh_layer)
        d_sh.text(
            (ox + shadow_offset[0], oy + shadow_offset[1]),
            text,
            font=font,
            fill=(0, 0, 0, 230),
            stroke_width=stroke_width + 2,
            stroke_fill=(0, 0, 0, 230),
        )
        base_layer = Image.alpha_composite(base_layer, sh_layer)
    if stroke_width > 0:
        base_layer = Image.alpha_composite(base_layer, st_layer)
    base_layer = Image.alpha_composite(base_layer, filled_txt)

    if abs(shear) > 0.001:
        extra_w = int(abs(shear) * h) + 12
        transform_args = (
            (w + extra_w, h),
            Image.Transform.AFFINE,
            (1.0, shear, -shear * h * 0.65, 0.0, 1.0, 0.0),
        )
        sheared = base_layer.transform(*transform_args, resample=Image.Resampling.BICUBIC)
        sheared_st = st_layer.transform(*transform_args, resample=Image.Resampling.NEAREST)
    else:
        sheared = base_layer
        sheared_st = st_layer

    core_bbox = sheared_st.getbbox()
    if core_bbox:
        cx0 = max(0, core_bbox[0] - 6)
        cy0 = max(0, core_bbox[1] - 4)
        cx1 = min(sheared.width, core_bbox[2] + 10)
        cy1 = min(sheared.height, core_bbox[3] + 8)
        sheared = sheared.crop((cx0, cy0, cx1, cy1))
    return sheared


def draw_center_transition_arrow(
    canvas: Image.Image,
    cx: int,
    cy: int,
    accent_rgb: Tuple[int, int, int] = (255, 215, 0),
):
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    pts = [
        (cx - 32, cy - 16),
        (cx + 2, cy - 16),
        (cx + 2, cy - 34),
        (cx + 38, cy),
        (cx + 2, cy + 34),
        (cx + 2, cy + 16),
        (cx - 32, cy + 16),
    ]
    sh_pts = [(x + 3, y + 4) for x, y in pts]
    draw.polygon(sh_pts, fill=(0, 0, 0, 200))
    draw.polygon(pts, fill=(*accent_rgb, 255), outline=(0, 0, 0, 235), width=3)

    canvas.alpha_composite(overlay)


def draw_opticglass_logo(
    canvas: Image.Image,
    x: int,
    y: int,
    logo_height: int = 40,
):
    """
    Composites the official transparent PNG logo (`옵틱글래스 로고.png`), which contains
    both the orange-red crescent+dot symbol and the white 'Optic-Glass' wordmark.
    Bare logo without a pill box, zero blur.
    """
    logo_candidates = [
        THUMBNAIL_ROOT_DIR / "옵틱글래스 로고.png",
        TEMPLATE_DIR / "옵틱글래스 로고.png",
    ]
    logo_im: Optional[Image.Image] = None
    for cand in logo_candidates:
        if cand.exists():
            raw_logo = Image.open(cand).convert("RGBA")
            bbox = raw_logo.getbbox()
            if bbox:
                raw_logo = raw_logo.crop(bbox)
            scale = logo_height / max(1, raw_logo.height)
            target_w = max(1, int(round(raw_logo.width * scale)))
            logo_im = raw_logo.resize((target_w, logo_height), Image.Resampling.LANCZOS)
            break

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    if logo_im is not None:
        alpha = logo_im.getchannel("A")
        shadow = Image.new("RGBA", logo_im.size, (0, 0, 0, 235))
        shadow.putalpha(alpha)
        overlay.alpha_composite(shadow, (x + 2, y + 2))
        overlay.alpha_composite(logo_im, (x, y))

    canvas.alpha_composite(overlay)


def render_split_horizontal(
    canvas: Image.Image,
    before_im: Image.Image,
    after_im: Image.Image,
    entry: Dict[str, Any],
):
    """
    Renders a sharp split-horizontal comparison thumbnail following the `수정` template:
    - Only big 2-line headline ({car name} + 광각미러 차이!)
    - Clean `시공 전` / `시공 후` comparison cards on the right (~70:30 balance so hero car is unobstructed)
    - Zero tooltip text (no badges, no bottom slogans, no 3-icon bars, no captions)
    - Zero blurs and zero unfit outlines
    - Bare official `옵틱글래스 로고.png` at bottom-left
    """
    accent_rgb = hex_to_rgb(entry.get("accent_color", "#FFD400"))
    sub_style = entry.get("sub_style", "audi_q3_0031")

    line1 = entry.get("headline_line1", entry.get("vehicle_ko", "2025 아우디 Q3"))
    line2 = entry.get("headline_line2", "광각미러 차이!")

    if sub_style == "benz_sl500_0029":
        im_l1 = render_slanted_gradient_text(line1, 82, (255, 255, 255), (210, 220, 235), stroke_width=10, shear=0.14)
        im_l2 = render_slanted_gradient_text(line2, 82, (255, 245, 110), accent_rgb, stroke_width=10, shear=0.14)
        total_w = im_l1.width + 24 + im_l2.width
        sx = max(28, (1280 - total_w) // 2)
        canvas.alpha_composite(im_l1, (sx, 36))
        canvas.alpha_composite(im_l2, (sx + im_l1.width + 24, 36))
    else:
        l1_size = 70 if len(line1) <= 10 else 58
        l2_size = 90 if len(line2) <= 9 else 76
        im_l1 = render_slanted_gradient_text(line1, l1_size, (255, 255, 255), (205, 215, 230), stroke_width=9, shear=0.15)
        im_l2 = render_slanted_gradient_text(line2, l2_size, (255, 248, 120), accent_rgb, stroke_width=11, shear=0.15)
        y1 = 26
        y2 = y1 + im_l1.height + 2
        canvas.alpha_composite(im_l1, (32, y1))
        canvas.alpha_composite(im_l2, (28, y2))

    # Maintain ~70:30 visual balance so left hero vehicle is completely visible
    c_y0, c_y1 = 246, 616
    c1_x0, c1_x1 = 736, 996
    c2_x0, c2_x1 = 1008, 1268

    c1_w, c1_h = c1_x1 - c1_x0, c_y1 - c_y0
    c2_w, c2_h = c2_x1 - c2_x0, c_y1 - c_y0

    is_cybertruck = "사이버트럭" in line1 or "cybertruck" in line1.lower()
    if is_cybertruck and before_im.width > before_im.height:
        bw0, bh0 = before_im.size
        aw0, ah0 = after_im.size
        before_im = before_im.crop((int(bw0 * 0.14), int(bh0 * 0.02), int(bw0 * 0.88), int(bh0 * 0.88)))
        after_im = after_im.crop((int(aw0 * 0.14), int(ah0 * 0.02), int(aw0 * 0.88), int(ah0 * 0.88)))

    bef_crop = resize_cover(before_im, c1_w, c1_h).convert("RGBA")
    aft_crop = resize_cover(after_im, c2_w, c2_h).convert("RGBA")

    for (x0, y0, w, h, card_img, is_after) in (
        (c1_x0, c_y0, c1_w, c1_h, bef_crop, False),
        (c2_x0, c_y0, c2_w, c2_h, aft_crop, True),
    ):
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=16, fill=255)
        canvas.paste(card_img, (x0, y0), mask=mask)

        b_ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        d_b = ImageDraw.Draw(b_ov)
        if is_after:
            d_b.rounded_rectangle([x0 - 2, y0 - 2, x0 + w + 2, y0 + h + 2], radius=18, outline=(*accent_rgb, 255), width=4)
        else:
            d_b.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=16, outline=(215, 220, 230, 235), width=2)
        canvas.alpha_composite(b_ov)

    bef_label = entry.get("before_label", "시공 전")
    aft_label = entry.get("after_label", "시공 후")
    aft_hdr_rgb = hex_to_rgb(entry.get("after_header_bg", entry.get("accent_color", "#FFD400")))
    aft_txt_rgb = (255, 235, 60) if entry.get("after_header_bg") else (15, 15, 15)
    aft_stroke_rgb = (0, 0, 0) if entry.get("after_header_bg") else (255, 255, 255)

    hdr_ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d_hdr = ImageDraw.Draw(hdr_ov)

    pw1, ph1 = 148, 46
    px1 = c1_x0 + (c1_w - pw1) // 2
    py1 = c_y0 - 18
    d_hdr.rounded_rectangle([px1, py1, px1 + pw1, py1 + ph1], radius=10, fill=(18, 20, 24, 248), outline=(235, 240, 245, 230), width=2)

    pw2, ph2 = 170, 52
    px2 = c2_x0 + (c2_w - pw2) // 2
    py2 = c_y0 - 24
    d_hdr.rounded_rectangle([px2, py2, px2 + pw2, py2 + ph2], radius=12, fill=(*aft_hdr_rgb, 252), outline=(255, 255, 255, 240), width=2)
    canvas.alpha_composite(hdr_ov)

    im_b = render_slanted_gradient_text(bef_label, 28, (255, 255, 255), (230, 235, 240), stroke_width=4, shear=0.08)
    im_a = render_slanted_gradient_text(aft_label, 32, aft_txt_rgb, aft_txt_rgb, stroke_width=4 if entry.get("after_header_bg") else 0, stroke_color=aft_stroke_rgb, shear=0.10)
    canvas.alpha_composite(im_b, (px1 + (pw1 - im_b.width) // 2, py1 + (ph1 - im_b.height) // 2))
    canvas.alpha_composite(im_a, (px2 + (pw2 - im_a.width) // 2, py2 + (ph2 - im_a.height) // 2))

    draw_center_transition_arrow(canvas, (c1_x1 + c2_x0) // 2, (c_y0 + c_y1) // 2 + 12, accent_rgb=accent_rgb)
    draw_opticglass_logo(canvas, 16, 666, logo_height=40)


def render_split_vertical(
    canvas: Image.Image,
    before_im: Image.Image,
    after_im: Image.Image,
    entry: Dict[str, Any],
):
    accent_rgb = hex_to_rgb(entry.get("accent_color", "#FFD400"))
    line1 = entry.get("headline_line1", entry.get("vehicle_ko", "테슬라 모델 Y"))
    line2 = entry.get("headline_line2", "광각미러 차이!")
    if line2 == "광각미러":
        line2 = "광각미러 차이!"

    l1_sz = 62 if len(line1) <= 11 else 54
    l2_sz = 88 if len(line2) <= 9 else 74
    im_l1 = render_slanted_gradient_text(line1, l1_sz, (255, 255, 255), (215, 225, 235), stroke_width=9, shear=0.14)
    y1 = 26
    canvas.alpha_composite(im_l1, (34, y1))
    y2 = y1 + im_l1.height + 2
    im_l2 = render_slanted_gradient_text(line2, l2_sz, (255, 250, 140), accent_rgb, stroke_width=10, shear=0.14)
    canvas.alpha_composite(im_l2, (30, y2))

    # Maintain ~70:30 ratio: left ~70% shows full background vehicle, right ~30% shows stacked cards
    cx0, cx1 = 790, 1260
    t_y0, t_y1 = 28, 344
    b_y0, b_y1 = 364, 684
    cw = cx1 - cx0

    is_sealion = "씨라이언" in line1 or "sealion" in line1.lower()
    bef_crop = resize_cover(before_im, cw, t_y1 - t_y0, align_y=0.33 if is_sealion else 0.5).convert("RGBA")
    aft_crop = resize_cover(after_im, cw, b_y1 - b_y0, align_y=0.62 if is_sealion else 0.5).convert("RGBA")

    for (y0, y1, card_img, is_after) in (
        (t_y0, t_y1, bef_crop, False),
        (b_y0, b_y1, aft_crop, True),
    ):
        ch = y1 - y0
        mask = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=16, fill=255)
        canvas.paste(card_img, (cx0, y0), mask=mask)
        b_ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        d_b = ImageDraw.Draw(b_ov)
        if is_after:
            d_b.rounded_rectangle([cx0 - 2, y0 - 2, cx1 + 2, y1 + 2], radius=18, outline=(*accent_rgb, 255), width=4)
        else:
            d_b.rounded_rectangle([cx0, y0, cx1, y1], radius=16, outline=(230, 235, 240, 230), width=2)
        canvas.alpha_composite(b_ov)

    bef_label = entry.get("before_label", "시공 전")
    aft_label = entry.get("after_label", "시공 후")
    tab_ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d_tab = ImageDraw.Draw(tab_ov)
    d_tab.polygon([(cx0, t_y0), (cx0 + 160, t_y0), (cx0 + 142, t_y0 + 50), (cx0, t_y0 + 50)], fill=(18, 20, 26, 248))
    d_tab.polygon([(cx0, b_y0), (cx0 + 160, b_y0), (cx0 + 142, b_y0 + 50), (cx0, b_y0 + 50)], fill=(*accent_rgb, 252))
    canvas.alpha_composite(tab_ov)

    im_b = render_slanted_gradient_text(bef_label, 28, (255, 255, 255), (240, 245, 250), stroke_width=0, shadow_offset=(0, 0), shear=0.08)
    im_a = render_slanted_gradient_text(aft_label, 28, (15, 15, 15), (15, 15, 15), stroke_width=0, shadow_offset=(0, 0), shear=0.08)
    canvas.alpha_composite(im_b, (cx0 + 22, t_y0 + 8))
    canvas.alpha_composite(im_a, (cx0 + 22, b_y0 + 8))

    draw_opticglass_logo(canvas, 16, 666, logo_height=40)


def build_sharp_custom_background(entry: Dict[str, Any], bg_path: Optional[pathlib.Path] = None) -> Image.Image:
    """
    Builds a 100% sharp (zero-blur) 1280x720 vehicle hero background for custom raw mirror photos.
    The caller must supply this car's own exterior photo: there is no stand-in, so a thumbnail
    never shows another car.
    """
    if bg_path is None or not bg_path.exists():
        raise FileNotFoundError(f"차량 외관 사진이 없습니다: {bg_path}")
    raw_bg = Image.open(bg_path).convert("RGB")
    bg = resize_cover(raw_bg, 1280, 720)
    arr = np.array(bg, dtype=np.float32)
    yy, xx = np.mgrid[0:720, 0:1280]
    top_shade = np.clip((210.0 - yy) / 210.0, 0.0, 1.0) * 0.25
    right_shade = np.clip((xx - 720.0) / 360.0, 0.0, 1.0) * 0.35
    total_shade = 1.0 - np.maximum(top_shade, right_shade)[:, :, None]
    arr = np.clip(arr * total_shade, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def generate_thumbnail(
    ref_id: str = "0031",
    bg_path: Optional[pathlib.Path] = None,
    before_path: Optional[pathlib.Path] = None,
    after_path: Optional[pathlib.Path] = None,
    out_path: pathlib.Path = pathlib.Path("out_thumbnail.jpg"),
    overrides: Optional[Dict[str, Any]] = None,
) -> pathlib.Path:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        cat = json.load(f)

    norm_id = ref_id.zfill(4)
    entry = None
    for item in cat["references"]:
        if item["id"] == norm_id:
            entry = dict(item)
            break
    if entry is None:
        raise KeyError(f"Reference ID {ref_id} not found in catalog_0002_0043.json")

    if overrides:
        for k, v in overrides.items():
            if v is not None:
                entry[k] = v

    out_path.parent.mkdir(parents=True, exist_ok=True)

    missing = [n for n, p in (("외관", bg_path), ("시공 전", before_path), ("시공 후", after_path)) if not (p and p.exists())]
    if missing:
        raise FileNotFoundError(f"이 차의 사진이 없습니다 ({', '.join(missing)}). 다른 차 사진으로 대체하지 않습니다.")
    canvas = build_sharp_custom_background(entry, bg_path).convert("RGBA")
    if entry.get("preset", "split_horizontal") == "split_vertical":
        render_split_vertical(canvas, Image.open(before_path), Image.open(after_path), entry)
    else:
        render_split_horizontal(canvas, Image.open(before_path), Image.open(after_path), entry)
    final_rgb = canvas.convert("RGB")

    if out_path.suffix.lower() == ".png":
        final_rgb.save(out_path, format="PNG")
    else:
        final_rgb.save(out_path, format="JPEG", quality=95, subsampling=0)
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="옵틱글래스 유튜브 썸네일 (0002~0043 레퍼런스 기반) 1280x720 이미지 합성기"
    )
    parser.add_argument("--id", type=str, default="0031", help="레퍼런스 번호 (0002 ~ 0043, 기본값: 0031)")
    parser.add_argument("--preset", choices=["split_horizontal", "split_vertical", "hero_review"], help="레이아웃 프리셋 강제 지정")
    parser.add_argument("--bg", type=str, help="배경/차량 히어로 이미지 경로")
    parser.add_argument("--before", type=str, help="시공 전 사이드미러 사진 경로")
    parser.add_argument("--after", type=str, help="시공 후 광각미러 사진 경로")
    parser.add_argument("--line1", type=str, help="1줄 차종명 텍스트 덮어쓰기 (예: '2025 아우디 Q3')")
    parser.add_argument("--line2", type=str, help="2줄 메인 카피 덮어쓰기 (예: '광각미러 차이!')")
    parser.add_argument("--accent", type=str, help="강조 색상 HEX 코드 (예: '#FFD400', '#00E5FF')")
    parser.add_argument("--out", type=str, default=str(TEMPLATE_DIR / "samples" / "sample_0031.jpg"), help="출력 이미지 경로")

    args = parser.parse_args()

    overrides = {
        "preset": args.preset,
        "headline_line1": args.line1,
        "headline_line2": args.line2,
        "accent_color": args.accent,
    }
    saved = generate_thumbnail(
        ref_id=args.id,
        bg_path=pathlib.Path(args.bg) if args.bg else None,
        before_path=pathlib.Path(args.before) if args.before else None,
        after_path=pathlib.Path(args.after) if args.after else None,
        out_path=pathlib.Path(args.out),
        overrides=overrides,
    )
    print(f"[썸네일 생성 완료] {saved}")


if __name__ == "__main__":
    main()
