"""End-to-End Unified Automation Pipeline:
Google Drive Ingest -> AI/Heuristic Slot Classification -> Stage 2 (Video Template) + Stage 3 (1280x720 Thumbnail)

Eliminates manual file path passing between Stage 1 (Collect Media), Stage 2 (Video Edit),
and Stage 3 (Thumbnail Generation).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

WORK_DIR = pathlib.Path(__file__).resolve().parent
ROOT_DIR = WORK_DIR.parent
REPO_ROOT = ROOT_DIR.parent

sys.path.insert(0, str(WORK_DIR))
import drive_index  # noqa: E402
from longform_common import atomic_write_json  # noqa: E402
from preflight_check import run_preflight, validate_media_paths  # noqa: E402
from portable_paths import find_gdrive_cmd, ASSETS_DIR, DRAFT_ROOT, OUTPUT_DIR  # noqa: E402

GDRIVE_CMD = find_gdrive_cmd()
THUMBNAIL_SCRIPT = (
    REPO_ROOT / "옵틱글래스_유튜브_썸네일" / "template" / "generate_thumbnail.py"
)
_LOCAL_LOGOS = pathlib.Path(r"C:\Users\bssho\Downloads\300+ Car Logos & Brand Stories _ CarLogos")
CAR_LOGOS_ROOT = _LOCAL_LOGOS if _LOCAL_LOGOS.exists() else (ASSETS_DIR / "logos")


def extract_gdrive_id(folder_arg: str) -> str:
    """Extract Google Drive Folder ID from a URL or raw ID string."""
    m = re.search(r"/folders/([a-zA-Z0-9_-]+)", folder_arg)
    if m:
        return m.group(1)
    m_id = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", folder_arg)
    if m_id:
        return m_id.group(1)
    return folder_arg.strip()


def run_gdrive_cli(args: List[str]) -> str:
    """Run the bundled gdrive CLI and return stdout."""
    if not GDRIVE_CMD.exists():
        raise FileNotFoundError(f"gdrive CLI not found at {GDRIVE_CMD}")
    cmd = ["cmd.exe", "/c", str(GDRIVE_CMD)] + args
    res = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        # the GUI (pythonw, no console) calls this for the Drive table: without the flag every call opens a terminal
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if res.returncode != 0:
        raise RuntimeError(
            f"gdrive command failed ({' '.join(args)}):\n{res.stderr or res.stdout}"
        )
    return res.stdout if res.stdout.strip() else res.stderr


def check_gdrive_logged_in() -> bool:
    """Return True if gdrive CLI is authenticated."""
    try:
        out = run_gdrive_cli(["auth", "status"])
        return "Logged in" in out and "Not logged in" not in out
    except Exception:
        return False


GDRIVE_OPTIC_ROOT_ID = "1TT2v1sLCQdBIISjDucJPJGcineVIB76B"  # 이전 자료 > 0.옵틱 광각 (Google Drive vehicle folder index)
GDRIVE_OPTIC_SUBROOT_IDS = [
    "1TT2v1sLCQdBIISjDucJPJGcineVIB76B",  # 0.옵틱 광각
    "10p1isRRpD4uv447Q8qtVD9sPUQBbc6az",  # 1. 잔여 차량
]


def find_gdrive_folder_by_name(folder_name: str) -> Optional[str]:
    """Resolve a vehicle folder by name in the '0.옵틱 광각' index, then Drive-wide; folders only. One model often has
    several dated job folders (and two can share a name), so more than one match stops with the candidates instead of
    taking the first: pick one and pass its ID with --gdrive-folder (or use the GUI's vehicle table)."""
    q = folder_name.strip().lower()

    def folders(items):
        return [it for it in items if "folder" in it.get("mimeType", "") and q in it.get("name", "").lower()]

    matches = []
    for root_id in GDRIVE_OPTIC_SUBROOT_IDS:
        idx_data = json.loads(run_gdrive_cli(["readonly", "ls", root_id, "--max", "1000", "--json"]))
        matches += folders(idx_data if isinstance(idx_data, list) else idx_data.get("files", idx_data.get("items", [])))
    if not matches:
        data = json.loads(run_gdrive_cli(["readonly", "search", "--name-contains", folder_name, "--json"]))
        matches = folders(data if isinstance(data, list) else data.get("files", data.get("items", [])))
    exact = [it for it in matches if it.get("name", "").strip().lower() == q]
    if len(matches) > 1 and len(exact) == 1:  # "19 포드 머스탱 옵틱" also sits inside "19 포드 머스탱 옵틱 [25.05.06]"
        return exact[0].get("id")
    if len(matches) > 1:
        listing = "\n".join(f"  {it.get('name', '').strip()}  --gdrive-folder {it.get('id')}" for it in matches[:20])
        more = f"\n  ... and {len(matches) - 20} more" if len(matches) > 20 else ""
        raise ValueError(f"'{folder_name}' matches {len(matches)} Drive folders; choose one:\n{listing}{more}")
    return matches[0].get("id") if matches else None


# What a vehicle job folder holds besides its top level (subfolder names counted over all 742 folders, 2026-10-29):
# camera originals ("Photos-1-001" Google Photos exports, 영상, 차사진, 외관사진, ...) and edited output (블로그, 수정,
# 유튜브, 인스타, Premiere caches, ...). Edited output is never footage; a name in neither list is skipped and reported.
SUBFOLDER_EDITS = re.compile(r"adobe|premiere|motion graphics|\.prv$|^audio$|블로그|^블\d*$|유튜브|youtube|수정|슈정|보정|인스타|insta|"
                             r"^sns$|^gif$|편집|완료|최종|완성|-assets(\s*\(\d+\))?$|로고|썸네일|thumbnail", re.I)
# "번호판 가린 사진" holds photos whose plates are already masked: the safest thumbnail material. A subfolder named after
# another car or job ("BMWX5+스타포쉬", "포드 F-150") is not listed: it can hold another product or car.
SUBFOLDER_ORIGINALS = re.compile(r"^(\d+\.\s*)?(photos-\d+-\d+.*|영상|동영상|원본|사진|이미지|차\s?사진|외관\s?사진|차량\s?외관\s?사진|"
                                 r"작업\s?사진|차량\s?작업\s?사진|번호판\s?가린\s?사진|비교|교체|시공|새 폴더|옵틱)$", re.I)
# Edited files kept next to the originals (old thumbnails, Instagram crops, finished cuts).
EDIT_FILE_NAMES = re.compile(r"썸네일|thumbnail|인스타|insta|블로그|blog|완성|최종|편집|캡처|스크린샷|screenshot|템플릿|template", re.I)
MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".mov", ".mp4", ".heic", ".heif"}
MIME_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/heif": ".heic", "image/heic": ".heic",
            "video/quicktime": ".mov", "video/mp4": ".mp4"}
