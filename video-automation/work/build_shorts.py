"""The 9:16 shortform builder for every car, on the CapCut shortform template (scenarios/templates/shorts_optic, a copy
of the user's multi-timeline project 「숏폼 영상 프로젝트」): one CapCut project with five shorts, each a stretch of the
car's longform shown in a 9:16 frame:
- 비트: the intro (first BEAT_S s) over a blurred, zoomed copy of itself, the OpticGlass logo on top;
- 외관 / 시공 전 / 시공 후 / 전후 비교: one section of the longform, fitted to the frame's width, with a two-line hook
  above it (the template's green-glow text, written per car by agy) and the logo under it.
The longform here is the car's scene clips joined (plates and faces already covered, the 4 arrows already drawn) with
its BGM, so no CapCut export is needed; the longform's captions are not in it. Sections come from the scene ids of the
car's longform scenario (scenarios/<slug>_longform.json: a hand-made 80 s cut, or the generated 57.7 s
「광각미러 템플릿 1」 cut, whose 시공 전 / 시공 후 / 전후 비교 are its compare_before / compare_after / split scenes).
Builds media/<car>/shorts_source.mp4, then the draft hermes_<slug>_optic_shorts (staged; deployed while CapCut is closed).

usage: py build_shorts.py <slug>
       py build_shorts.py --extract "<CapCut draft folder>"   copy a shortform project into scenarios/templates/shorts_optic
       py build_shorts.py                                      self-check (no agy call, no build)
"""
from __future__ import annotations

import copy
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import uuid

import build_longform as bl
import drive_index
import render_subtitles
from compile_spec_to_capcut import populate_draft_materials
from longform_common import SCENARIOS_DIR, _enc_clip, _frame_us, atomic_write_json, build_if_stale, run_ffmpeg, vehicle_build_lock
from portable_paths import ASSETS_DIR, DRAFT_ROOT, find_ffmpeg, rewrite_foreign_user_paths, to_fwd

TEMPLATE = SCENARIOS_DIR / "templates" / "shorts_optic"
LOGO = ASSETS_DIR / "logos" / "옵틱글래스 로고.png"
BEAT_S = 12.6  # the template's 비트 length
# The template's five timelines in its order -> what each short shows here
# (the template's 내부/성능/가격 chapters have no counterpart in a mirror longform)
CHAPTERS = ["비트", "외관", "시공 전", "시공 후", "전후 비교"]
CHAPTER_ROLES = {
    "외관": ("exterior", "detail"),
    "시공 전": ("before", "install"),
    "시공 후": ("after",),
    "전후 비교": ("compare_before", "compare_after", "split", "close"),
}
# 광각미러 템플릿 1 (no before/install/after scenes): its single before and after mirror shots are the 시공 전/후 shorts
WIDE1_ROLES = {**CHAPTER_ROLES, "시공 전": ("compare_before",), "시공 후": ("compare_after",), "전후 비교": ("split",)}
HOOK_ASK = """You write the two-line hook text shown above five YouTube Shorts (Korean). They are cut from a video of an
OpticGlass wide-angle side mirror install (the stock side-mirror glass is replaced with a wide-view glass) on a {car}.
Shorts: "비트" (high-impact intro showcase of the car and OpticGlass mirror install), "외관" (the car's exterior),
"시공 전" (the narrow view of the stock side mirror), "시공 후" (the wide view of the OpticGlass mirror),
"전후 비교" (stock vs OpticGlass side by side).
Each hook: 2 lines, each at most {max_len} characters, catchy and spoken Korean, at most one emoji in the two lines.
No prices, specs or claims you cannot see in such a video. The tone of the headlines this channel's shorts use:
{examples}.
Answer with only a JSON object: {{"비트": ["line 1", "line 2"], "외관": [...], "시공 전": [...], "시공 후": [...], "전후 비교": [...]}}"""
HOOK_MAX = 18
HOOK_EXAMPLES = ["대륙의 실수 전기 SUV 🚨 / 모델Y 잡으러 온 역대급 신차", "차박 무조건 가능⛺ / 광활하다 못해 넓어 터진 공간"]


def hook_examples(n: int = 6, avoid: tuple = ()) -> str:
    """The channel's recent OpticGlass shorts headlines (youtube_lines.py; none naming this car), topped up with the
    template's old ones."""
    import youtube_lines
    got = [h.replace("\n", " / ") for h in youtube_lines.shorts_headlines(n, avoid)]
    got += [h for h in HOOK_EXAMPLES if h not in got][:max(0, n - len(got))]
    return ", ".join(json.dumps(h, ensure_ascii=False) for h in got)


