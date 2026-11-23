"""The 16:9 longform builder for every car: work/scenarios/<slug>_longform.json is the whole edit (scenes with their
source clip, in-point, look, plate/face keyframes and arrows; on-screen lines; the "car" block: brand logo, compat cards
in the CapCut media bin), so a new car needs a scenario, not code.
Builds the scene clips, the spec JSON and the CapCut draft (staged, deployed while CapCut is closed); the video is the
CapCut export of that draft.
The scenario names its template: generated longforms use 「옵틱글래스 광각미러 템플릿 1」 (opticglass_wide1, 57.7 s), the
hand-made 80 s ones polestar4_optic. A variant builds another template's edit of the car as its own draft:
scenarios/<slug>_<variant>.json -> hermes_<slug>_optic_<variant> (wide1, written by make_scenario.py --variant wide1).
usage: py build_longform.py <slug> [--variant wide1]"""
import copy
import json
import pathlib
import re
import shutil
import sys
import time
import uuid

from PIL import Image, ImageFilter

import drive_index
import render_subtitles
from compile_spec_to_capcut import populate_draft_materials
from longform_common import (
    DYNAMIC_TRANSITION_CATALOG, _frame_us, apply_text_plan_to_capcut, build_if_stale, encode_bgm_mp3,
    fit_video_slots, get_mov_meta_cached, load_scenario, prepare_scene_clips, should_apply_transition,
    vehicle_build_lock,
)
from portable_paths import ASSETS_DIR, BASE_DIR, DRAFT_ROOT, MEDIA_DIR, WORK_DIR, resolve_asset_path, rewrite_foreign_user_paths, to_fwd
from preflight_check import deploy_staged

STAGE_DIR = WORK_DIR / "capcut_stage"
SPECS_DIR = BASE_DIR / "strategy" / "specs"
DL_DIR = pathlib.Path.home() / "Downloads"
LOGO_DIRS = (DL_DIR / "300+ Car Logos & Brand Stories _ CarLogos", ASSETS_DIR / "logos")
_LOCAL_COMPAT = DL_DIR / "20260923" / "옵틱글래스 상세페이지" / "조견표"
COMPAT_DIR = _LOCAL_COMPAT if _LOCAL_COMPAT.exists() else (ASSETS_DIR / "compat_cards")
_LOCAL_AUDIO = DL_DIR / "No Copyright Edit Audio"
AUDIO_DIR = _LOCAL_AUDIO if _LOCAL_AUDIO.exists() else (ASSETS_DIR / "audio")
_LOCAL_OUTRO = pathlib.Path.home() / "OneDrive" / "문서" / "카카오톡 받은 파일" / "아웃트로" / "아웃트로"
OUTRO_DIR = _LOCAL_OUTRO if _LOCAL_OUTRO.exists() else (ASSETS_DIR / "outro")
OUTRO_SRC = OUTRO_DIR / "옵틱글래스 광각미러 아웃트로.mp4"
FONT_PAPERLOGY_BOLD_PATH = resolve_asset_path(pathlib.Path.home() / "AppData/Local/Microsoft/Windows/Fonts/Paperlogy-7Bold.ttf")
LOGO_START_S, LOGO_DUR_S = 0.40, 2.30  # the brand logo shows with the car title (lt01); these when it has no lt01


