"""Index of the vehicle folders under Google Drive '0.옵틱 광각' (and '1. 잔여 차량'), for picking the exact folder to
build from instead of guessing it from a typed name (one model can have a dozen dated job folders).

- fetch:  lists the folders with the gdrive CLI (read-only) and caches them in work/datasets/drive_vehicle_index.json
- parse:  splits a folder name into job no., model year, model, product tags and job date (a heuristic on free-typed
          names; the raw name is always kept and shown)
- links:  work/scenarios/drive_folders.json maps a pipeline slug to the folder it was built from
- status: per linked slug, whether its longform scenario exists and the last pipeline run's CapCut deploy and check result

usage: py drive_index.py [--refresh] [--link-existing] [--find <text>]
"""
import argparse
import json
import os
import pathlib
import re
from datetime import datetime

WORK_DIR = pathlib.Path(__file__).resolve().parent
from portable_paths import MEDIA_DIR, OUTPUT_DIR  # noqa: E402  (the data folder)
CACHE = WORK_DIR / "datasets" / "drive_vehicle_index.json"
LINKS = WORK_DIR / "scenarios" / "drive_folders.json"
ROOT_LABELS = {"1TT2v1sLCQdBIISjDucJPJGcineVIB76B": "0.옵틱 광각", "10p1isRRpD4uv447Q8qtVD9sPUQBbc6az": "1. 잔여 차량"}
# Product words in folder names -> tag. A folder can hold two jobs ("전사스, 옵틱"); a name with none is left untagged.
PRODUCTS = [("starposh", r"전사스"), ("osami", r"오사미"), ("opticglass", r"옵틱|광각|미러"), ("other", r"매트|PPF|썬쉐이드|블로그|썬팅|틴팅|모니터|블랙박스|광택|코팅|유리막|신차패키지")]
PRODUCT_KO = {"opticglass": "옵틱", "starposh": "전사스", "osami": "오사미", "other": "기타"}