def utf16_len(s: str) -> int:
    """CapCut text ranges count UTF-16 units (an emoji is 2)."""
    return len(s.encode("utf-16-le")) // 2


# --- template ---------------------------------------------------------------------------------------------------------
def extract(draft: str) -> None:
    """Copies the plaintext timelines and project index of a CapCut shortform project into TEMPLATE, with
    template.json: the timelines in project order ({id, name, dur}) and the main one."""
    src = DRAFT_ROOT / draft
    project = json.loads((src / "Timelines" / "project.json").read_text(encoding="utf-8"))
    tls = [t for t in project["timelines"] if not t.get("is_marked_delete")]
    if len(tls) != len(CHAPTERS):
        raise SystemExit(f"{draft}: {len(tls)} timelines, the builder maps {len(CHAPTERS)} ({CHAPTERS})")
    dcs = []  # read and check every timeline before the old template goes: it is the only copy
    for t in tls:
        f = src / "Timelines" / t["id"] / "draft_content.json"
        if f.read_bytes()[:1] != b"{":
            raise SystemExit(f"{f} is encrypted; only plaintext drafts can be templates")
        dcs.append(json.loads(f.read_text(encoding="utf-8")))
    shutil.rmtree(TEMPLATE, ignore_errors=True)
    (TEMPLATE / "Timelines").mkdir(parents=True)
    out = []
    for t, dc in zip(tls, dcs):
        (TEMPLATE / "Timelines" / t["id"]).mkdir()
        (TEMPLATE / "Timelines" / t["id"] / "draft_content.json").write_text(json.dumps(dc, ensure_ascii=False), encoding="utf-8")
        out.append({"id": t["id"], "name": t["name"], "dur": round(dc["duration"] / 1e6, 3)})
    (TEMPLATE / "Timelines" / "project.json").write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
    (TEMPLATE / "template.json").write_text(json.dumps({"draft": draft, "main": project["main_timeline_id"], "timelines": out},
                                                       ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"shorts_optic: {[(t['name'], t['dur']) for t in out]} -> {TEMPLATE}")


# --- inputs -----------------------------------------------------------------------------------------------------------
def sections(scenes: list, total: float) -> list:
    """[(chapter, start s, dur s)] in CHAPTERS order: the 비트 is the first BEAT_S s, each other chapter spans the
    longform scenes whose role belongs to that chapter (load_scenario gives every scene a role)."""
    out = []
    roles = CHAPTER_ROLES if any(s.get("role") in ("before", "install", "after") for s in scenes) else WIDE1_ROLES
    for name in CHAPTERS:
        if name == "비트":
            out.append((name, 0.0, round(min(BEAT_S, total), 3)))
            continue
        hit = [s for s in scenes if s.get("role") in roles[name]]
        if not hit:
            raise ValueError(f"no longform scene ({roles[name]}) for the {name} short")
        a, b = min(s["start"] for s in hit), max(s["start"] + s["dur"] for s in hit)
        out.append((name, round(a, 3), round(b - a, 3)))
    return out


def _concat_line(lst: pathlib.Path, clip_path: pathlib.Path) -> str:
    rel = clip_path.name if clip_path.resolve().parent == lst.resolve().parent else to_fwd(clip_path.resolve())
    return "file '" + rel.replace("'", r"'\''") + "'\n"


def source_video(car, prepared: list) -> pathlib.Path:
    """media/<car>/shorts_source.mp4: the pre-outro section of the subtitled longform MP4 (matching @optic_glass/shorts
    so the center 16:9 frame carries the longform subtitles and BGM)."""
    clips = prepared[:-1]  # the last scene is the outro (load_scenario), which no short shows
    total = round(clips[-1]["start"] + clips[-1]["dur"], 3)
    out = car.media / "shorts_source.mp4"
    src_mp4 = car.preview_mp4

    def build(part, dur):
        if src_mp4.exists() and src_mp4.stat().st_size >= 10_000:
            copy_cmd = [find_ffmpeg(), "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
                        "-i", str(src_mp4), "-t", f"{dur:.3f}", "-c:v", "copy", "-c:a", "copy", str(part)]
            res = subprocess.run(copy_cmd, stdin=subprocess.DEVNULL, capture_output=True,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if res.returncode == 0 and part.exists() and part.stat().st_size > 0:
                return
            run_ffmpeg(["-i", str(src_mp4), "-t", f"{dur:.3f}",
                        "-vf", "fps=30,format=yuv420p", *_enc_clip(), "-c:a", "aac", "-b:a", "192k", str(part)])
            return
        lst = car.media / f"shorts_source.{os.getpid()}.txt"
        try:
            lst.write_text("".join(_concat_line(lst, c["path"]) for c in clips), encoding="utf-8")
            run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(car.bgm), "-map", "0:v", "-map", "1:a",
                        "-vf", "fps=30,format=yuv420p", *_enc_clip(), "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}", str(part)])
        finally:
            lst.unlink(missing_ok=True)

    deps = ([src_mp4] if src_mp4.exists() else [c["path"] for c in clips] + [car.bgm])
    key = json.dumps({"src": src_mp4.name, "total": total, "v": render_subtitles.RENDER_VERSION}, sort_keys=True)
    with vehicle_build_lock(car.media, f"{car.slug}_shorts"):
        build_if_stale(out, build, total, deps, key=key)
    return out