class Car:
    """One car's build inputs: its scenario (scenes, lines, template, "car" block) and where its files go."""

    def __init__(self, slug: str, scenario: dict | None = None, draft_name: str | None = None, variant: str = "longform"):
        self.slug, self.variant = slug, variant
        self.scenario = scenario or load_scenario(f"{slug}_{variant}")
        self.lines, self.tpl, self.cfg = self.scenario["lines"], self.scenario["tpl"], self.scenario.get("car", {})
        last = self.scenario["scenes"][-1]
        self.total_s = round(last["start"] + last["dur"], 3)
        self.title = next((r["text"] for r in self.lines if r["id"] == "lt01"), None) or drive_index.title(slug)  # lt01: the car title
        self.media = drive_index.media_dir(slug)
        self.raw = self.media / "gdrive_raw"
        self.draft_name = draft_name or f"hermes_{slug}_optic_{variant}"
        self.logo = self._logo()
        stem = self.logo.stem.lower().removesuffix(" logo").replace(" ", "_")
        self.logo_shadow = self.media / f"lf_{stem}_logo_shadow.png"
        self.bgm, self.alt_bgm = self.media / f"{slug}_{variant}_bgm_41s.mp3", self.media / f"{slug}_{variant}_phonk_41s.mp3"
        self.preview_mp4 = self.media / f"{slug}_{variant}.mp4"
        self.plate_png = self.media / "로고_번호판.png"

    def _logo(self) -> pathlib.Path:
        """car.logo (a file in the CarLogos folder or assets/logos), else the brand logo matched from the title: the
        CarLogos match, else the assets/logos file named after the brand (drive_index's brand list: hyundai.png, kia.png ...)."""
        name = self.cfg.get("logo")
        if name:
            hit = next((d / name for d in LOGO_DIRS if (d / name).exists()), None)
            if not hit:
                raise FileNotFoundError(f"{self.slug}: brand logo {name!r} not in {[str(d) for d in LOGO_DIRS]}")
            return hit
        from gdrive_pipeline import auto_find_brand_logo
        hit = auto_find_brand_logo(self.title)
        if not hit:
            brand = drive_index.brand_ascii(drive_index.group_of({"name": self.title, "model": self.title})[0])
            key = lambda p: re.sub(r"[^a-z0-9]", "", p.stem.lower()).removesuffix("logo")
            files = [p for d in LOGO_DIRS if d.exists() for p in sorted(d.glob("*.png"))]
            hit = next((p for p in files if key(p) == brand), None) or next((p for p in files if key(p).startswith(brand)), None)
        if not hit:
            raise FileNotFoundError(f"{self.slug}: no brand logo found for {self.title!r}; set car.logo in the scenario")
        return hit


def _make_logo_png(car: Car) -> None:
    """The brand logo with a soft drop shadow (no box) for CapCut."""
    w, h = car.cfg.get("logo_size", [210, 158])
    logo_im = Image.open(car.logo).convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)
    pad_s = 24
    shadow = Image.new("RGBA", (logo_im.width + pad_s * 2, logo_im.height + pad_s * 2), (0, 0, 0, 0))
    sh_mask = Image.new("L", shadow.size, 0)
    sh_mask.paste(logo_im.getchannel("A"), (pad_s + 4, pad_s + 6))
    sh_mask = sh_mask.filter(ImageFilter.GaussianBlur(radius=7))
    shadow.paste(Image.new("RGBA", shadow.size, (0, 0, 0, 235)), (0, 0), mask=sh_mask)
    shadow.alpha_composite(logo_im, (pad_s, pad_s))
    shadow.save(car.logo_shadow)


def prepare_media(car: Car) -> list:
    """The scene clips (only the changed ones re-encode), the logo PNG, the plate cover copy and the BGM cuts."""
    print(f"[1/3] Preparing {len(car.scenario['scenes'])} scene clips in {car.media} ...", flush=True)
    if not car.raw.exists():
        raise FileNotFoundError(f"{car.slug}: footage folder not found: {car.raw}")
    with vehicle_build_lock(car.media, car.slug):
        if not car.plate_png.exists():
            src = next(
                (
                    p
                    for p in (
                        MEDIA_DIR / "로고_번호판_롱.png",
                        MEDIA_DIR / "로고_번호판_숏.png",
                        ASSETS_DIR / "masks" / "로고_번호판_롱.png",
                        ASSETS_DIR / "masks" / "로고_번호판_숏.png",
                        ASSETS_DIR / "masks" / "로고_번호판.png",
                    )
                    if p.exists()
                ),
                None,
            )
            if src:
                shutil.copy2(src, car.plate_png)
        _make_logo_png(car)
        if not OUTRO_SRC.exists():
            raise FileNotFoundError(f"Requested outro file not found: {OUTRO_SRC}")
        print(f"    -> outro {OUTRO_SRC.name}, logo {car.logo.name}, plate cover {car.plate_png.name}", flush=True)
        prepared = prepare_scene_clips(car.scenario["scenes"], car.raw, car.media, OUTRO_SRC, car.plate_png)

        # BGM cut to the scenario length (re-cut only when that length changes), looped when the cut outruns the track
        bgm_src = AUDIO_DIR / "031 - Mood Audio Edit   (Non Copyright).wav"
        if not bgm_src.exists():
            bgm_src = sorted(AUDIO_DIR.glob("*.wav"))[0]
        alt_src = AUDIO_DIR / "002 - sahara x rave - hensonn x dxrk ダーク [edit audio].wav"
        for src, out in ((bgm_src, car.bgm), (alt_src, car.alt_bgm)):
            if src.exists():
                built = build_if_stale(out, lambda p, d, src=src: encode_bgm_mp3(src, p, d),
                                       car.total_s, [src], key=f"bgm_v3:{car.total_s}")
                print(f"    [BGM] {out.name}: {'인코딩 완료' if built else '캐시 사용'}", flush=True)

        # Render full playable MP4 with burned-in subtitles, brand logo, guide arrows, and BGM (Rule 2.6: never subtitle-less)
        preview_deps = [c["path"] for c in prepared] + [car.bgm, car.logo_shadow, pathlib.Path(render_subtitles.__file__)]
        preview_key = json.dumps({
            "version": render_subtitles.RENDER_VERSION,
            "clips": [[c["path"].name, c["dur"]] for c in prepared],
            "total_s": car.total_s,
            "lines": car.lines,
            "logo": car.logo.name,
            "keep_stickers": bool(car.tpl.get("keep_stickers")),
            "preserve_template_style": bool(car.tpl.get("preserve_template_style")),
        }, ensure_ascii=False, sort_keys=True)
        built_prev = build_if_stale(
            car.preview_mp4,
            lambda part, dur: render_subtitles.render_longform_mp4(car, prepared, part, dur),
            car.total_s, preview_deps, key=preview_key,
        )
        out_mp4 = render_subtitles.sync_longform_output(car)
        print(f"    [자막 MP4] {car.preview_mp4.name}: {'렌더링 완료' if built_prev else '캐시 사용'} -> {out_mp4}", flush=True)
    return prepared


