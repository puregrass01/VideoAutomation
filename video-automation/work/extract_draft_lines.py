"""Collects every on-screen line from the local CapCut drafts into work/datasets/draft_lines.jsonl, as examples for
LLM-written scenario lines. Each record carries the scenario line fields (start, dur, fc_pos, size, color, stroke_w,
shadow, font, font_style, text) plus where it came from (draft, timeline, scene) and tags: brand, format (longform /
shortform), part (role in the video). Brand and part are keyword heuristics; part_rule says which rule fired.
fc_pos/size use the longform calibration (CapCut -> scenario px), so they are approximate on 9:16 and 4:5 canvases.
Encrypted drafts are skipped and listed, never decrypted.
usage: py extract_draft_lines.py
"""
import collections
import json
import pathlib
import re

from extract_template import text_slot
from longform_common import CC_STROKE_PER_FC_RATIO
from portable_paths import DRAFT_ROOT

OUT = pathlib.Path(__file__).resolve().parent / "datasets" / "draft_lines.jsonl"
# First match wins, tested on the draft name plus all its lines; the drafts also hold other products' videos.
BRAND_RULES = [
    ("other", r"TOP\s?\d|꿀템|코일\s?매트"),  # multi-product listicles (mats, cushions, prices)
    ("starposh", r"사이드\s?스텝|STAR\s?POSH|STAPOSH|승하차|점프해서"),
    ("blacksound", r"나카미치|Nakamichi|스피커|블랙사운드"),
    ("osami", r"오토\s?사이드\s?미러|오사미"),
    ("opticglass", r"광각|옵틱|OPTIC|사이드\s?미러|순정\s?미러|시야|사각지대"),
]
# First match wins, tested on one line. Before them: a Latin-only line early in the video is the title (model name)
# and a "<model> x OpticGlass" card is the ending. Lines no rule matches get a part from their position in the video.
# Strong complaint words go before solution (불편한 contains 편한); weak ones after it (위험을 지워버리는 = solution).
PART_RULES = [
    ("compare", r"^(시공|설치)\s?(전|후)$|^(Before|After)$|^(순정|광각)\s?미러(보다|와|vs|\s*$)|(설치|시공|교체)\s?(전|후)$|이렇게 보니|다르죠"),
    ("section", r"꼭 필요한 이유|BY OPTICGLASS|^(첫|두|세|네|다섯)\s?번째$"),
    ("cta", r"문의|구매|스토어|링크|상담|예약|주목|직접 장착|할인|구독|지금 바로|^[\d.,]+\s?원$|(하|해|보|험하)세요[.!]*$"),
    ("problem", r"불편|불안|힘들|힘든|부담|허전|엉거주춤|아쉬|피곤|때문에|높이\s?차이|승하차\s?높이|못하"),
    ("solution", r"옵틱글래스|광각미러로|광각미러는|교체|장착|해결|넓어|넓게|넓은 시야|확장|확보|안심|안전하게|(?<!불)편리|(?<!불)편안|(?<!불)편한"
                 r"|해소|선택|달라|눈이 되어|바꿨|바꿔|괜찮|지워|없애|걱정\s?(도|하지|없|NO)"),
    ("problem", r"좁|사각지대|위험|어렵|어려|답답|두려|무서|사고|못해|않아|않는|않던|안 보|죽|피로|고개|멀게"),
]
# Copies and aspect variants of one edit ("-복사", "-복사 (1)", "(4대5)"/"(9대16)") share their lines; keep them once.
# A bare " (1)" is not a copy: CapCut gives that name to a new, different edit too ("0720" vs "0720 (1)").
FAMILY = re.compile(r"(-복사( \(\d+\))?)?(\((4대5|9대16)\))?$")


def brand_of(draft, texts):
    joined = "\n".join([draft, *texts])
    return next((b for b, rx in BRAND_RULES if re.search(rx, joined, re.I)), "other")