# Brand -> how folder names write it (first match wins; motorcycles first, they reuse car brands' names).
BRANDS = [
    ("오토바이", r"오토바이|바이크|m1000rr|n-?max|할리|두카티|트라이엄프|트럼프타이거|야마하|가와사키|캔암|스즈키|버그만"),
    ("제네시스", r"제네시스|제니서스|genesis|g80|g90|gv70|gv80|eq900"), ("현대", r"현대|hyundai"), ("기아", r"기아|kia"),
    ("테슬라", r"테슬라|태슬라|tesla"), ("BMW", r"bmw|비엠"), ("벤츠", r"벤츠|메르세데스|mercedes|benz|마이바흐|maybach|amg"),
    ("아우디", r"아우디|audi"), ("포르쉐", r"포르쉐|porsche"), ("볼보", r"볼보|volvo"), ("폭스바겐", r"폭스바겐|volkswagen|\bvw\b"),
    ("렉서스", r"렉서스|lexus"), ("토요타", r"토요타|도요타|toyota"), ("혼다", r"혼다|honda"), ("닛산", r"닛산|nissan"),
    ("포드", r"포드|ford"), ("링컨", r"링컨|lincoln"), ("쉐보레", r"쉐보레|chevrolet"), ("캐딜락", r"캐딜락|케딜락|cadillac"),
    ("GMC", r"gmc"), ("지프", r"지프|jeep"), ("닷지", r"닷지|dodge"), ("람보르기니", r"람보르기니|lamborghini"),
    ("페라리", r"페라리|ferrari"), ("마세라티", r"마세라티|maserati"), ("벤틀리", r"벤틀리|bentley"),
    ("롤스로이스", r"롤스로이스|rolls"), ("랜드로버", r"랜드로버|레인지로버|land ?rover|range ?rover|디펜더"),
    ("미니", r"미니|\bmini\b"), ("푸조", r"푸조|peugeot"), ("시트로엥", r"시트로엥|시트로앵|citroen"), ("르노", r"르노|renault"),
    ("폴스타", r"폴스타|polestar"), ("BYD", r"byd"), ("KGM", r"쌍용|kgm|토레스|렉스턴"), ("맥라렌", r"맥라렌|mclaren"),
    ("애스턴마틴", r"애스턴|aston"), ("피아트", r"피아트|fiat"), ("인피니티", r"인피니티|infiniti"), ("리비안", r"리비안|rivian"),
    ("재규어", r"재규어|jaguar"), ("스바루", r"스바루|subaru"), ("로터스", r"로터스|lotus"),
]
# Folders often name only the model ("25 싼타페 MX5", "바야디 옵틱"): model word -> brand.
MODEL_BRAND = {
    "싼타페": "현대", "아반떼": "현대", "쏘나타": "현대", "그랜저": "현대", "투싼": "현대", "팰리세이드": "현대", "코나": "현대",
    "스타렉스": "현대", "스타리아": "현대", "캐스퍼": "현대", "포터": "현대", "아이오닉": "현대", "베뉴": "현대",
    "카니발": "기아", "쏘렌토": "기아", "스포티지": "기아", "모하비": "기아", "k5": "기아", "k7": "기아", "k8": "기아", "k9": "기아",
    "ev3": "기아", "ev5": "기아", "ev6": "기아", "ev9": "기아", "니로": "기아", "셀토스": "기아", "봉고": "기아",
    "모델": "테슬라", "사이버트럭": "테슬라", "카이엔": "포르쉐", "마칸": "포르쉐", "타이칸": "포르쉐", "파나메라": "포르쉐",
    "911": "포르쉐", "박스터": "포르쉐", "카레라": "포르쉐", "지바겐": "벤츠", "g바겐": "벤츠", "에스컬레이드": "캐딜락",
    "랭글러": "지프", "글래디에이터": "지프", "글래디에터": "지프", "루비콘": "지프", "시에나": "토요타", "알파드": "토요타",
    "트래버스": "쉐보레", "타호": "쉐보레", "콜로라도": "쉐보레", "익스플로러": "포드", "f150": "포드", "머스탱": "포드",
    "브롱코": "포드", "네비게이터": "링컨", "에비에이터": "링컨", "시에라": "GMC", "유콘": "GMC", "캐니언": "GMC",
    "챌린저": "닷지", "어코드": "혼다", "파일럿": "혼다", "오딧세이": "혼다", "알티마": "닛산", "패트롤": "닛산",
    "바야디": "르노", "아르카나": "르노", "qm6": "르노", "xm3": "르노", "sm6": "르노", "토레스": "KGM", "렉스턴": "KGM",
    "우라칸": "람보르기니", "골프": "폭스바겐", "노틸러스": "링컨", "mkc": "링컨", "트랜짓": "포드", "볼트": "쉐보레",
    "하이랜더": "토요타", "gle": "벤츠", "gls": "벤츠", "glc": "벤츠", "gla": "벤츠", "glb": "벤츠", "cls": "벤츠",
    "eqs": "벤츠", "eqe": "벤츠", "eqb": "벤츠",
}
# one spelling per model, so its folders sit under one button
MODEL_ALIASES = {"소나타": "쏘나타", "소렌토": "쏘렌토", "쏘랜토": "쏘렌토", "그랜져": "그랜저", "글래디에터": "글래디에이터"}
_MODEL_PREFIX = r"^(더\s?뉴|디\s?올\s?뉴|올\s?뉴|신형|뉴|그랜드)\s*"  # 그랜드 스타렉스 -> 스타렉스


def group_of(row: dict) -> tuple:
    """(brand, model) for the brand -> model -> folder browser. Unknown brands go under 기타; the model is the first
    word after the brand ("현대 더뉴 싼타페 MX5" -> 싼타페, "테슬라 모델x" -> 모델 X, "BMW X5 40i" -> X5)."""
    text = row["model"]
    brand = next((b for b, rx in BRANDS if re.search(rx, row["name"], re.I)), None)
    for _, rx in BRANDS:
        text = re.sub(rx, " ", text, flags=re.I)
    text = re.sub(_MODEL_PREFIX, "", text.strip())
    text = re.sub(r"사이버\s+트럭", "사이버트럭", text)
    text = re.sub(r"^\d{2}\s+(?=\S)", "", text)  # a model year written after the brand ("벤츠 21 GLE")
    tesla = re.match(r"모델\s*([A-Za-z0-9])", text)
    m = re.match(r"\d+\s?시리즈|[A-Za-z]{1,2}\s?클래스|[A-Za-z]페이스|[가-힣]+(?=[A-Za-z0-9]|\s|$)|[A-Za-z0-9]+|[가-힣]+", text)
    model = f"모델 {tesla.group(1).upper()}" if tesla else (m.group(0).replace(" ", "") if m else "")
    model = model.upper() if re.fullmatch(r"[A-Za-z0-9]+", model or "-") else model
    model = re.sub(r"^([a-z]{1,2})(클래스)$", lambda c: c.group(1).upper() + c.group(2), model)  # s클래스 -> S클래스
    model = MODEL_ALIASES.get(model, model)
    if not brand:
        brand = MODEL_BRAND.get(model.lower()) or MODEL_BRAND.get(model.split(" ")[0].lower()) or "기타"
    trim = re.fullmatch(r"([A-Z]{1,3})\d{3}[A-Z]?", model)  # Benz trims: GLE450 -> GLE, E300 -> E
    if brand == "벤츠" and trim:
        model = trim.group(1)
    if brand == "벤츠" and re.fullmatch(r"[A-Z]", model):
        model += "클래스"
    if model.isdigit() and brand != "기타":  # 폴스타 4, 페라리 812, 푸조 208
        model = f"{brand} {model}"
    if brand == "테슬라" and re.fullmatch(r"[3SXY]", model):
        model = f"모델 {model}"
    return brand, model or "기타"