SYNC_RESERVE_BYTES = 3 * 1024 ** 3  # left free after a download: clips, drafts and frames are written next
SYNC_MAX_DEPTH = 2  # job folder -> Photos-1-001 -> (one more level)


def _gdrive_ls(folder_id: str) -> List[Dict[str, Any]]:
    data = json.loads(run_gdrive_cli(["readonly", "ls", folder_id, "--max", "1000", "--json"]))
    return data if isinstance(data, list) else data.get("files", data.get("items", []))


def _same_car_subfolder(sub_name: str, folder_name: Optional[str]) -> bool:
    """A subfolder named after the job's own car ("71.BMW XM" -> "BMW XM", "23 BMW X7 옵틱" -> "23 BMW X7 옵틱+영상"):
    same brand and model as the job folder (drive_index normalization), and no product the job folder does not have
    (some folders are archives of other cars' Starposh/Osami/mat jobs)."""
    if not folder_name:
        return False
    parent, sub = ({"name": n, **drive_index.parse_name(n)} for n in (folder_name, sub_name))
    other_products = set(sub["products"]) - set(parent["products"]) - {"opticglass"}
    return not other_products and drive_index.group_of(parent) == drive_index.group_of(sub) and "기타" not in drive_index.group_of(sub)


def _indexed_folder_name(folder_id: str) -> Optional[str]:
    cache = WORK_DIR / "datasets" / "drive_vehicle_index.json"
    if not cache.exists():
        return None
    return next((r["name"] for r in json.loads(cache.read_text(encoding="utf-8"))["folders"] if r["id"] == folder_id), None)


def plan_gdrive_sync(folder_id: str, dest_dir: pathlib.Path, ls=_gdrive_ls, folder_name: Optional[str] = None) -> Dict[str, Any]:
    """What a sync would fetch, without downloading: the media of the folder, of its original-footage subfolders and
    of subfolders named after the same car, with edited output, non-media and duplicates (same name and size) set
    aside by reason."""
    plan: Dict[str, Any] = {"folder_id": folder_id, "folder_name": folder_name, "files": [], "skipped": {},
                            "subfolders": {"included": [], "edited": [], "unknown": []}}
    skip = lambda reason, label: plan["skipped"].setdefault(reason, []).append(label)
    seen = set()

    def walk(fid: str, prefix: str, depth: int) -> None:
        for it in ls(fid):
            name, mime = (it.get("name") or "").strip(), it.get("mimeType") or ""
            label = prefix + name
            if mime.endswith(".folder"):
                kind = "edited" if SUBFOLDER_EDITS.search(name) else "included" if SUBFOLDER_ORIGINALS.match(name) else "unknown"
                if kind == "unknown" and depth == 0 and _same_car_subfolder(name, folder_name):
                    kind = "included"
                if kind == "included" and depth >= SYNC_MAX_DEPTH:
                    kind = "unknown"
                plan["subfolders"][kind].append(label)
                if kind == "included":
                    walk(it["id"], label + "/", depth + 1)
                continue
            ext = pathlib.Path(name).suffix.lower()
            if ext not in MEDIA_EXTS:
                if mime in MIME_EXT and not ext:  # a video or photo uploaded without an extension
                    ext, name = MIME_EXT[mime], name + MIME_EXT[mime]
                else:
                    skip("바로가기" if "shortcut" in mime else "RAW 사진 (CR2 등)" if "raw" in mime or "cr2" in mime
                         else "미디어 아님", label)
                    continue
            if EDIT_FILE_NAMES.search(name):
                skip("편집 결과물", label)
                continue
            key = (name.lower(), it.get("size"))
            if key in seen:
                skip("중복 (같은 이름·크기)", label)
                continue
            seen.add(key)
            plan["files"].append({"id": it["id"], "name": name, "from": label, "size": int(it.get("size") or 0),
                                  "heic": ext in (".heic", ".heif")})

    walk(folder_id, "", 0)
    used = set()
    for f in plan["files"]:  # different Drive files with one name (two phones, two subfolders) get the file id appended
        stem, suffix = pathlib.Path(f["name"]).stem, pathlib.Path(f["name"]).suffix
        target = f["name"] if f["name"].lower() not in used else f"{stem}_{f['id'][:6]}{suffix}"
        used.add(target.lower())
        f["target"] = target
        f["have"] = (dest_dir / target).exists()
    # HEIC is kept and also converted to JPG, so count it twice
    plan["need_bytes"] = sum(f["size"] * (2 if f["heic"] else 1) for f in plan["files"] if not f["have"])
    return plan


def _heic_to_jpg(src: pathlib.Path, taken: set) -> pathlib.Path:
    """The thumbnail and frame code read JPG/PNG; the HEIC original stays next to it. taken: the lowercased names of
    the Drive files; <stem>_heic.jpg only when a Drive file is already called <stem>.jpg (else a re-sync made a twin)."""
    jpg = src.with_suffix(".jpg")
    if jpg.name.lower() in taken:
        jpg = src.with_name(src.stem + "_heic.jpg")
    if not jpg.exists():
        import pillow_heif
        from PIL import Image, ImageOps
        pillow_heif.register_heif_opener()
        with Image.open(src) as im:
            ImageOps.exif_transpose(im).convert("RGB").save(jpg, "JPEG", quality=95)
    return jpg