def _default_hooks(car) -> dict:
    return {
        "비트": [f"{car.title[:14]} 광각미러", "옵틱글래스 시공으로 시야 확장"],
        "외관": [f"{car.title[:12]} 실물 포스 🚨", "광각미러 시공 입고"],
        "시공 전": ["순정 미러 답답한 시야", "사각지대 그대로 노출"],
        "시공 후": ["옵틱글래스 광각미러 장착!", "시야각이 확 넓어집니다"],
        "전후 비교": ["순정 vs 옵틱글래스 비교", "한눈에 보이는 시야 차이"],
    }


def hooks(car) -> dict:
    """{chapter: [line 1, line 2]} for ALL FIVE shorts (including 비트), written by agy once per car title and kept in
    media/<car>/shorts_hooks.json (edit that file to change them; delete it to have agy write new ones)."""
    f = car.media / "shorts_hooks.json"
    kept = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    default_hooks = _default_hooks(car)
    if kept.get("car") == car.title and isinstance(kept.get("hooks"), dict):
        got = dict(kept["hooks"])
        updated = False
        for n in CHAPTERS:
            if not (isinstance(got.get(n), list) and len(got[n]) == 2 and all(isinstance(x, str) and x.strip() for x in got[n])):
                got[n] = default_hooks[n]
                updated = True
        if updated:
            atomic_write_json(f, {"car": car.title, "hooks": got}, indent=1)
        return got
    import llm
    names = list(CHAPTERS)
    examples = hook_examples(avoid=(car.title, car.slug, car.title.split()[-1]))
    for attempt in (1, 2):
        try:
            ans = llm.generate_json("scenario_lines", HOOK_ASK.format(car=car.title, max_len=HOOK_MAX, examples=examples))
        except Exception as exc:
            if attempt == 2:
                print(f"  [숏폼 훅 폴백] agy 응답 실패({exc}) — 기본 훅 문구를 사용합니다", flush=True)
                ans = default_hooks
                break
            continue
        bad = [n for n in names if not (isinstance(ans.get(n), list) and len(ans[n]) == 2
                                        and all(isinstance(x, str) and 0 < len(x.strip()) <= HOOK_MAX + 2 for x in ans[n]))]
        if not bad:
            break
        if attempt == 2:
            print(f"  [숏폼 훅 폴백] agy 문구 규칙 미충족({', '.join(bad)}) — 해당 구간은 기본 훅 문구를 사용합니다", flush=True)
            for n in bad:
                ans[n] = default_hooks[n]
    got = {n: [x.strip() for x in ans[n]] for n in names}
    atomic_write_json(f, {"car": car.title, "hooks": got}, indent=1)
    return got


def _extract_text_proto(dc: dict) -> dict | None:
    """Return a deep copy of a timeline's text track + text material so text-less timelines (비트) can inherit it."""
    texts = dc.get("materials", {}).get("texts", [])
    ttracks = [tr for tr in dc.get("tracks", []) if tr.get("type") == "text" and tr.get("segments")]
    if not texts or not ttracks:
        return None
    return {"track": copy.deepcopy(ttracks[0]), "mat": copy.deepcopy(texts[0])}