def parse_name(name: str) -> dict:
    n = name.strip()
    job = re.match(r"^(\d{1,3})\.\s*", n)
    rest = n[job.end():] if job else n
    # model year: "23년식" / "2026년식" / "2025년" anywhere, else a leading two-digit number ("24 현대 싼타페")
    year = None
    y = re.search(r"(?<!\d)(20\d{2}|\d{2})년(식)?(\s*\d{1,2}월)?", rest)
    if y:
        year, rest = y.group(1)[-2:], rest[:y.start()] + " " + rest[y.end():]
    else:
        y = re.match(r"^(?:20)?(\d{2})(?=\s|[가-힣A-Za-z])", rest)
        if y:
            year, rest = y.group(1), rest[y.end():]
    date = re.search(r"\[\s*((?:\d{2}\.)?\d{2}\.\d{2})|-\s*((?:\d{2}\.)?\d{2}\.\d{2})\s*$|\(((?:\d{2}\.)?\d{2}\.\d{2})\)|\s(\d{2}\.\d{2})\s*$", rest)
    tags = [p for p, rx in PRODUCTS if re.search(rx, n, re.I)]
    # the model is what comes before the first product word; job codes, dates and copy suffixes follow it
    head = rest[:date.start()] if date else rest
    product_word = r"옵틱|광각|광가|사이드\s?미러|미러|전사스|오사미"
    model = re.split(product_word + r"|\[|\(|\s-\s|\s-$", head)[0]
    if not model.strip(" -."):  # the name starts with a product word or a bracket ("옵틱 25 렉서스 ...", "(X)26 ...")
        model = re.sub(product_word + r"|\([^)]*\)|\[[^\]]*\]", " ", head)
        model = re.sub(r"^\s*\d{2}(?=\s|[가-힣A-Za-z])", " ", model)
    model = re.sub(r"(?<!\d)20\d{2}(?!\d)|[\]),+]", " ", model)
    return {
        "job_no": job.group(1) if job else None,
        "year": year,
        "model": re.sub(r"\s+", " ", model).strip(" -.") or n,
        "products": tags,
        "date": next((g for g in date.groups() if g), None) if date else None,
    }


MEDIA_SUFFIXES = {".mov", ".mp4", ".jpg", ".jpeg", ".png"}


def _write_json(path: pathlib.Path, data) -> None:
    """Write to a temp file and swap it in, so an interrupted write never leaves an empty or half file."""
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def fetch() -> list:
    from gdrive_pipeline import GDRIVE_OPTIC_SUBROOT_IDS, run_gdrive_cli  # only fetching needs the Drive CLI
    rows = []
    for root_id in GDRIVE_OPTIC_SUBROOT_IDS:
        items = json.loads(run_gdrive_cli(["readonly", "ls", root_id, "--max", "1000", "--json"]))
        for it in items if isinstance(items, list) else items.get("files", []):
            if "folder" in it.get("mimeType", ""):
                rows.append({"id": it["id"], "name": it["name"].strip(), "root": ROOT_LABELS.get(root_id, root_id),
                             "modified": (it.get("modifiedTime") or "")[:10], **parse_name(it["name"])})
    rows.sort(key=lambda r: r["modified"], reverse=True)
    _write_json(CACHE, {"fetched_at": datetime.now().isoformat(timespec="seconds"), "folders": rows})
    return rows