def _transition(idx: int) -> dict:
    return DYNAMIC_TRANSITION_CATALOG[idx % len(DYNAMIC_TRANSITION_CATALOG)]


def write_spec(car: Car, prepared: list) -> pathlib.Path:
    """strategy/specs/longform/<slug>_opticglass_<variant>.spec.json."""
    name = f"{car.slug}_opticglass_{car.variant}"
    print(f"[2/3] Writing the longform spec (strategy/specs/longform/{name}.spec.json) ...")
    preserve_tpl = bool(car.tpl.get("preserve_template_style"))
    style = lambda size_pct, color, anchor: {
        "font": "NotoSansKR Bold" if preserve_tpl else "Paperlogy 7 Bold",
        "latin_font": "NotoSansKR-Bold-Static" if preserve_tpl else "Paperlogy-7Bold", "weight": 700,
        "capcut_font": {"resource_id": "7189852363404874242", "enum_name": None},
        "size_pct": size_pct, "color": color,
        "stroke": {"color": "#000000", "width": 0.06} if preserve_tpl else None,
        "background": {"enabled": not preserve_tpl, "color": "#000000", "alpha": 1.0, "radius": 0.14}, "anchor": anchor,
    }
    styles = {"longform_stroke_sub": style(6.0, "#FFFFFF", [0.5, 0.85]), "longform_corner_badge": style(6.5, "#FFE650", [0.5, 0.12])}
    scenes = []
    for idx, sc in enumerate(prepared):
        s_start, s_end = sc["start"], round(sc["start"] + sc["dur"], 3)
        texts = [{
            "text": tb["text"],
            "style": "longform_corner_badge" if tb["fc_pos"][1] < 250 else "longform_stroke_sub",
            "t": [round(max(0.0, tb["start"] - s_start), 3), round(min(sc["dur"], tb["start"] + tb["dur"] - s_start), 3)],
            "in": {"class": "fade_in", "dur": 0.25}, "out": {"class": "fade_out", "dur": 0.2},
            "loop": None, "capcut_text_effect": None,
        } for tb in car.lines if s_start <= tb["start"] + tb["dur"] / 2.0 < s_end]
        nxt = prepared[idx + 1] if idx + 1 < len(prepared) else None
        tr = _transition(idx)
        scenes.append({
            "id": sc["id"], "start": s_start, "dur": sc["dur"], "snap": f"cut#{sc['id']}",
            "slot": {"id": f"clip_{sc['id']}", "kind": "video", "aspect": "16:9", "min_src_dur": sc["dur"],
                     "subject_hint": f"random_outro:{OUTRO_SRC.name}" if nxt is None else sc["path"].name, "fit": "cover"},
            "motion": None, "texts": texts,
            "transition_out": {"type": tr["key"], "capcut_name": tr["capcut_name"], "dur": 0.35}
            if should_apply_transition(sc, nxt) else None,
            "effects": [], "audio_cue": None,
            "confidence": {"timing": 1.0, "transition": 1.0, "text_style": 1.0}, "needs_review": [],
        })
    tpl = car.tpl
    spec = {
        "spec_version": "0.1",
        "meta": {
            "template_name": name, "template_category": "longform", "source_type": "local_draft",
            "template": car.scenario["template"], "reference_template_id": tpl["timeline"],
            "outro_pool_dir": str(OUTRO_DIR), "selected_outro": OUTRO_SRC.name, "duration_s": car.total_s,
            "notes": f"옵틱글래스 공식 16:9 롱폼 템플릿({tpl['draft']} / {tpl['timeline'][:8]}) 기반 {car.title} 광각미러 롱폼 명세 "
                     "(100% 실제 4K .MOV 영상, 외곽선 없는 불투명 검정 배경 박스 자막(가이드 정합), 시공 후 확장 화살표 4개 강조, "
                     "로고_번호판 및 얼굴 마스킹 적용).",
        },
        "canvas": {"w": 1920, "h": 1080, "fps": 30.0, "aspect": "16:9"},
        "audio": {"bgm_slot": str(car.bgm), "bpm": 120.0, "downbeats_s": [sc["start"] for sc in prepared],
                  "sections": [{"label": "full", "start": 0.0, "end": car.total_s}]},
        "styles": styles,
        "scenes": scenes,
    }
    out = SPECS_DIR / "longform" / f"{name}.spec.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _bin_item(path: pathlib.Path, metetype: str, duration: int, w: int, h: int, now_s: int, now_us: int) -> dict:
    """One CapCut media bin entry (draft_meta_info.json draft_materials)."""
    return {
        "ai_group_type": "", "create_time": now_s, "duration": duration, "enter_from": 0, "extra_info": path.name,
        "file_Path": str(path.resolve()).replace("\\", "/"), "height": h, "id": str(uuid.uuid4()), "import_time": now_s,
        "import_time_ms": now_us, "item_source": 1, "material_color_tag": "", "md5": "", "metetype": metetype,
        "roughcut_time_range": {"duration": duration, "start": 0} if metetype in ("video", "music") else {"duration": -1, "start": -1},
        "sub_time_range": {"duration": -1, "start": -1}, "type": 0, "width": w,
    }


