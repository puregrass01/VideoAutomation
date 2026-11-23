import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
WORK_DIR = BASE_DIR / "work"
STAGE_DIR = WORK_DIR / "capcut_stage"
APPS_DIR = pathlib.Path.home() / "AppData" / "Local" / "CapCut" / "Apps"
DRAFT_ROOT = pathlib.Path.home() / "AppData" / "Local" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
SNAPSHOT_FILE = WORK_DIR / "capcut_version_snapshot.json"

VERIFIED_MAX_VERSION = (9, 7, 0, 4153)
AI_SLOP_BLOCKLIST = (
    "puregrass_",
    "kling_",
    "smoke_video",
    "Ultra_realistic_dashcam",
    "사이드미러가_좀더",
    "사이드미러를_보다",
    "사이버트럭 리사",
    "라리사",
    "리사씨",
    "리사차",
)


def parse_version_tuple(vstr: str):
    parts = []
    for p in vstr.strip().split("."):
        if p.isdigit():
            parts.append(int(p))
        else:
            return None
    return tuple(parts) if parts else None


def get_capcut_process_count() -> int:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/NH", "/FO", "CSV"],
            text=True,
            errors="ignore",
        )
        return sum(1 for line in out.splitlines() if "capcut.exe" in line.lower())
    except Exception:
        return -1


def get_installed_capcut_versions():
    if not APPS_DIR.exists():
        return []
    versions = []
    for p in APPS_DIR.iterdir():
        if p.is_dir():
            vt = parse_version_tuple(p.name)
            if vt is not None:
                versions.append((vt, p.name))
    versions.sort(key=lambda x: x[0])
    return versions


def check_draft_plaintext(draft_dir: pathlib.Path):
    """Returns (is_ok, details_dict) verifying both root and Timelines/*/draft_content.json start with '{'."""
    root_dc = draft_dir / "draft_content.json"
    result = {
        "draft": draft_dir.name,
        "exists": draft_dir.exists(),
        "root_plaintext": False,
        "timelines_checked": 0,
        "timelines_plaintext": True,
        "encrypted_paths": [],
    }
    if not root_dc.exists():
        return False, result

    b0 = root_dc.open("rb").read(1)
    result["root_plaintext"] = (b0 == b"{")
    if not result["root_plaintext"]:
        result["encrypted_paths"].append(str(root_dc))

    for tdc in sorted(draft_dir.glob("Timelines/*/draft_content.json")):
        result["timelines_checked"] += 1
        tb0 = tdc.open("rb").read(1)
        if tb0 != b"{":
            result["timelines_plaintext"] = False
            result["encrypted_paths"].append(str(tdc))

    is_ok = result["root_plaintext"] and result["timelines_plaintext"]
    return is_ok, result


def validate_media_paths(paths, allowed_vehicle_dir: pathlib.Path | None = None):
    """Ensures all media files exist, none match the AI-slop / unrelated stock blocklist,
    and (when allowed_vehicle_dir is given) all vehicle raw footage/images reside strictly inside
    the designated Google Drive vehicle folder index directory."""
    issues = []
    allowed_resolved = allowed_vehicle_dir.resolve() if allowed_vehicle_dir else None
    for p in paths:
        pp = pathlib.Path(p)
        if not pp.exists():
            issues.append(f"missing_file:{pp}")
        for blocked in AI_SLOP_BLOCKLIST:
            if blocked.lower() in pp.name.lower():
                issues.append(f"blocked_ai_or_stock_media:{pp.name}")
        if allowed_resolved is not None and pp.exists():
            try:
                pp.resolve().relative_to(allowed_resolved)
            except ValueError:
                issues.append(f"outside_designated_vehicle_index:{pp}")
    return len(issues) == 0, issues