def part_of(text, start, duration):
    pos = start / duration if duration else 0.0
    if (start < 3 or pos < 0.15) and len(text) <= 40 and re.search(r"[A-Za-z]", text) and not re.search(r"[가-힣]{2}|\sx\s", text):
        return "title", "title"
    if re.search(r"\n\s*x\s*\n", text, re.I):
        return "ending", "keyword"
    for part, rx in PART_RULES:
        if re.search(rx, text.replace("\n", " "), re.I):
            return part, "keyword"
    return ("hook" if pos < 0.12 else "ending" if pos > 0.85 else "body"), "position"


def timeline_lines(dc):
    """(segment, text material, kind) for every text segment; a text_template segment yields each of its texts."""
    M = dc.get("materials", {})
    texts = {t["id"]: t for t in M.get("texts", [])}
    tmpls = {t["id"]: t for t in M.get("text_templates", [])}
    for tr in dc.get("tracks", []):
        if tr.get("type") != "text":
            continue
        for seg in tr["segments"]:
            if seg["material_id"] in texts:
                yield seg, texts[seg["material_id"]], texts[seg["material_id"]].get("type", "text")
            for res in tmpls.get(seg["material_id"], {}).get("text_info_resources", []):
                if res.get("text_material_id") in texts:
                    yield seg, texts[res["text_material_id"]], "text_template"


def font_name(mat, style):
    """CapCut writes the title "none" for fonts it names only by file; en.ttf is its default system font and an effect
    cache's font.ttf has no name."""
    title = next((t for t in [mat.get("font_title")] + [f.get("title") for f in mat.get("fonts") or []] if t and t != "none"), None)
    stem = pathlib.Path(style.get("font", {}).get("path") or mat.get("font_path") or "").stem
    return title or {"en": "CapCut default", "font": None, "": None}.get(stem, stem)


def record(dc, seg, mat, kind):
    try:
        content = json.loads(mat.get("content") or "")
    except ValueError:  # a few older materials keep plain text (or nothing) instead of the JSON content
        content = {"text": mat.get("content") or "", "styles": [{}]}
        mat = {**mat, "content": json.dumps(content, ensure_ascii=False)}
    w, h = dc["canvas_config"]["width"], dc["canvas_config"]["height"]
    row = text_slot(seg, mat, w, h, False)  # timing, position, size, colour; the style fields are replaced below
    style = (content.get("styles") or [{}])[0]
    strokes = style.get("strokes") or []
    fx = {e["id"]: e for e in dc["materials"].get("effects", []) if e.get("type") == "text_effect"}
    fills = collections.Counter()  # two-tone lines: the colour covering the most characters
    for st in content.get("styles") or []:
        rgb = st.get("fill", {}).get("content", {}).get("solid", {}).get("color")
        if rgb and len(st.get("range") or []) == 2:
            fills["#%02X%02X%02X" % tuple(round(c * 255) for c in rgb[:3])] += st["range"][1] - st["range"][0]
    if len(fills) > 1:
        row["color"] = fills.most_common(1)[0][0]
    row.update({
        "stroke_w": round(strokes[0]["width"] * row["size"] / CC_STROKE_PER_FC_RATIO, 1) if strokes else 0.0,
        "shadow": bool(style.get("shadows") or mat.get("has_shadow")),
        "font": font_name(mat, style),
        "font_style": "",
        "effect": next((fx[r].get("name") for r in seg.get("extra_material_refs", []) if r in fx), None),
        "kind": kind,
    })
    return row