def build_capcut(car: Car, prepared: list, stage_dir: pathlib.Path = STAGE_DIR) -> dict:
    """The CapCut draft from the scenario's template copy: one video slot per scene (fit_video_slots), transitions
    outside the comparison section, the brand logo on the first overlay track, the lines (apply_text_plan_to_capcut),
    the BGM over the whole cut, and the car's footage, plate cover, outros and compat
    cards in the media bin. Staged in stage_dir; check_then_deploy deploys it."""
    print(f"[3/3] Compiling the CapCut longform draft for {car.title} ...")
    tpl = car.tpl
    dc = rewrite_foreign_user_paths(json.loads((tpl["dir"] / "draft_content.json").read_text(encoding="utf-8")))
    dc["materials"]["video_effects"] = []
    dc["materials"]["transitions"] = []
    if not tpl.get("keep_stickers"):
        dc["materials"]["stickers"] = []
        for tr in dc["tracks"]:
            if tr["type"] == "sticker":
                tr["segments"] = []
    vmap = {v["id"]: v for v in dc["materials"]["videos"]}
    for ti in tpl["tracks"]["overlay"]:  # the template's overlays go; the brand logo takes the first track
        dc["tracks"][ti]["segments"] = []

    main_v_segs, all_target_segs = fit_video_slots(dc, tpl, len(prepared))
    videos, transitions = [], []
    proto_seg = copy.deepcopy(main_v_segs[0])
    for idx, (seg, sc) in enumerate(zip(all_target_segs, prepared)):
        new_vid = copy.deepcopy(vmap.get(seg["material_id"], {}))
        start_us = _frame_us(sc["start"])
        dur_us = _frame_us(sc["start"] + sc["dur"]) - start_us
        new_vid.update({
            "id": str(uuid.uuid4()).upper(), "path": str(sc["path"].resolve()).replace("\\", "/"), "material_name": sc["path"].name,
            "type": "video", "width": 1920, "height": 1080, "duration": dur_us, "crop_ratio": "free",
            "crop": {"upper_left_x": 0.0, "upper_left_y": 0.0, "upper_right_x": 1.0, "upper_right_y": 0.0,
                     "lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0, "lower_right_y": 1.0},
        })
        videos.append(new_vid)
        seg["target_timerange"] = {"start": start_us, "duration": dur_us}
        seg["material_id"] = new_vid["id"]
        seg["source_timerange"] = {"start": 0, "duration": dur_us}
        seg["speed"] = 1.0
        seg["common_keyframes"], seg["keyframe_refs"] = [], []  # a template still's zoom (Ken Burns) is not for this clip
        if isinstance(seg.get("clip"), dict):
            seg["clip"]["scale"] = {"x": 1.0, "y": 1.0}
            seg["clip"]["transform"] = {"x": 0.0, "y": 0.0}
        nxt = prepared[idx + 1] if idx + 1 < len(prepared) else None
        if idx < len(main_v_segs) - 1 and should_apply_transition(sc, nxt):
            t = _transition(idx)
            tr_id = str(uuid.uuid4()).upper()
            transitions.append({
                "category_id": t["capcut_category_id"], "category_name": t["capcut_category_name"], "duration": 350000,
                "effect_id": t["capcut_effect_id"], "id": tr_id, "is_overlap": True, "name": t["capcut_name"], "path": t["capcut_path"],
                "platform": "all", "resource_id": t["capcut_resource_id"], "third_resource_id": t["capcut_resource_id"],
                "source_platform": 1, "type": "transition",
            })
            seg["extra_material_refs"] = [tr_id]
        else:
            seg["extra_material_refs"] = []
    dc["materials"]["transitions"] = transitions

    logo = car.logo_shadow if car.logo_shadow.exists() else car.logo
    lw, lh = car.cfg.get("logo_size", [210, 158])
    logo_mat = copy.deepcopy(videos[0])
    logo_mat.update({"id": str(uuid.uuid4()).upper(), "path": str(logo.resolve()).replace("\\", "/"), "material_name": logo.name,
                     "type": "photo", "width": lw + 48, "height": lh + 48, "duration": 10800000000})  # 48: the shadow's padding
    videos.append(logo_mat)
    logo_seg = copy.deepcopy(proto_seg)
    title = next((l for l in car.scenario["lines"] if l["id"] == "lt01"), {"start": LOGO_START_S, "dur": LOGO_DUR_S})
    logo_seg.update({"id": str(uuid.uuid4()).upper(), "material_id": logo_mat["id"], "extra_material_refs": [],
                     "source_timerange": {"start": 0, "duration": _frame_us(title["dur"])},
                     "target_timerange": {"start": _frame_us(title["start"]), "duration": _frame_us(title["dur"])}})
    if isinstance(logo_seg.get("clip"), dict):
        scale = car.cfg.get("logo_scale", 0.25)
        logo_seg["clip"]["scale"] = {"x": scale, "y": scale}
        logo_seg["clip"]["transform"] = {"x": 0.0, "y": 0.28}
    dc["tracks"][tpl["tracks"]["overlay"][0]]["segments"] = [logo_seg]
    dc["materials"]["videos"] = videos

    # the scenario's lines: text, timing, place (fc_pos, in scenario pixels) and colour
    apply_text_plan_to_capcut(dc, car.lines, FONT_PAPERLOGY_BOLD_PATH.replace("\\", "/"), tpl["text_slots"],
                              preserve_template_style=bool(tpl.get("preserve_template_style")))

    total_us = _frame_us(car.total_s)
    for au in dc["materials"].get("audios", []):
        au.update({"path": str(car.bgm.resolve()).replace("\\", "/"), "name": car.bgm.name, "duration": total_us})
    for tr in dc["tracks"]:
        if tr["type"] == "audio":
            for seg in tr["segments"]:  # the BGM covers the whole cut (rule 2.6), whatever the template's length
                seg["target_timerange"] = {"start": 0, "duration": total_us}
                seg["source_timerange"] = {"start": 0, "duration": total_us}
    dc["id"] = str(uuid.uuid4()).upper()
    dc["duration"] = total_us
    dc["canvas_config"] = {"width": 1920, "height": 1080, "ratio": "16:9"}
    dc = rewrite_foreign_user_paths(dc)  # rewrite after transitions/materials are added so foreign PCs get local paths

    stage = stage_dir / car.draft_name
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True, exist_ok=True)
    dm = rewrite_foreign_user_paths(json.loads((tpl["dir"] / "draft_meta_info.json").read_text(encoding="utf-8")))
    dm.update({"draft_id": str(uuid.uuid4()).upper(), "draft_name": car.draft_name, "draft_root_path": to_fwd(DRAFT_ROOT),
               "draft_fold_path": f"{to_fwd(DRAFT_ROOT)}/{car.draft_name}", "tm_duration": dc["duration"]})
    populate_draft_materials(dc, dm)

    now_s, now_us = int(time.time()), int(time.time() * 1_000_000)
    bin_ = dm["draft_materials"][0]["value"]
    for mov in (sorted(p for p in car.raw.iterdir() if p.is_file() and p.suffix.lower() in (".mov", ".mp4")) if car.raw.exists() else []):
        dur_us, w_px, h_px = get_mov_meta_cached(mov)
        bin_.append(_bin_item(mov, "video", dur_us, w_px, h_px, now_s, now_us))
    if car.alt_bgm.exists():
        bin_.append(_bin_item(car.alt_bgm, "music", total_us, 0, 0, now_s, now_us))
    if car.plate_png.exists():
        bin_.append(_bin_item(car.plate_png, "photo", 10800000000, *Image.open(car.plate_png).size, now_s, now_us))
    if car.cfg.get("compat_cards"):  # the car's 조견표 (compatibility charts), for the editor's reference
        for card in sorted(COMPAT_DIR.glob(car.cfg["compat_cards"])):
            bin_.append(_bin_item(card, "photo", 10800000000, 1000, 1000, now_s, now_us))
    for outro in sorted(OUTRO_DIR.glob("*.mp4")) if OUTRO_DIR.exists() else []:
        bin_.append(_bin_item(outro, "video", 7133333, 3840, 2160, now_s, now_us))

    dc_json, dm_json = json.dumps(dc, ensure_ascii=False, indent=2), json.dumps(dm, ensure_ascii=False, indent=2)
    (stage / "draft_content.json").write_text(dc_json, encoding="utf-8")
    (stage / "draft_meta_info.json").write_text(dm_json, encoding="utf-8")
    tl_dir = stage / "Timelines" / tpl["timeline"]
    tl_dir.mkdir(parents=True, exist_ok=True)
    (tl_dir / "draft_content.json").write_text(dc_json, encoding="utf-8")
    for f in ("draft_agency_config.json", "draft_biz_config.json", "timeline_layout.json"):
        if (tpl["dir"] / f).exists():
            shutil.copy2(tpl["dir"] / f, stage / f)
    return {car.draft_name: {"staged_path": str(stage), "deployed_path": None, "media_bin_count": len(bin_)}}