def _style_shorts_hook_mat(mat: dict, text: str) -> None:
    """Clean @optic_glass/shorts top 2-line hook look: pure bold white Korean font on black letterbox, no green glow."""
    font_path = to_fwd(render_subtitles.resolve_font_file("shorts_hook").resolve())
    font_id = str(uuid.uuid5(uuid.NAMESPACE_URL, font_path)).upper()
    content = json.loads(mat.get("content") or "{}")
    style = (content.get("styles") or [{}])[0]
    style.update({
        "range": [0, utf16_len(text)],
        "size": 13.5,
        "bold": False,
        "useLetterColor": True,
        "font": {"id": font_id, "path": font_path},
        "fill": {"alpha": 1.0, "content": {"render_type": "solid", "solid": {"alpha": 1.0, "color": [1.0, 1.0, 1.0]}}},
        "strokes": [],
        "shadows": [],
        "effectStyle": None,
    })
    content.update({"text": text, "styles": [style]})
    mat.update({
        "content": json.dumps(content, ensure_ascii=False),
        "text_color": "#FFFFFF",
        "use_effect_default_color": False,
        "font_path": font_path,
        "font_title": "NotoSansKR Bold",
        "font_id": "",
        "font_resource_id": "",
        "fonts": [{"id": font_id, "path": font_path, "title": "NotoSansKR Bold", "resource_id": "",
                   "third_resource_id": "", "category_id": "", "category_name": "", "source_platform": 0, "effect_id": "",
                   "team_id": "", "file_uri": "", "request_id": ""}],
        "font_size": 13.5,
        "alignment": 1,
        "background_style": 0,
        "has_shadow": False,
        "bold_width": 0.0,
        "check_flag": 7,
    })


# --- the draft --------------------------------------------------------------------------------------------------------
def fill_timeline(dc: dict, source: pathlib.Path, source_us: int, start_s: float, dur_s: float,
                  hook: list | None, text_proto: dict | None = None) -> dict:
    """One template timeline on this car's source: every video clip plays source start_s..+dur_s, the logo sits in the
    bottom band (y=-0.658) and the 2-line white bold hook sits in the top band (y=+0.658) across ALL 5 timelines."""
    dc = rewrite_foreign_user_paths(copy.deepcopy(dc))
    M = dc["materials"]
    a = _frame_us(start_s)
    d = min(_frame_us(start_s + dur_s), source_us) - a  # the source's -t cut can end a frame before the rounded end
    kind = {}
    for v in M["videos"]:
        if v["type"] == "photo":
            v.update({"path": to_fwd(LOGO.resolve()), "material_name": LOGO.name})
        else:
            v.update({"path": to_fwd(source.resolve()), "material_name": source.name, "duration": source_us,
                      "width": 1920, "height": 1080})
        kind[v["id"]] = v["type"]

    # Inject a text track/material if the template timeline (e.g. 비트) lacked one
    if hook and not M.get("texts") and text_proto is not None:
        new_mat = copy.deepcopy(text_proto["mat"])
        new_mat["id"] = str(uuid.uuid4()).upper()
        M.setdefault("texts", []).append(new_mat)
        new_tr = copy.deepcopy(text_proto["track"])
        new_tr["id"] = str(uuid.uuid4()).upper()
        for seg in new_tr["segments"]:
            seg["id"] = str(uuid.uuid4()).upper()
            seg["material_id"] = new_mat["id"]
            seg["extra_material_refs"] = []
        dc["tracks"].append(new_tr)

    # Clear legacy green-glow text_templates and bind text segments directly to clean pure-white bold texts
    M["text_templates"] = []
    first_text_id = M["texts"][0]["id"] if M.get("texts") else None

    for i, tr in enumerate(dc["tracks"]):
        for seg in tr["segments"]:
            seg["target_timerange"] = {"start": 0, "duration": d}
            if tr["type"] == "video":
                seg["source_timerange"] = {"start": a if kind.get(seg["material_id"]) == "video" else 0, "duration": d}
                if i == 0 and seg["clip"]["scale"]["x"] > 2.5:  # the blurred, zoomed background copy
                    seg["volume"] = 0.0
                if kind.get(seg["material_id"]) == "photo" and seg.get("clip", {}).get("transform", {}).get("y", 0.0) > 0.3:
                    # Move 비트's top logo to bottom band (y=-0.658) so it never overlaps the top hook and matches @optic_glass
                    seg["clip"]["transform"]["y"] = -0.6582
            elif tr["type"] == "text" and first_text_id:
                seg["material_id"] = first_text_id
                seg["extra_material_refs"] = []
                if isinstance(seg.get("clip"), dict):
                    seg["clip"]["scale"] = {"x": 1.0, "y": 1.0}
                    seg["clip"]["transform"] = {"x": 0.0, "y": 0.6575}

    if hook:
        text = "\n".join(hook)
        for mat in M.get("texts", []):
            _style_shorts_hook_mat(mat, text)
    dc["duration"] = d
    return dc