def load(refresh: bool = False) -> tuple:
    """(rows, fetched_at). Uses the cache unless refresh is asked for or there is none."""
    if refresh or not CACHE.exists():
        rows = fetch()
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    return data["folders"], data["fetched_at"]


def links() -> dict:
    return json.loads(LINKS.read_text(encoding="utf-8")) if LINKS.exists() else {}


def drive_path(row: dict) -> str:
    """The folder's Drive path ("0.옵틱 광각/11 아우디 tts 로드스터 옵틱 [25.11.14]"), each part made a legal Windows
    folder name (no <>:"/\\|?*, no trailing dot or space)."""
    return "/".join(re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", p).rstrip(" .") or "_" for p in (row["root"], row["name"]))


def media_dir(slug: str) -> pathlib.Path:
    """Where a car's media lives: <data>/media/<its Drive path>/ (gdrive_raw/, thumb/, thumb_picks.json), or
    <data>/media/<slug>/ for the cars downloaded before the Drive path was kept (portable_paths.MEDIA_DIR)."""
    return MEDIA_DIR / (links().get(slug, {}).get("media") or slug)


_RR = ("g kk n d tt r m b pp s ss _ j jj ch k t p h".split(),  # Revised Romanization, syllable by syllable
       "a ae ya yae eo e yeo ye o wa wae oe yo u wo we wi yu eu ui i".split(),
       ["", *"k k k n n n t l k m l l l p l m p p t t ng t t k t p t".split()])


def _ascii(text: str) -> str:
    """Hangul romanized, letters/digits kept, the rest dropped: "아우디" -> "audi", "싼타페" -> "ssantape"."""
    out = []
    for ch in text.lower():
        i = ord(ch) - 0xAC00
        out.append((_RR[0][i // 588].strip("_") + _RR[1][i // 28 % 21] + _RR[2][i % 28]) if 0 <= i < 11172
                   else ch if ch.isascii() and ch.isalnum() else " ")
    return "_".join("".join(out).split())


def brand_ascii(brand: str) -> str:
    """The brand's own Latin spelling from BRANDS ("현대" -> "hyundai", "벤츠" -> "mercedes"), else romanized."""
    rx = next((rx for b, rx in BRANDS if b == brand), "")
    return next((w for w in rx.replace(r"\b", "").replace(" ?", "").split("|") if re.fullmatch(r"[a-z]+", w)), None) or _ascii(brand)


def auto_slug(row: dict) -> str:
    """The id a Drive folder gets for file and CapCut draft names, from its brand, model and job no.
    ("11 아우디 tts 로드스터 옵틱 [25.11.14]" -> "audi_tts_251114": 11 is its model year, so the job date); _2, _3 ... when another folder has it."""
    brand, model = group_of(row)
    parts = [] if brand == "기타" else [brand_ascii(brand)]
    parts += [_ascii(model.removeprefix(brand)) if model != "기타" else "", row.get("job_no") or (row.get("date") or "").replace(".", "")]
    base = "_".join(p for p in parts if p)[:26].strip("_") or "car"
    base = base if base[0].isalpha() else f"car_{base}"
    data, slug, n = links(), base, 1
    while slug in data and data[slug]["folder_id"] != row["id"]:
        n += 1
        slug = f"{base}_{n}"
    return slug


def link(slug: str, row: dict) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,30}", slug):
        raise ValueError(f"slug must be lowercase letters/digits/_ (got {slug!r})")
    data = links()
    other = next((s for s, v in data.items() if v["folder_id"] == row["id"] and s != slug), None)
    if other:
        raise ValueError(f"folder already linked to {other}")
    if slug in data and data[slug]["folder_id"] != row["id"]:
        raise ValueError(f"{slug} is already linked to {data[slug]['folder_name']}")
    data[slug] = {"folder_id": row["id"], "folder_name": row["name"], "car_name": row["model"]}
    if not (MEDIA_DIR / slug).exists():  # a car already downloaded to media/<slug> stays there
        data[slug]["media"] = drive_path(row)
    _write_json(LINKS, data)


CAR_TITLES = {  # thumbnail/intro names for the cars that came before the GUI name field
    "cybertruck": "2026 테슬라 사이버트럭",
    "santafe": "현대 싼타페",
    "bmwx5": "BMW X5",
    "sealion7": "BYD 씨라이언7",
}


def title(slug: str) -> str:
    """The car name on the thumbnail and in the lines: the GUI field, else the old fixed name, else the Drive model."""
    v = links().get(slug, {})
    return v.get("title") or CAR_TITLES.get(slug) or v.get("car_name") or slug


def set_title(slug: str, text: str) -> None:
    data = links()
    if slug not in data:
        raise ValueError(f"{slug} is not linked to a Drive folder")
    data[slug]["title"] = text.strip()
    _write_json(LINKS, data)


def status(slug: str) -> dict:
    manifest = OUTPUT_DIR / slug / "package_manifest.json"
    m = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    st = m.get("stage2_video_outputs") or {}
    if not st or (st.get("capcut_deploy") or {}).get("status") in (None, "not_built"):
        st = (m.get("extra_drafts") or {}).get(f"hermes_{slug}_optic_wide1") or st
    raw = media_dir(slug) / "gdrive_raw"
    return {
        "scenario": any((WORK_DIR / "scenarios" / f"{slug}_{v}.json").exists() for v in ("longform", "wide1")),  # build_longform.py builds any car with one
        "media": sum(1 for p in raw.iterdir() if p.suffix.lower() in MEDIA_SUFFIXES) if raw.exists() else 0,  # not .part leftovers
        "ran": manifest.exists(),  # a pipeline run finished (it writes the manifest last)
        "deploy": (st.get("capcut_deploy") or {}).get("status"),
        "check": st.get("output_check"),
        # "needs_photo_pick" while agy has not produced photos that pass its check; a manifest from before that counts as not done
        "thumb": m.get("stage3_thumbnail_status", "needs_photo_pick" if m else None),
    }


def missing_footage(slug: str) -> list:
    """Source clips the car's scenarios (longform, and the wide1 template edit) use that are not in its gdrive_raw (all
    of them on a PC set up from the light release zip, which leaves the .MOV files out); [] without a scenario."""
    import longform_common as lc
    files = [WORK_DIR / "scenarios" / f"{slug}_{v}.json" for v in ("longform", "wide1")]
    raw = media_dir(slug) / "gdrive_raw"
    scenes = [s for f in files if f.exists() for s in json.loads(f.read_text(encoding="utf-8"))["scenes"]]
    srcs = {s["src"] for s in scenes if s["src"] != "outro"} | {s["split"]["src_after"] for s in scenes if s.get("split", {}).get("src_after")}
    return sorted(s for s in srcs if not lc.resolve_scene_src(raw, s).exists())


def status_text(slug: str) -> str:
    s = status(slug)
    pick = " · 썸네일 AI 미완료" if s["thumb"] == "needs_photo_pick" else ""
    if not s["scenario"]:  # 롱폼 makes one (make_scenario.py) unless an earlier try found too little footage
        short = (media_dir(slug) / "scenario_short.json").exists()
        return f"{'영상 부족' if short else '시나리오 자동 생성 전'} · 미디어 {s['media']}" + pick
    deploy = {"deployed": "배포됨", "held": "배포 보류", "not_built": "미빌드"}.get(s["deploy"], "기록 없음")
    return deploy + (" · 검사 실패" if s["check"] == "fail" else "") + pick


def find(rows: list, text: str, products: set = None) -> list:
    """Every folder whose raw or parsed name contains all the words of text (case-insensitive)."""
    words = text.lower().split()
    out = []
    for r in rows:
        if products and not (set(r["products"]) & products or not r["products"]):
            continue
        hay = f"{r['name']} {r['model']} {' '.join(PRODUCT_KO[p] for p in r['products'])}".lower().replace(" ", "")
        if all(w.replace(" ", "") in hay for w in words):
            out.append(r)
    return out


def link_existing(rows: list) -> dict:
    """Links slugs that already have a builder to the Drive folder whose files best match their local gdrive_raw."""
    from gdrive_pipeline import run_gdrive_cli
    keywords = {"cybertruck": "사이버", "santafe": "싼타페", "bmwx5": "x5", "sealion7": "라이언"}
    done = {}
    for slug, kw in keywords.items():
        raw = MEDIA_DIR / slug / "gdrive_raw"
        if slug in links() or not raw.exists():
            continue
        local = {p.name for p in raw.iterdir() if p.suffix.upper() in (".MOV", ".MP4", ".JPG", ".JPEG", ".PNG", ".HEIC")}
        best, best_n = None, 0
        for r in find(rows, kw):
            names = {it["name"] for it in json.loads(run_gdrive_cli(["readonly", "ls", r["id"], "--max", "500", "--json"]))}
            if len(local & names) > best_n:
                best, best_n = r, len(local & names)
        if best and best_n >= 3:
            link(slug, best)
            done[slug] = (best["name"], best_n)
    return done


def _selftest():
    p = parse_name("61.26 BYD 씨라이언7 광각 [26.04.15]")
    assert (p["job_no"], p["year"], p["model"], p["products"], p["date"]) == ("61", "26", "BYD 씨라이언7", ["opticglass"], "26.04.15"), p
    p = parse_name("24 현대 싼타페 옵틱 - 02.15")
    assert (p["year"], p["model"], p["date"]) == ("24", "현대 싼타페", "02.15"), p
    p = parse_name("120. 현대 2026년식 싼타페mx5 광각미러 [26.07.21]")
    assert (p["job_no"], p["year"], p["model"]) == ("120", "26", "현대 싼타페mx5"), p
    p = parse_name("38. 26 테슬라 사이버 트럭 전사스, 옵틱")
    assert p["products"] == ["starposh", "opticglass"] and p["model"] == "테슬라 사이버 트럭", p
    p = parse_name("06 포르쉐 박스터 옵틱 822 - 02.02")
    assert (p["model"], p["date"]) == ("포르쉐 박스터", "02.02"), p
    assert parse_name("18 도요타 시에나")["products"] == []
    assert parse_name("14 피아트 500 옵틱")["model"] == "피아트 500"
    assert parse_name("19 포르쉐 카레라 911 옵틱 823 - 09.11")["model"] == "포르쉐 카레라 911"
    assert parse_name("42. 09 포르쉐 997.2 옵틱 [26.03.23]")["model"] == "포르쉐 997.2"
    p = parse_name("142. 23년식 BMW x7 흰색 스커트 [26.08.05]")
    assert (p["year"], p["model"], p["date"]) == ("23", "BMW x7 흰색 스커트", "26.08.05"), p
    p = parse_name("144. BMW 25년식 X7 흰색 광각미러")
    assert (p["year"], p["model"]) == ("25", "BMW X7 흰색"), p
    p = parse_name("10 혼다 어코드 옵틱(22.08.26)")
    assert (p["model"], p["date"]) == ("혼다 어코드", "22.08.26"), p
    assert parse_name("21 링컨 네비게이터 옵틱 [12.19, No.5040-1]")["date"] == "12.19"
    assert (parse_name("84. 2022 페라리 296 GTB 퓨어그래스")["year"], parse_name("84. 2022 페라리 296 GTB 퓨어그래스")["model"]) == ("22", "페라리 296 GTB 퓨어그래스")
    rows = [{"name": "24 현대 싼타페 옵틱 - 02.15", **parse_name("24 현대 싼타페 옵틱 - 02.15")},
            {"name": "24 BMW X5 전사스 - 07.23", **parse_name("24 BMW X5 전사스 - 07.23")}]
    assert len(find(rows, "싼타페")) == 1 and len(find(rows, "bmw x5")) == 1 and find(rows, "x5", {"opticglass"}) == []
    row = lambda name, root="0.옵틱 광각": {"id": name, "name": name, "root": root, **parse_name(name)}
    assert auto_slug(row("11 아우디 tts 로드스터 옵틱 [25.11.14]")) == "audi_tts_251114"
    assert auto_slug(row("24 현대 싼타페 옵틱 - 02.15")) == "hyundai_ssantape_0215"
    assert auto_slug(row("61.26 BYD 씨라이언7 광각 [26.04.15]")) == "byd_ssiraieon_61"
    assert auto_slug(row("120. 테슬라 모델Y 옵틱")) == "tesla_model_y_120"
    assert auto_slug(row("24 벤츠 옵틱 [25.03.02]")) == "mercedes_250302"
    assert drive_path(row('03. 벤츠 S클래스: 옵틱?. ')) == "0.옵틱 광각/03. 벤츠 S클래스_ 옵틱_"


if __name__ == "__main__":
    _selftest()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--link-existing", action="store_true")
    ap.add_argument("--find")
    a = ap.parse_args()
    rows, fetched = load(a.refresh)
    print(f"{len(rows)} folders (fetched {fetched}) -> {CACHE}")
    if a.link_existing:
        print("linked:", link_existing(rows))
    for slug, v in links().items():
        print(f"  {slug:12} {v['folder_name']}  [{status_text(slug)}]")
    if a.find:
        for r in find(rows, a.find):
            print(f"  {r['modified']}  {r['name']}  ({r['id']})")
