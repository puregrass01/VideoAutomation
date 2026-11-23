"""The pyCapCut #13 media-bin link, shared by build_longform.py and build_shorts.py."""
import pathlib
import time
import uuid


def populate_draft_materials(dc: dict, dm: dict):
    """Fixes pyCapCut #13: populates local_material_id in draft_content.json and draft_materials in draft_meta_info.json."""
    now_s = int(time.time())
    now_us = int(time.time() * 1_000_000)
    type0_values = []

    for vm in dc.get("materials", {}).get("videos", []):
        lmid = vm.get("local_material_id") or str(uuid.uuid4())
        vm["local_material_id"] = lmid
        vpath = vm.get("path", "").replace("\\", "/")
        dur = int(vm.get("duration", 0))
        type0_values.append({
            "ai_group_type": "",
            "create_time": now_s,
            "duration": dur,
            "enter_from": 0,
            "extra_info": pathlib.Path(vpath).name if vpath else vm.get("material_name", ""),
            "file_Path": vpath,
            "height": int(vm.get("height", 1920)),
            "id": lmid,
            "import_time": now_s,
            "import_time_ms": now_us,
            "item_source": 1,
            "material_color_tag": "",
            "md5": "",
            "metetype": "video" if vm.get("type", "video") == "video" else "photo",
            "roughcut_time_range": {"duration": dur, "start": 0},
            "sub_time_range": {"duration": -1, "start": -1},
            "type": 0,
            "width": int(vm.get("width", 1080)),
        })

    for am in dc.get("materials", {}).get("audios", []):
        lmid = am.get("local_material_id") or am.get("id") or str(uuid.uuid4())
        am["local_material_id"] = lmid
        apath = am.get("path", "").replace("\\", "/")
        dur = int(am.get("duration", 0))
        type0_values.append({
            "ai_group_type": "",
            "create_time": now_s,
            "duration": dur,
            "enter_from": 0,
            "extra_info": pathlib.Path(apath).name if apath else am.get("name", ""),
            "file_Path": apath,
            "height": 0,
            "id": lmid,
            "import_time": now_s,
            "import_time_ms": now_us,
            "item_source": 1,
            "material_color_tag": "",
            "md5": "",
            "metetype": "music",
            "roughcut_time_range": {"duration": dur, "start": 0},
            "sub_time_range": {"duration": -1, "start": -1},
            "type": 0,
            "width": 0,
        })

    dm["draft_materials"] = [
        {"type": 0, "value": type0_values},
        {"type": 1, "value": []},
        {"type": 2, "value": []},
        {"type": 3, "value": []},
        {"type": 6, "value": []},
        {"type": 7, "value": []},
        {"type": 8, "value": []},
    ]