def run_preflight(check_snapshot: bool = False):
    proc_cnt = get_capcut_process_count()
    versions = get_installed_capcut_versions()
    highest_tuple, highest_str = versions[-1] if versions else ((0,), "unknown")
    all_version_strs = [v[1] for v in versions]

    status = "ok"
    warnings = []
    errors = []

    if highest_tuple and highest_tuple[0] >= 10:
        status = "blocked_v10"
        errors.append(f"CapCut 10.x detected ({highest_str}): external draft writing is strictly blocked per HERMES.md Rule 3-3.")
    elif highest_tuple > VERIFIED_MAX_VERSION:
        status = "needs_smoke_retest"
        warnings.append(f"CapCut version {highest_str} is newer than verified {'.'.join(map(str, VERIFIED_MAX_VERSION))}. Re-run Phase 1 smoke test before deploying.")

    can_write_drafts_dir = (proc_cnt == 0) and (status == "ok")

    snapshot_changed = False
    if check_snapshot:
        prev = []
        if SNAPSHOT_FILE.exists():
            try:
                prev = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8")).get("versions", [])
            except Exception:
                prev = []
        if prev != all_version_strs:
            snapshot_changed = True
            SNAPSHOT_FILE.write_text(
                json.dumps({"highest": highest_str, "versions": all_version_strs}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    report = {
        "status": status,
        "capcut_process_count": proc_cnt,
        "can_write_to_com_lveditor_draft": can_write_drafts_dir,
        "highest_version": highest_str,
        "verified_max_version": ".".join(map(str, VERIFIED_MAX_VERSION)),
        "installed_versions": all_version_strs,
        "snapshot_changed": snapshot_changed,
        "warnings": warnings,
        "errors": errors,
    }
    return report


def _sync_root_meta_info(dst: pathlib.Path) -> None:
    """Upserts a deployed hermes_*/pycapcut_smoke_* draft into DRAFT_ROOT/root_meta_info.json when plaintext."""
    rmi_path = DRAFT_ROOT / "root_meta_info.json"
    dmi_path = dst / "draft_meta_info.json"
    if not rmi_path.exists() or not dmi_path.exists():
        return
    try:
        if rmi_path.open("rb").read(1) != b"{":
            return
        rmi = json.loads(rmi_path.read_text(encoding="utf-8"))
        dmi = json.loads(dmi_path.read_text(encoding="utf-8"))
    except Exception:
        return
    store = rmi.get("all_draft_store")
    if not isinstance(store, list):
        return
    now_us = int(time.time() * 1_000_000)
    fold_fwd = str(dst.resolve()).replace("\\", "/")
    root_fwd = str(DRAFT_ROOT.resolve()).replace("\\", "/")
    existing = next((item for item in store if isinstance(item, dict) and item.get("draft_name") == dst.name), None)
    entry = dict(existing) if existing else {
        "cloud_draft_cover": False,
        "cloud_draft_sync": False,
        "draft_cloud_last_action_download": False,
        "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_is_ai_shorts": False,
        "draft_is_cloud_temp_draft": False,
        "draft_is_infinite_canvas_draft": False,
        "draft_is_invisible": False,
        "draft_is_pippit_draft": False,
        "draft_is_web_article_video": False,
        "draft_new_version": "",
        "draft_timeline_materials_size": 0,
        "draft_type": "",
        "draft_web_article_video_enter_from": "",
        "pippit_avatar_url": "",
        "pippit_extra_info": "",
        "pippit_id": "",
        "pippit_user_name": "",
        "streaming_edit_draft_ready": True,
        "tm_draft_cloud_completed": "",
        "tm_draft_cloud_entry_id": 0,
        "tm_draft_cloud_modified": 0,
        "tm_draft_cloud_parent_entry_id": -1,
        "tm_draft_cloud_space_id": -1,
        "tm_draft_cloud_user_id": -1,
        "tm_draft_create": now_us,
        "tm_draft_removed": 0,
    }
    entry.update({
        "draft_cover": f"{fold_fwd}\\draft_cover.jpg",
        "draft_fold_path": fold_fwd,
        "draft_id": dmi.get("draft_id") or entry.get("draft_id") or "",
        "draft_json_file": f"{fold_fwd}\\draft_content.json",
        "draft_name": dst.name,
        "draft_root_path": root_fwd,
        "streaming_edit_draft_ready": True,
        "tm_draft_modified": now_us,
        "tm_draft_removed": 0,
        "tm_duration": int(dmi.get("tm_duration") or 0),
    })
    if existing is not None:
        store.remove(existing)
    store.insert(0, entry)
    rmi["draft_ids"] = len(store)
    tmp = rmi_path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(rmi, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, rmi_path)


def deploy_staged(names, force: bool = False):
    """Copies staged drafts (capcut_stage/<name>) into CapCut's draft folder, only while CapCut is closed.
    A draft that is already deployed is moved to capcut_stage/_replaced/<name>_<time> first, so edits made in
    CapCut are never deleted. `force=True` permits deploying on an unverified minor 9.x update (never while CapCut
    is running or on CapCut 10.x+). Returns {name: deployed_path} for the drafts actually deployed."""
    pf = run_preflight(check_snapshot=False)
    can_deploy = pf["can_write_to_com_lveditor_draft"] or (
        force and pf["capcut_process_count"] == 0 and pf["status"] == "needs_smoke_retest"
    )
    if not can_deploy:
        extra_hint = " --force" if pf["capcut_process_count"] == 0 and pf["status"] == "needs_smoke_retest" else ""
        why = "close CapCut and " if pf["capcut_process_count"] != 0 else ""
        print(f"[SKIP DEPLOY] status={pf['status']} capcut_processes={pf['capcut_process_count']} "
              f"warnings={pf['warnings']} errors={pf['errors']} -> staged only in {STAGE_DIR}; "
              f"{why}run: py preflight_check.py --deploy {' '.join(names)}{extra_hint}")
        return {}
    DRAFT_ROOT.mkdir(parents=True, exist_ok=True)
    deployed = {}
    for name in names:
        if not name.startswith(("hermes_", "pycapcut_smoke_")):  # HERMES rule 3-2: only our own drafts
            print(f"[SKIP DEPLOY] {name}: only hermes_* / pycapcut_smoke_* drafts are deployed")
            continue
        src, dst = STAGE_DIR / name, DRAFT_ROOT / name
        if not src.exists():
            print(f"[SKIP DEPLOY] {name}: not staged at {src}")
            continue
        if dst.exists():
            backup = STAGE_DIR / "_replaced" / f"{name}_{time.strftime('%Y%m%d_%H%M%S')}"
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(backup))
            print(f"    previous {name} kept at {backup}")
        shutil.copytree(src, dst)
        sys.path.insert(0, str(WORK_DIR))
        from portable_paths import rewrite_foreign_user_paths
        for dc_file in [dst / "draft_content.json", *(dst / "Timelines").glob("*/draft_content.json")]:
            if dc_file.exists():
                raw_dc = json.loads(dc_file.read_text(encoding="utf-8"))
                rebased_dc = rewrite_foreign_user_paths(raw_dc)
                if rebased_dc != raw_dc:
                    dc_file.write_text(json.dumps(rebased_dc, ensure_ascii=False), encoding="utf-8")
        _sync_root_meta_info(dst)
        ok_pt, _ = check_draft_plaintext(dst)
        deployed[name] = str(dst)
        print(f"    -> Deployed CapCut draft to {dst} (plaintext={ok_pt})")
    return deployed


def main():
    parser = argparse.ArgumentParser(description="Pre-flight check for CapCut & video automation pipeline.")
    parser.add_argument("--snapshot", action="store_true", help="Compare & update CapCut Apps version snapshot.")
    parser.add_argument("--quiet-if-unchanged", action="store_true", help="Print only if version changed or error exists.")
    parser.add_argument("--check-draft", type=str, default=None, help="Verify plaintext status of a specific draft name.")
    parser.add_argument("--deploy", nargs="+", metavar="DRAFT", help="Deploy already-staged drafts (no rebuild), e.g. hermes_cybertruck_optic_longform.")
    parser.add_argument("--force", action="store_true", help="Allow --deploy when CapCut is closed on an unverified 9.x minor update.")
    args = parser.parse_args()

    if args.deploy:  # the output check first, as the builders do (a draft that breaks a rule is not deployed)
        import re
        import check_text_outputs
        for name in args.deploy:
            m = re.fullmatch(r"hermes_(.+)_optic_(longform|wide1|shorts)", name)
            bad = check_text_outputs.check_draft(m[1], m[2]) if m else []
            if bad:
                sys.exit(f"[검사 실패] {name}: 규칙 검사를 통과하지 못해 배포하지 않습니다\n" + "\n".join(bad))
        sys.exit(0 if len(deploy_staged(args.deploy, force=args.force)) == len(args.deploy) else 1)

    report = run_preflight(check_snapshot=args.snapshot)
    if args.check_draft:
        dpath = DRAFT_ROOT / args.check_draft
        ok, dinfo = check_draft_plaintext(dpath)
        report["draft_check"] = dinfo
        if not ok:
            report["errors"].append(f"Draft '{args.check_draft}' is missing or encrypted.")

    if args.quiet_if_unchanged and not report["snapshot_changed"] and not report["errors"]:
        return

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