def sync_from_gdrive(
    dest_dir: pathlib.Path,
    folder_id_or_url: Optional[str] = None,
    folder_name: Optional[str] = None,
    on_progress=lambda frac, what: None,
) -> List[pathlib.Path]:
    """Download a Drive vehicle folder's photos and videos into dest_dir (flat), including its original-footage
    subfolders, and return the usable media. Never overwrites a local file (the builders cut from them). Checks free
    disk space before the first download, and writes what it took and skipped to dest_dir/.drive_sync.json.
    on_progress(share of the bytes to fetch done, label) runs before each download."""
    if not check_gdrive_logged_in():
        raise RuntimeError(
            "Google Drive CLI is not logged in yet. Complete the browser OAuth login first."
        )

    folder_id = (
        extract_gdrive_id(folder_id_or_url)
        if folder_id_or_url
        else find_gdrive_folder_by_name(folder_name or "")
    )
    if not folder_id:
        raise ValueError(
            f"Could not resolve Google Drive folder (id={folder_id_or_url}, name={folder_name})"
        )

    dest_dir.mkdir(parents=True, exist_ok=True)
    plan = plan_gdrive_sync(folder_id, dest_dir, folder_name=_indexed_folder_name(folder_id) or folder_name)
    free = shutil.disk_usage(dest_dir).free
    if plan["need_bytes"] + SYNC_RESERVE_BYTES > free:
        gb = 1024 ** 3
        raise RuntimeError(f"디스크 공간 부족: {plan['need_bytes'] / gb:.1f} GB를 받고 작업용으로 {SYNC_RESERVE_BYTES / gb:.0f} GB를 "
                           f"남겨야 하는데 {dest_dir.anchor} 여유가 {free / gb:.1f} GB입니다. 공간을 비운 뒤 다시 실행하세요.")

    media: List[pathlib.Path] = []
    fetched = converted = 0
    todo = [f for f in plan["files"] if not f["have"]]
    done_bytes, todo_bytes = 0, sum(f["size"] or 0 for f in todo) or 1
    if todo:
        lock = threading.Lock()

        def _fetch_one(f: Dict[str, Any]) -> None:
            nonlocal done_bytes, fetched
            target = dest_dir / f["target"]
            # The Drive name never reaches cmd.exe (an unquoted & or | in it would split or run a command): download to
            # the file id ([A-Za-z0-9_-] only) plus this process id, so two runs of the same car never share a .part.
            part = dest_dir / f"{f['id']}.{os.getpid()}.part"
            with lock:
                on_progress(done_bytes / todo_bytes, f"Drive 다운로드 {fetched + 1}/{len(todo)}")
                print(f"[Google Drive Download] {f['from']} -> {target.name}", flush=True)
            try:
                run_gdrive_cli(["readonly", "download", f["id"], "--out", str(part)])
                part.replace(target)
            finally:
                part.unlink(missing_ok=True)
            with lock:
                done_bytes += f["size"] or 0
                fetched += 1
                on_progress(done_bytes / todo_bytes, f"Drive 다운로드 {fetched}/{len(todo)}")

        with ThreadPoolExecutor(max_workers=min(3, len(todo))) as ex:
            list(ex.map(_fetch_one, todo))

    taken = {f["target"].lower() for f in plan["files"]}
    for f in plan["files"]:
        target = dest_dir / f["target"]
        if f["have"] and f["size"] and target.stat().st_size != f["size"]:
            print(f"[Google Drive] {f['target']}: 로컬 파일 크기가 Drive와 다름 — 로컬 파일 유지 (다시 받으려면 로컬 파일 삭제)")
        if f["heic"]:
            try:
                target = _heic_to_jpg(target, taken)
                converted += 1
            except Exception as exc:  # a damaged HEIC: keep going, say which
                plan["skipped"].setdefault("HEIC 변환 실패", []).append(f"{f['from']} ({exc})")
                continue
        media.append(target)

    plan["synced_at"] = datetime.now().isoformat(timespec="seconds")
    atomic_write_json(dest_dir / ".drive_sync.json", plan, indent=1)
    videos = sum(p.suffix.lower() in (".mov", ".mp4") for p in media)
    print(f"[Google Drive] 미디어 {len(media)}개 (영상 {videos}, 사진 {len(media) - videos}, HEIC→JPG {converted}), "
          f"새로 받음 {fetched}, 이미 있음 {sum(f['have'] for f in plan['files'])}")
    if plan["subfolders"]["included"]:
        print(f"[Google Drive] 포함한 하위폴더: {', '.join(plan['subfolders']['included'])}")
    for kind, title in (("edited", "편집물이라 건너뛴 하위폴더"), ("unknown", "이름을 몰라 건너뛴 하위폴더 (원본이면 SUBFOLDER_ORIGINALS에 추가)")):
        if plan["subfolders"][kind]:
            print(f"[Google Drive] {title}: {', '.join(plan['subfolders'][kind])}")
    for reason, labels in plan["skipped"].items():
        print(f"[Google Drive] 건너뛴 파일 ({reason}) {len(labels)}개: {', '.join(labels[:5])}{' ...' if len(labels) > 5 else ''}")
    if not media:
        raise RuntimeError("이 Drive 폴더에서 쓸 수 있는 사진·영상이 없습니다 (위의 건너뛴 하위폴더와 파일을 확인하세요).")
    return media


def auto_find_brand_logo(car_name: str) -> Optional[pathlib.Path]:
    """Automatically match brand logo PNG from local CarLogos repository."""
    if not CAR_LOGOS_ROOT.exists():
        return None
    brand_map = {
        "테슬라": "Tesla",
        "사이버트럭": "Tesla",
        "폴스타": "Polestar",
        "아우디": "Audi",
        "벤츠": "Mercedes-Benz",
        "제네시스": "Genesis",
        "현대": "Hyundai",
        "기아": "Kia",
        "포르쉐": "Porsche",
        "폭스바겐": "Volkswagen",
        "볼보": "Volvo",
        "렉서스": "Lexus",
        "토요타": "Toyota",
        "미니": "MINI",
        "랜드로버": "Land Rover",
        "지프": "Jeep",
        "포드": "Ford",
        "캐딜락": "Cadillac",
        "링컨": "Lincoln",
        "푸조": "Peugeot",
        "르노": "Renault",
        "쉐보레": "Chevrolet",
        "페라리": "Ferrari",
        "람보르기니": "Lamborghini",
        "마세라티": "Maserati",
        "벤틀리": "Bentley",
        "비엠": "BMW",
        "bmw": "BMW",
        "byd": "BYD",
        "씨라이언": "BYD",
    }
    target_brand = None
    for kr, en in brand_map.items():
        if kr in car_name or en.lower() in car_name.lower():
            target_brand = en
            break
    if not target_brand:
        return None
    for p in CAR_LOGOS_ROOT.glob("*.png"):
        if target_brand.lower() in p.stem.lower():
            return p
    return None