def build(slug: str, stage_dir: pathlib.Path = bl.STAGE_DIR, deploy: bool = True) -> dict:
    t0 = time.time()
    tpl = json.loads((TEMPLATE / "template.json").read_text(encoding="utf-8"))
    variant = "longform" if (SCENARIOS_DIR / f"{slug}_longform.json").exists() else "wide1"
    try:
        car = bl.Car(slug, variant=variant)  # the car's longform/wide1: its scenes, clips, subtitles and BGM
    except ValueError as e:  # its scenario breaks a role rule
        print(f"[검사 실패] {e}", flush=True)
        sys.exit(bl.CHECK_FAILED)
    print(f"[1/4] 롱폼 장면 클립 및 자막 소스 준비 ({car.title})")
    prepared = bl.prepare_media(car)
    source = source_video(car, prepared)
    from longform_common import get_mov_meta_cached
    source_us = get_mov_meta_cached(source)[0]
    parts = sections(car.scenario["scenes"], source_us / 1e6)
    print(f"[2/4] 숏폼 훅 문구 5종 (agy) · 구간 {[(n, a, d) for n, a, d in parts]}")
    hook = hooks(car)

    print("[3/4] CapCut 숏폼 초안 (타임라인 5개 전체 자막 포함)")
    name = f"hermes_{slug}_optic_shorts"
    stage = stage_dir / name
    shutil.rmtree(stage, ignore_errors=True)
    (stage / "Timelines").mkdir(parents=True)
    project = json.loads((TEMPLATE / "Timelines" / "project.json").read_text(encoding="utf-8"))
    now_us = int(time.time() * 1_000_000)
    project.update({"id": str(uuid.uuid4()).upper(), "create_time": now_us, "update_time": now_us})
    by_id = {t["id"]: t for t in project["timelines"]}
    tpl_dcs = [json.loads((TEMPLATE / "Timelines" / t["id"] / "draft_content.json").read_text(encoding="utf-8"))
               for t in tpl["timelines"]]
    text_proto = next((_extract_text_proto(d) for d in tpl_dcs if _extract_text_proto(d)), None)
    main_dc = None
    all_dcs = []
    for t, dc_raw, (chapter, a, d) in zip(tpl["timelines"], tpl_dcs, parts):
        if chapter not in hook:  # never ship the template's own (another car's) hook or leave a timeline without text
            raise KeyError(f"{car.media / 'shorts_hooks.json'}에 '{chapter}' 훅 문구가 없습니다 (파일을 지우면 agy가 다시 씁니다)")
        dc = fill_timeline(dc_raw, source, source_us, a, d, hook[chapter], text_proto=text_proto)
        all_dcs.append(dc)
        by_id[t["id"]].update({"name": chapter, "update_time": now_us})
        if t["id"] == tpl["main"]:
            main_dc = dc
    project["timelines"] = [t for t in project["timelines"] if not t.get("is_marked_delete")]
    (stage / "Timelines" / "project.json").write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
    # the meta of the longform template (a draft our builder writes and CapCut opens), with this draft's ids and media
    dm = rewrite_foreign_user_paths(json.loads((SCENARIOS_DIR / "templates" / "polestar4_optic" / "draft_meta_info.json").read_text(encoding="utf-8")))
    dm.update({"draft_id": str(uuid.uuid4()).upper(), "draft_name": name, "draft_root_path": to_fwd(DRAFT_ROOT),
               "draft_fold_path": f"{to_fwd(DRAFT_ROOT)}/{name}", "tm_duration": main_dc["duration"]})
    # Index materials across all 5 timelines so non-main sub-timeline assets are registered in draft_meta_info.json
    merged_dc = {"materials": {k: [m for sub in all_dcs for m in sub.get("materials", {}).get(k, [])]
                               for k in ("videos", "audios", "texts")}}
    populate_draft_materials(merged_dc, dm)  # sets local_material_id in all_dcs' materials, so they are written after it
    for t, dc in zip(tpl["timelines"], all_dcs):
        (stage / "Timelines" / t["id"]).mkdir()
        (stage / "Timelines" / t["id"] / "draft_content.json").write_text(json.dumps(dc, ensure_ascii=False, indent=2), encoding="utf-8")
    (stage / "draft_content.json").write_text(json.dumps(main_dc, ensure_ascii=False, indent=2), encoding="utf-8")
    (stage / "draft_meta_info.json").write_text(json.dumps(dm, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[4/4] 자막 포함 숏폼 5종 MP4 렌더링 (output/<slug>/shorts/)")
    shorts_mp4s = render_subtitles.render_shorts_mp4s(car, source, parts, hook)
    result = {name: {"staged_path": str(stage), "deployed_path": None,
                     "shorts": [[n, a, d] for n, a, d in parts],
                     "shorts_mp4s": [str(p) for p in shorts_mp4s]}}
    if deploy:  # the output check first: a draft that fails stays staged (exit CHECK_FAILED)
        bl.check_then_deploy(slug, "shorts", result)
    print(f"\n[COMPLETE in {round(time.time() - t0, 1)}s]\n  CapCut Drafts: {json.dumps(result, ensure_ascii=False)}")
    return result


def _selftest() -> None:
    assert utf16_len("신차 🚨") == 5
    assert _concat_line(pathlib.Path("a/21' gle/s.txt"), pathlib.Path("a/21' gle/lf_w00.mp4")) == "file 'lf_w00.mp4'\n"
    assert "{examples}" not in HOOK_ASK.format(car="X", max_len=HOOK_MAX, examples=hook_examples())
    sc = lambda i, a, d, r: {"id": i, "src": "x.mov", "start": a, "dur": d, "role": r}
    roled = [sc("w00", 0, 10, "exterior"), sc("w05", 10, 3, "card"), sc("w06", 13, 12, "before"),
             sc("w08", 25, 7, "after"), sc("w10", 32, 7, "split"), {"id": "w12", "role": "outro", "src": "outro", "start": 39, "dur": 7}]
    got = sections(roled, 39.0)
    assert got == [("비트", 0.0, 12.6), ("외관", 0, 10), ("시공 전", 13, 12), ("시공 후", 25, 7), ("전후 비교", 32, 7)], got
    wide1 = json.loads((SCENARIOS_DIR / "templates" / "opticglass_wide1" / "skeleton.json").read_text(encoding="utf-8"))["scenes"]
    assert sections(wide1, 50.6) == [("비트", 0.0, 12.6), ("외관", 0.0, 12.567), ("시공 전", 22.6, 10.0),
                                     ("시공 후", 32.6, 10.0), ("전후 비교", 42.6, 8.0)], sections(wide1, 50.6)
    if TEMPLATE.exists():  # every timeline (including 비트) filled: source range, hook text, muted background copy
        tpl = json.loads((TEMPLATE / "template.json").read_text(encoding="utf-8"))
        assert [t["name"] for t in tpl["timelines"]][0] == "비트" and len(tpl["timelines"]) == len(CHAPTERS)
        tpl_dcs = [json.loads((TEMPLATE / "Timelines" / t["id"] / "draft_content.json").read_text(encoding="utf-8"))
                   for t in tpl["timelines"]]
        text_proto = next((_extract_text_proto(d) for d in tpl_dcs if _extract_text_proto(d)), None)
        assert text_proto is not None
        for t, dc in zip(tpl["timelines"], tpl_dcs):
            out = fill_timeline(dc, pathlib.Path("src.mp4"), 70_000_000, 13.0, 12.0, ["첫 줄 🚨", "둘째 줄"], text_proto=text_proto)
            vsegs = [s for tr in out["tracks"] if tr["type"] == "video" for s in tr["segments"]]
            assert out["duration"] == 12_000_000 and all(s["target_timerange"]["duration"] == 12_000_000 for s in vsegs)
            src_segs = [s for s in vsegs if s["source_timerange"]["start"] == 13_000_000]
            assert src_segs, f"{t['name']}: no clip plays the source from 13 s"
            assert "회장님" not in json.dumps(out, ensure_ascii=False), "the template PC's user paths are rewritten"
            texts = out["materials"].get("texts", [])
            assert len(texts) >= 1, f"{t['name']}: missing hook subtitle text"
            for m in texts:
                c = json.loads(m["content"])
                assert c["text"] == "첫 줄 🚨\n둘째 줄" and c["styles"][0]["range"] == [0, utf16_len(c["text"])]
            if t["name"] == "비트":
                assert [s["volume"] for s in vsegs][:2] == [0.0, 1.0], "the blurred copy is muted, the front one plays"
    print("build_shorts self-check ok")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        _selftest()
    elif sys.argv[1] == "--extract":
        extract(sys.argv[2])
    else:
        build(sys.argv[1])