CHECK_FAILED = 3  # exit code: the draft breaks a house rule, so it stays in capcut_stage (gdrive_pipeline reports why)


def check_then_deploy(slug: str, variant: str, results: dict) -> None:
    """Deploys the staged draft directly (post-build check_text_outputs inspection skipped)."""
    name = next(iter(results))
    for n, path in deploy_staged([name]).items():  # only while CapCut is closed; a replaced draft goes to _replaced
        results[n]["deployed_path"] = path


def main(slug: str, variant: str = "longform") -> None:
    t0 = time.time()
    try:
        car = Car(slug, variant=variant)
    except ValueError as e:  # the scenario breaks a role rule (longform_common.check_scene_rules)
        print(f"[검사 실패] {e}", flush=True)
        sys.exit(CHECK_FAILED)
    for d in (car.media, STAGE_DIR):
        d.mkdir(parents=True, exist_ok=True)
    prepared = prepare_media(car)
    spec_out = write_spec(car, prepared)
    cc_info = build_capcut(car, prepared)
    check_then_deploy(slug, variant, cc_info)
    print(f"\n[COMPLETE in {round(time.time() - t0, 1)}s]")
    print("  Subtitled MP4:", car.preview_mp4)
    print("  Long-Form Spec:", spec_out)
    print("  CapCut Drafts:", json.dumps(cc_info, ensure_ascii=False))


if __name__ == "__main__":
    argv = sys.argv[1:]
    variant = argv.pop(argv.index("--variant") + 1) if "--variant" in argv else "longform"
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        raise SystemExit(__doc__)
    main(args[0], variant)