def classify_media_slots(
    media_files: List[pathlib.Path],
    allowed_vehicle_dir: Optional[pathlib.Path] = None,
) -> Dict[str, Optional[pathlib.Path]]:
    """Guess the three thumbnail photos (by file name, else shoot order); the GUI's 썸네일 사진 window starts from these."""
    ok, issues = validate_media_paths([str(p) for p in media_files], allowed_vehicle_dir=allowed_vehicle_dir)
    if not ok:
        raise RuntimeError(f"Media validation failed: {issues}")

    images = sorted(
        [p for p in media_files if p.suffix.lower() in {".jpg", ".jpeg", ".png"}],
        key=lambda p: (p.stat().st_mtime, p.name),
    )
    slots: Dict[str, Optional[pathlib.Path]] = {"before_photo": None, "after_photo": None, "car_exterior": None}

    # 1. Match images by filename hints first
    remaining_imgs: List[pathlib.Path] = []
    for img in images:
        stem = img.stem.lower()
        if any(k in stem for k in ("조견표", "5010_", "compat", "logo", "로고")):
            continue
        elif any(k in stem for k in ("미러전", "시공전", "before", "_bef")):
            slots["before_photo"] = img
        elif any(k in stem for k in ("미러후", "시공후", "after", "_aft")):
            slots["after_photo"] = img
        elif any(k in stem for k in ("외관", "사진", "exterior", "hero", "car")):
            slots["car_exterior"] = img
        else:
            remaining_imgs.append(img)

    # 2. If before/after not matched by filename (e.g., raw IMG_0001.JPG from Google Drive), chronological workshop
    # shoot order. Only a suggestion: the GUI's 썸네일 사진 window is where a person picks the photos.
    if not slots["before_photo"] and remaining_imgs:
        slots["before_photo"] = remaining_imgs.pop(0)
    if not slots["after_photo"] and remaining_imgs:
        slots["after_photo"] = remaining_imgs.pop(0)
    if not slots["car_exterior"] and remaining_imgs:
        slots["car_exterior"] = remaining_imgs.pop(0)
    return slots