def extract():
    rows, seen, encrypted = [], set(), []
    for d in sorted(p for p in DRAFT_ROOT.iterdir() if p.is_dir() and not p.name.startswith(("hermes_", "pycapcut_", "."))):
        family = FAMILY.sub("", d.name)
        draft_rows, enc = [], 0
        for f in sorted((d / "Timelines").glob("*/draft_content.json")) + [d / "draft_content.json"]:
            if not f.exists() or f.stat().st_size < 200:
                continue
            raw = f.read_bytes()
            if raw[:1] != b"{":
                enc += 1
                continue
            dc = json.loads(raw)
            duration = dc.get("duration", 0) / 1e6
            cuts = []  # clip starts on every video track (edits spread clips over several); cuts < 0.2 s apart merged
            for c in sorted({0.0} | {s["target_timerange"]["start"] / 1e6 for t in dc.get("tracks", []) if t.get("type") == "video" for s in t["segments"]}):
                if not cuts or c - cuts[-1] >= 0.2:
                    cuts.append(c)
            for seg, mat, kind in timeline_lines(dc):
                r = record(dc, seg, mat, kind)
                if not r["text"] or (family, r["text"], r["start"]) in seen:
                    continue
                seen.add((family, r["text"], r["start"]))
                w, h = dc["canvas_config"]["width"], dc["canvas_config"]["height"]
                draft_rows.append({
                    "draft": d.name, "timeline": f.parent.name if f.parent.name != d.name else None,
                    "format": "shortform" if h > w else "longform", "aspect": "9:16" if h / w > 1.6 else "4:5" if h > w else "16:9",
                    "duration": round(duration, 3), "scene": sum(c <= r["start"] + 1e-6 for c in cuts) - 1, "scenes": len(cuts),
                    **r,
                })
        if enc and not draft_rows:
            encrypted.append(d.name)
        brand = brand_of(d.name, [r["text"] for r in draft_rows])
        for r in draft_rows:
            r["part"], r["part_rule"] = part_of(r["text"], r["start"], r["duration"])
            rows.append({"brand": brand, **r})
    families = collections.defaultdict(set)  # lines every template of the family repeats ("시공 전", section titles)
    for r in rows:
        families[r["text"]].add(FAMILY.sub("", r["draft"]))
    for r in rows:
        r["common_drafts"] = len(families[r["text"]])
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return rows, encrypted


def _selftest():
    assert brand_of("전사스", ["사이드 스텝이 없어 허전한 하부"]) == "starposh"
    assert brand_of("x", ["오토 사이드 미러 시공"]) == "osami"
    assert brand_of("x", ["옵틱글래스 광각미러로 한방에 해결!"]) == "opticglass"
    assert brand_of("0720 (1)", ["후기좋은 차량 꿀템", "옵틱글래스 광각미러"]) == "other"
    assert part_of("높은 높이로 인해 불편한 승하차", 20.0, 60.0) == ("problem", "keyword")
    assert part_of("위험을 단숨에 지워버리는", 20.0, 60.0) == ("solution", "keyword")
    assert part_of("PORSCHE", 5.4, 42.4) == ("title", "title")
    assert part_of("폴스타4 타면서 / 야간에 디밍 때문에", 1.0, 24.0)[0] != "title"
    assert part_of("Porsche 997.2\nx\nOpticGlass Wide-Angle Side Mirror", 56.7, 76.0) == ("ending", "keyword")
    assert part_of("시공 전", 31.6, 41.5) == ("compare", "keyword")
    assert part_of("운행 시 차선 확인 어려움!", 16.5, 41.5) == ("problem", "keyword")
    assert part_of("옵틱글래스 광각미러로 한방에 해결!", 26.2, 41.5) == ("solution", "keyword")
    assert part_of("BMW ACEMAN", 0.5, 42.6) == ("title", "title")
    assert part_of("드라이버들의 드림카 포르쉐", 0.5, 30.0) == ("hook", "position")
    assert part_of("광각미러 설치 전", 20.0, 60.0) == ("compare", "keyword")
    assert part_of("광각미러가 꼭 필요한 이유", 12.1, 41.5) == ("section", "keyword")
    assert part_of("고개 돌리기 어렵죠?", 20.0, 60.0) == ("problem", "keyword")
    assert part_of("사각지대 해소 가능한 넓은 시야,", 29.3, 41.5) == ("solution", "keyword")
    assert FAMILY.sub("", "가족1(9대16)") == FAMILY.sub("", "가족1(4대5)") == "가족1" and FAMILY.sub("", "0728-복사 (1)") == "0728" != FAMILY.sub("", "0720 (1)")


if __name__ == "__main__":
    _selftest()
    rows, encrypted = extract()
    count = lambda k: dict(collections.Counter(r[k] for r in rows).most_common())
    print(f"{len(rows)} lines from {len({r['draft'] for r in rows})} drafts -> {OUT}")
    print("unique texts:", len({r["text"] for r in rows}), "| brand:", count("brand"), "| format:", count("format"))
    print("part:", count("part"), "| part_rule:", count("part_rule"))
    print("skipped (encrypted):", encrypted)