def generate_thumbnails_from_slots(
    slots: Dict[str, Optional[pathlib.Path]],
    car_name: str,
    output_dir: pathlib.Path,
    headline_line2: str = "광각미러 차이!",
    ref_id_horizontal: str = "0031",
    ref_id_vertical: str = "0034",
    name: str = "thumbnail",
) -> List[pathlib.Path]:
    """Automatically invoke Stage 3 (generate_thumbnail.py) using Stage 1 classified media."""
    if not THUMBNAIL_SCRIPT.exists():
        raise FileNotFoundError(f"Thumbnail generator not found at {THUMBNAIL_SCRIPT}")

    spec = importlib.util.spec_from_file_location("generate_thumbnail_mod", THUMBNAIL_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load generate_thumbnail.py module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    output_dir.mkdir(parents=True, exist_ok=True)
    before_path = slots.get("before_photo")
    after_path = slots.get("after_photo")
    bg_path = slots.get("car_exterior")

    generated_paths: List[pathlib.Path] = []

    # 1. Primary 1280x720 Horizontal Split Thumbnail (Ref #0031 style)
    out_h = output_dir / f"{name}_1280x720_split_horizontal.jpg"
    mod.generate_thumbnail(
        ref_id=ref_id_horizontal,
        bg_path=bg_path,
        before_path=before_path,
        after_path=after_path,
        out_path=out_h,
        overrides={
            "preset": "split_horizontal",
            "headline_line1": car_name,
            "headline_line2": headline_line2,
        },
    )
    generated_paths.append(out_h)

    # 2. Secondary 1280x720 Vertical Split Thumbnail (Ref #0034 style)
    out_v = output_dir / f"{name}_1280x720_split_vertical.jpg"
    mod.generate_thumbnail(
        ref_id=ref_id_vertical,
        bg_path=bg_path,
        before_path=before_path,
        after_path=after_path,
        out_path=out_v,
        overrides={
            "preset": "split_vertical",
            "headline_line1": car_name,
            "headline_line2": headline_line2,
        },
    )
    generated_paths.append(out_v)

    return generated_paths


def gauge(weights: Dict[str, int]):
    """The 실행 로그 gauge in opticglass_gui.py. Each step this run takes gets a share of 0-100 % by its usual time
    (0 = skipped). at(step, frac, label) prints `[진행 NN%] label`: the GUI moves the bar, the command line just shows it."""
    total = sum(weights.values()) or 1
    done = {k: 0.0 for k in weights}
    high = 0
    _lock = threading.Lock()

    def at(step: str, frac: float = 0.0, label: str = "") -> None:
        nonlocal high
        with _lock:
            if step in done:
                done[step] = max(done[step], min(max(frac, 0.0), 1.0))
            raw_pct = round(100 * sum(weights[k] * done[k] for k in weights) / total)
            high = max(high, raw_pct)
            print(f"[진행 {high}%] {label}", flush=True)
    return at


BUILDS = {  # --build: the GUI button -> (builder command after the script name, the scenario it needs, its draft, gauge label)
    "longform": (["build_longform.py"], "longform", "longform", "롱폼 빌드"),
    "wide1": (["build_longform.py", "--variant", "wide1"], "wide1", "wide1", "광각미러 템플릿 빌드"),
    "shorts": (["build_shorts.py"], "longform", "shorts", "숏폼 빌드"),
}


_report_lock = threading.Lock()


def report_file(slug: str) -> pathlib.Path:
    return OUTPUT_DIR / slug / "report.txt"


def report(slug: str, text: str) -> None:
    """A ~100-character reason this run stopped that the user can act on (footage or photos short, a rule broken); the
    GUI shows report.txt in a message box when the job ends. Each run starts without one."""
    print(f"\n[리포트] {text}", flush=True)
    f = report_file(slug)
    with _report_lock:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(((f.read_text(encoding="utf-8") + "\n") if f.exists() else "") + text, encoding="utf-8")


def scenario_problem(path: pathlib.Path):
    """The house rule the scenario breaks (longform_common.check_scene_rules and the other load checks), else None."""
    import longform_common
    try:
        longform_common.load_scenario(path.stem)
    except ValueError as e:
        return str(e)
    return None


def run_builder(slug: str, at, build: str = "longform") -> list:
    """The builder of --build for slug, its output passed through; its `[n/m]` steps move the gauge. Returns its
    "[검사 실패]" lines when the output check stopped the deploy (exit CHECK_FAILED), else []."""
    script, *opts = BUILDS[build][0]
    proc = subprocess.Popen(
        [sys.executable, "-u", str(WORK_DIR / script), slug, *opts],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONUTF8": "1"},
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    fails = []
    for line in proc.stdout:
        print(line, end="", flush=True)
        m = re.match(r"\[(\d+)/(\d+)\]", line)
        if m:
            at("build", (int(m[1]) - 1) / int(m[2]), f"{BUILDS[build][3]} {m[1]}/{m[2]}")
        else:
            mc = re.search(r"\[씬 클립 (\d+)/(\d+)\]", line)
            if mc:
                at("build", 0.65 * int(mc[1]) / max(int(mc[2]), 1), f"{BUILDS[build][3]} 클립 {mc[1]}/{mc[2]}")
        if line.startswith("[검사 실패]"):
            fails.append(line.removeprefix("[검사 실패]").strip())
    rc = proc.wait()
    if rc == 3:  # build_longform.CHECK_FAILED: built and staged, not deployed
        return fails
    if rc:
        raise subprocess.CalledProcessError(rc, [script, slug, *opts])
    return []


def fetch_reason(ran: bool, has_videos: bool, footage_missing, has_scenario: bool) -> Optional[str]:
    """Why a run of a linked car syncs its Drive folder first, else None (it builds from its local media: new Drive
    files could change the chosen photos). An interrupted first download resumes; clips uploaded after a 영상 부족
    run (no scenario yet) and videos deleted here (폴더 영상 삭제) are fetched again."""
    if not ran:
        return "첫 실행이 아직 끝나지 않아"
    if not has_videos:
        return "내려받은 영상이 없어"
    if footage_missing:
        return f"시나리오 영상 {len(footage_missing)}개가 없어"
    if not has_scenario:
        return "시나리오가 없어 새 클립을 찾으러"
    return None


def deploy_state(draft_name: str) -> dict:
    """The builder deploys only while CapCut is closed; the staged draft compared with the one CapCut actually opens."""
    staged, live = WORK_DIR / "capcut_stage" / draft_name / "draft_content.json", DRAFT_ROOT / draft_name / "draft_content.json"
    # mtimes, not bytes: deploy's copytree keeps them, a CapCut save makes live newer, a new build makes staged newer
    status = "not_built" if not staged.exists() else "deployed" if live.exists() and live.stat().st_mtime >= staged.stat().st_mtime else "held"
    reason = None
    force_flag = ""
    if status == "held":
        pf = run_preflight()
        if pf.get("errors"):  # blocked_v10: --deploy refuses too
            reason = "CapCut 배포 차단: " + "; ".join(pf["errors"])
        elif pf.get("status") == "needs_smoke_retest":
            reason = f"CapCut {pf.get('highest_version')} 미검증 버전 보류 (평문 확인 시 --force로 배포 가능)"
            force_flag = " --force"
        elif pf.get("capcut_process_count", 0) > 0:
            reason = "CapCut이 실행 중이라 배포 보류"
        elif pf.get("capcut_process_count", 0) < 0:  # tasklist failed
            reason = "CapCut 실행 여부를 확인하지 못해 배포 보류"
    return {
        "status": status,
        "path": str(live.parent) if live.exists() else None,
        "reason": reason,
        "command": f"py {WORK_DIR / 'preflight_check.py'}{force_flag} --deploy {draft_name}",
    }


def _print_held_notice(draft_name: str, deploy: dict) -> None:
    why = f" ({deploy['reason']})" if deploy.get("reason") else ""
    print(f"\n!!! [CapCut 배포 보류] {draft_name}는 capcut_stage에만 있습니다{why}."
          f"\n!!! CapCut을 완전히 닫은 뒤 실행: {deploy['command']}")


def finish_extra_draft(args, output_dir: pathlib.Path, draft_name: str, output_check, at) -> None:
    """The end of a 광각미러 템플릿 / 숏폼 run: its draft's state goes into the manifest's extra_drafts (the longform and
    thumbnail records stay as they were), and the run fails when nothing was built or the check failed."""
    manifest_path = output_dir / "package_manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"slug": args.slug, "car_name": args.car_name}
    deploy = deploy_state(draft_name)
    data.setdefault("extra_drafts", {})[draft_name] = {"build": args.build, "generated_at": datetime.now().isoformat(),
                                                       "capcut_deploy": deploy, "output_check": output_check}
    atomic_write_json(manifest_path, data, indent=2)
    at("build", 1.0, "완료")
    if deploy["status"] == "not_built":
        sys.exit(f"[{args.build}] {draft_name}을 만들지 못했습니다 (위 로그 참조)")
    if deploy["status"] == "held":
        _print_held_notice(draft_name, deploy)
    if output_check == "fail":
        sys.exit("[Stage 2 검사 실패] CapCut 초안이 대본과 다릅니다 (위 check_text_outputs 결과 참조)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Google Drive -> AI Media Classification -> Video Template (Stage 2) + Thumbnail (Stage 3) Unified Pipeline"
    )
    parser.add_argument(
        "--car-name",
        type=str,
        default=None,
        help="차종명 (영상 인트로 및 썸네일 1줄 타이틀에 공통 적용)",
    )
    parser.add_argument(
        "--slug",
        "--vehicle",
        dest="slug",
        type=str,
        default="cybertruck",
        help="영문 슬러그 (cybertruck, santafe, bmwx5, sealion7 등)",
    )
    parser.add_argument(
        "--gdrive-folder",
        type=str,
        default=None,
        help="Google Drive 폴더 URL 또는 Folder ID",
    )
    parser.add_argument(
        "--gdrive-search",
        type=str,
        default=None,
        help="Google Drive 폴더 이름으로 검색하여 다운로드",
    )
    parser.add_argument(
        "--local-inbox",
        type=str,
        default=None,
        help="로컬 폴더(또는 Google Drive 데스크톱 동기화 폴더) 경로",
    )
    parser.add_argument(
        "--skip-video-rebuild",
        action="store_true",
        help="이미 생성된 영상 빌드를 재사용하고 매니페스트 + 썸네일 연동만 빠르게 실행",
    )
    parser.add_argument(
        "--ai-bg",
        action="store_true",
        help="가린 외관 사진으로 AI 배경(agy 구독)을 만들어 thumbnail_ai_* 썸네일 한 쌍을 더 생성",
    )
    parser.add_argument(
        "--build",
        choices=list(BUILDS),
        default="longform",
        help="Stage 2에서 만들 것: longform (롱폼 + 썸네일), wide1 (광각미러 템플릿 1 롱폼), shorts (롱폼에서 자른 9:16 숏폼 5개). "
             "wide1/shorts는 Stage 3(썸네일)을 건너뜀",
    )
    parser.add_argument(
        "--auto-photos",
        action="store_true",
        help="썸네일 사진 3장을 AI(agy)가 이 차의 모든 사진에서 다시 골라 가리기 (검수 생략, 저장된 선택을 바꿈)",
    )
    args = parser.parse_args()
    if not args.car_name:
        args.car_name = drive_index.title(args.slug)  # the GUI's car-name field

    inbox_dir = drive_index.media_dir(args.slug) / "gdrive_raw"  # media/<Drive path>/ (media/<slug>/ for cars downloaded before that)
    output_dir = OUTPUT_DIR / args.slug
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file(args.slug).unlink(missing_ok=True)
    import thumb_photos
    only_video = args.build != "longform"  # 광각미러 템플릿 / 숏폼 buttons: their draft only, no thumbnails
    variant = BUILDS[args.build][1]
    if args.build == "shorts" and not (WORK_DIR / "scenarios" / f"{args.slug}_longform.json").exists() and (WORK_DIR / "scenarios" / f"{args.slug}_wide1.json").exists():
        variant = "wide1"
    scenario = WORK_DIR / "scenarios" / f"{args.slug}_{variant}.json"  # the car's edit; build_longform.py builds any car with one
    problem = scenario_problem(scenario) if scenario.exists() and not args.skip_video_rebuild else None
    # a scenario the generator wrote that breaks a rule is written again (cached agy answers); a person's is not touched
    regen = problem and json.loads(scenario.read_text(encoding="utf-8")).get("generated")
    link = drive_index.links().get(args.slug)
    if link and not (args.gdrive_folder or args.gdrive_search or args.local_inbox):
        media_exts = (".jpg", ".jpeg", ".png", ".mov", ".mp4") if args.skip_video_rebuild else (".mov", ".mp4")
        why = fetch_reason(drive_index.status(args.slug)["ran"],
                           inbox_dir.exists() and any(p.suffix.lower() in media_exts for p in inbox_dir.rglob("*")),
                           not args.skip_video_rebuild and drive_index.missing_footage(args.slug),
                           args.skip_video_rebuild or scenario.exists())
        if why:
            print(f"[Google Drive] {args.slug}: {why} Drive 폴더에서 내려받습니다 (이미 받은 파일은 건너뜀)")
            args.gdrive_folder = link["folder_id"]
    at = gauge({  # rough minutes on this PC: post-masking & post-build inspections are skipped to finish within 10m
        "download": 25 if (args.gdrive_folder or args.gdrive_search) else 0,
        "scenario": 0 if args.skip_video_rebuild or (scenario.exists() and not regen) else 15,  # make_scenario.py: 1st-pass review only
        "build": 0 if args.skip_video_rebuild else 20,
        "photos": 0 if only_video or (not args.auto_photos and thumb_photos.ready(args.slug)) else 10,
        "thumbs": 0 if only_video else 5,
        "ai_bg": 20 if args.ai_bg and not only_video else 0,
    })

    # Step 1: Collect media strictly from the designated vehicle model index in Google Drive (or its synced local folder)
    active_vehicle_dir = inbox_dir
    at("download", 0, "Drive 사진·영상 확인")
    if args.gdrive_folder or args.gdrive_search:
        print(f"=== [Stage 1] Google Drive 지정 차종 인덱스에서 미디어 다운로드 중 ({args.gdrive_folder or args.gdrive_search}) ===")
        media_files = sync_from_gdrive(
            dest_dir=inbox_dir,
            folder_id_or_url=args.gdrive_folder,
            folder_name=args.gdrive_search,
            on_progress=lambda frac, label: at("download", frac, label),
        )
        still = drive_index.missing_footage(args.slug)
        if still:  # the scenario names clips the Drive folder does not have (renamed, moved or never uploaded)
            print(f"[Google Drive] Drive 폴더에도 없는 시나리오 영상 {len(still)}개: {', '.join(still[:8])}")
    elif args.local_inbox:
        local_path = pathlib.Path(args.local_inbox)
        active_vehicle_dir = local_path
        media_files = [
            p
            for p in local_path.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".mov", ".mp4"}
        ]
    else:
        print(f"=== [Stage 1] 지정 차종 Google Drive 동기화 폴더({inbox_dir}) 미디어 로드 ===")
        media_files = (
            [
                p
                for p in inbox_dir.iterdir()
                if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".mov", ".mp4"}
            ]
            if inbox_dir.exists()
            else []
        )

    if not media_files:
        raise RuntimeError("수집된 미디어 파일이 없습니다. 폴더 경로 또는 Google Drive 폴더를 확인하세요.")

    # Step 2: the picker's first guess of the thumbnail photos, with strict vehicle folder isolation
    slots = classify_media_slots(media_files, allowed_vehicle_dir=active_vehicle_dir)
    print("\n=== [Stage 1] 썸네일 사진 첫 추정 (썸네일 사진 창의 시작값) ===")
    for k, v in slots.items():
        print(f"  - {k:15s}: {v}")

    # Step 3: Stage 2 Video Build & Stage 3 Thumbnail Build (executed concurrently when building longform)
    if not args.skip_video_rebuild:
        if not scenario.exists() or regen:  # a car with no scenario yet: agy writes it from the car's own clips
            import make_scenario
            why = f"규칙 위반({problem})이라 다시" if regen else "없음: 이 차 영상·사진으로"
            print(f"\n=== [Stage 2 시나리오] {scenario.name} {why} 광각미러 템플릿 1(57.7초) 시나리오를 만듭니다 (make_scenario.py, agy) ===", flush=True)
            try:
                make_scenario.generate(args.slug, lambda frac, label: at("scenario", frac, label), force=True, variant=variant)
            except make_scenario.ShortFootage as e:
                print(f"  [시나리오 생성 불가] {e}", flush=True)
                report(args.slug, str(e))
            except Exception as e:  # agy timeout, an unanswered still, ffmpeg: no longform this run, thumbnails still run
                print(f"  [시나리오 생성 실패] {type(e).__name__}: {e} (다시 실행하면 분류된 장면은 이어서 씁니다)", flush=True)
                report(args.slug, f"{args.car_name} {BUILDS[args.build][3]}: 시나리오 생성 실패 — {type(e).__name__}: {e}")
        elif problem:
            report(args.slug, f"{args.car_name}: 시나리오가 규칙에 맞지 않아 만들지 않았습니다 — {problem}")
        problem = scenario_problem(scenario) if scenario.exists() else "없음"

    draft_name = f"hermes_{args.slug}_optic_{BUILDS[args.build][2]}"

    def _run_stage2():
        fails_res = None
        out_check = None
        if not args.skip_video_rebuild:
            if not problem:
                print(f"\n=== [Stage 2] {BUILDS[args.build][3]}: 영상 클립 & CapCut 초안 ({' '.join(BUILDS[args.build][0])} {args.slug}) ===", flush=True)
                at("build", 0, BUILDS[args.build][3])
                fails_res = run_builder(args.slug, at, args.build)
                if fails_res:
                    report(args.slug, f"{args.car_name} {BUILDS[args.build][3]}: 규칙 검사 실패 {len(fails_res)}건이라 CapCut에 넣지 않았습니다 (첫째: {fails_res[0][:60]})")
            else:
                print(f"\n=== [Stage 2 건너뜀] {scenario.name}: {'영상이 부족해' if (drive_index.media_dir(args.slug) / 'scenario_short.json').exists() else problem} 롱폼을 만들지 못했습니다 ===", flush=True)

        if args.build != "shorts" and (WORK_DIR / "capcut_stage" / draft_name).exists():
            out_check = "pass"
            print(f"\n=== [Stage 2 완료] {draft_name}: 사후 검수 생략 (check_text_outputs.py 건너뜀) ===", flush=True)
        elif args.build == "shorts" and fails_res is not None:
            out_check = "fail" if fails_res else "pass"
        at("build", 1.0, f"{BUILDS[args.build][3]} 완료")
        return fails_res, out_check

    def _run_stage3():
        pts = None if args.auto_photos else thumb_photos.ready(args.slug)
        if not pts:
            print(f"\n=== [Stage 3 사진 분류·마스킹] {args.slug}: 사진 분류·번호판/얼굴 가리기 (검수 생략) ===", flush=True)
            at("photos", 0, "사진 분류·가리기")
            try:
                for line in thumb_photos.ai_check(args.slug, fresh=args.auto_photos,
                                                  progress=lambda frac, label: at("photos", frac, label)):
                    print(f"  [가려지지 않음] {line}", flush=True)
            except Exception as exc:
                print(f"  [사진 분류·가리기 실패] {exc}", flush=True)
                if isinstance(exc, thumb_photos.ShortFootage):
                    report(args.slug, str(exc))
            pts = thumb_photos.ready(args.slug)
        at("photos", 1.0, "사진 분류·가리기 완료")

        gen_thumbs: List[pathlib.Path] = []
        status_ai = None
        manifest_p = output_dir / "package_manifest.json"
        old_data = json.loads(manifest_p.read_text(encoding="utf-8")) if manifest_p.exists() else {}
        ex_ai_thumbs = sorted(output_dir.glob("thumbnail_ai_1280x720_split_*.jpg"))
        keep_ai = (
            not args.ai_bg
            and not args.auto_photos
            and bool(pts)
            and bool(ex_ai_thumbs)
            and old_data.get("car_name") == args.car_name
            and old_data.get("stage3_thumbnail_photos") == {k: str(v) for k, v in pts.items()}
        )
        if not keep_ai:
            for old_ai in ex_ai_thumbs:
                old_ai.unlink(missing_ok=True)
        if pts:
            print(f"\n=== [Stage 3] 분류·마스킹 완료된 외관/시공 전/후 사진으로 썸네일 생성 ({args.car_name}) ===", flush=True)
            at("thumbs", 0, "썸네일 만들기")
            scenario_f = WORK_DIR / "scenarios" / f"{args.slug}_longform.json"
            if not scenario_f.exists():
                scenario_f = WORK_DIR / "scenarios" / f"{args.slug}_wide1.json"
            thumb_c = json.loads(scenario_f.read_text(encoding="utf-8")).get("thumbnail", {}) if scenario_f.exists() else {}
            gen_thumbs = generate_thumbnails_from_slots(
                slots=pts,
                car_name=args.car_name,
                output_dir=output_dir,
                headline_line2=thumb_c.get("line2") or "광각미러 차이!",
            )
            for t in gen_thumbs:
                print(f"  [1280x720 썸네일 생성 완료] -> {t}", flush=True)
            if args.ai_bg:
                ai_bg = pts["car_exterior"].with_name("ai_background.png")
                try:
                    import llm
                    st = llm.status()
                    print(f"\n=== [Stage 3 AI 배경] 가린 외관 사진 -> {ai_bg.name} (agy: {st['note']}) ===", flush=True)
                    at("ai_bg", 0, "AI 배경 그리는 중 (약 2분)")
                    spec = importlib.util.spec_from_file_location("prompt_generator_mod", THUMBNAIL_SCRIPT.with_name("prompt_generator.py"))
                    pg = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(pg)
                    ai_bg.unlink(missing_ok=True)
                    pg.make_ai_background(pts["car_exterior"], args.car_name, ai_bg)
                    ai_thumbs = generate_thumbnails_from_slots(
                        slots={**pts, "car_exterior": ai_bg},
                        car_name=args.car_name,
                        output_dir=output_dir,
                        headline_line2=thumb_c.get("line2") or "광각미러 차이!",
                        name="thumbnail_ai",
                    )
                    gen_thumbs += ai_thumbs
                    status_ai = "done"
                    for t in ai_thumbs:
                        print(f"  [AI 배경 썸네일 생성 완료] -> {t}", flush=True)
                except Exception as exc:
                    status_ai = f"failed: {exc}"
                    print(f"  [AI 배경 실패] {exc}", flush=True)
            elif keep_ai:
                gen_thumbs += ex_ai_thumbs
                status_ai = old_data.get("stage3_ai_background") or "done"
        else:
            print(f"\n=== [Stage 3 건너뜀] {args.slug}: 썸네일 사진을 준비하지 못했습니다 ===\n"
                  "  위 [사진 분류·가리기 실패] 줄이 이유입니다 (사진·영상이 부족하면 촬영 자료를 Drive에 더 올리고 다시 실행).", flush=True)
        return pts, gen_thumbs, status_ai

    if only_video:
        fails, output_check = _run_stage2()
        if fails is None:  # an older staged draft is not this run's output
            finish_extra_draft(args, output_dir, draft_name, output_check, at)
            sys.exit(f"[{args.build}] {draft_name}을 이번 실행에서 만들지 못했습니다 (위 로그 참조)")
        finish_extra_draft(args, output_dir, draft_name, output_check, at)
        return

    # Execute Stage 2 (Video Build) and Stage 3 (Thumbnail Build) concurrently
    with ThreadPoolExecutor(max_workers=2) as stage_ex:
        stage2_fut = stage_ex.submit(_run_stage2)
        stage3_fut = stage_ex.submit(_run_stage3)
        fails, output_check = stage2_fut.result()
        photos, thumbs, ai_status = stage3_fut.result()

    # Step 5: Write unified package manifest
    def existing(p: pathlib.Path) -> Optional[str]:
        return str(p) if p.exists() else None

    manifest_path = output_dir / "package_manifest.json"
    old = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    deploy = deploy_state(draft_name)
    manifest_data: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "car_name": args.car_name,
        "slug": args.slug,
        "source_mode": "gdrive" if (args.gdrive_folder or args.gdrive_search) else "local",
        "slots": {k: (str(v) if v else None) for k, v in slots.items()},
        "stage2_video_outputs": {  # null = not built (yet)
            "spec_json": existing(ROOT_DIR / "strategy" / "specs" / "longform" / f"{args.slug}_opticglass_longform.spec.json"),
            "capcut_draft_name": draft_name if (WORK_DIR / "capcut_stage" / draft_name).exists() else None,
            "capcut_deploy": deploy,
            "output_check": (old.get("stage2_video_outputs") or {}).get("output_check") if args.skip_video_rebuild and output_check is None else output_check,  # null = nothing staged to check
        },
        "stage3_thumbnail_status": "done" if photos else "needs_photo_pick",
        "stage3_thumbnail_photos": {k: str(v) for k, v in photos.items()} if photos else None,
        "stage3_thumbnail_outputs": [str(t) for t in thumbs],
        "stage3_ai_background": ai_status,  # null = not asked for (--ai-bg), or no photos passed
    }
    if old.get("extra_drafts"):  # the 광각미러 템플릿 / 숏폼 drafts' state (finish_extra_draft)
        manifest_data["extra_drafts"] = old["extra_drafts"]
    atomic_write_json(manifest_path, manifest_data, indent=2)
    print(f"\n=== [통합 패키지 매니페스트 저장 완료] -> {manifest_path} ===")
    at("ai_bg", 1.0, "완료")  # the last step's end: 100 %
    if deploy["status"] == "held":
        _print_held_notice(draft_name, deploy)
    if not args.skip_video_rebuild and (fails is None or deploy["status"] == "not_built"):
        sys.exit(f"[longform] {draft_name}을 이번 실행에서 만들지 못했습니다 (위 로그 참조)")
    if output_check == "fail":
        sys.exit("[Stage 2 검사 실패] CapCut 초안이 대본과 다릅니다 (위 check_text_outputs 결과 참조)")
    if ai_status and ai_status != "done":
        sys.exit(f"[AI 배경 실패] {ai_status}")


def _selftest() -> None:
    import tempfile
    folder = lambda i, n: {"id": i, "name": n, "mimeType": "application/vnd.google-apps.folder"}
    file = lambda i, n, size=1, mime="video/quicktime": {"id": i, "name": n, "mimeType": mime, "size": str(size)}
    tree = {
        "root": [folder("ed", "블로그"), folder("ph", "Photos-1-001"), file("a1aaaaaa", "IMG_1.MOV", 10),
                 file("a2", "IMG_1.MOV", 10), file("noext", "clip"), file("doc", "memo.pdf", 1, "application/pdf"),
                 file("h1", "IMG_2.HEIC", 5, "image/heic"), file("j2", "IMG_3.jpg", 5, "image/jpeg"),
                 file("h3", "IMG_3.HEIC", 5, "image/heic")],
        "ed": [file("e1", "edited.MOV")],
        "ph": [file("b2bbbbbb", "IMG_1.MOV", 20)],
    }
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        plan = plan_gdrive_sync("root", d, ls=lambda fid: tree[fid])
        targets = {f["from"]: f["target"] for f in plan["files"]}
        assert plan["subfolders"]["edited"] == ["블로그"] and "edited.MOV" not in str(targets)  # edited output skipped
        assert plan["subfolders"]["included"] == ["Photos-1-001"]  # camera originals included
        assert plan["skipped"]["중복 (같은 이름·크기)"] == ["IMG_1.MOV"]  # same name and size: one download
        assert (targets["Photos-1-001/IMG_1.MOV"], targets["IMG_1.MOV"]) == ("IMG_1.MOV", "IMG_1_a1aaaa.MOV")  # other size: id suffix
        assert targets["clip"] == "clip.mov" and plan["skipped"]["미디어 아님"] == ["memo.pdf"]  # extension from MIME
        taken = {f["target"].lower() for f in plan["files"]}
        (d / "IMG_2.jpg").touch(), (d / "IMG_3_heic.jpg").touch()  # converted by an earlier sync: no decoding here
        assert _heic_to_jpg(d / "IMG_2.HEIC", taken).name == "IMG_2.jpg"  # a re-sync makes no IMG_2_heic.jpg twin
        assert _heic_to_jpg(d / "IMG_3.HEIC", taken).name == "IMG_3_heic.jpg"  # Drive's own IMG_3.jpg is not replaced
    assert fetch_reason(False, True, [], True) and fetch_reason(True, False, [], True)
    assert fetch_reason(True, True, ["a.MOV"], True) and fetch_reason(True, True, [], False)  # 영상 부족, then new clips
    assert fetch_reason(True, True, False, True) is None
    print("gdrive_pipeline self-check ok")


if __name__ == "__main__":
    _selftest() if "--selftest" in sys.argv else main()
