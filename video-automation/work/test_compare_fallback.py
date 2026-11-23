"""Offline unit & integration tests for cross-vehicle before/after comparing-scene fallback."""
import contextlib
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

from PIL import Image

WORK = pathlib.Path(__file__).resolve().parent
if str(WORK) not in sys.path:
    sys.path.insert(0, str(WORK))

import build_longform  # noqa: E402
import check_text_outputs as cto  # noqa: E402
import drive_index  # noqa: E402
import longform_common as lc  # noqa: E402
import make_scenario  # noqa: E402
import portable_paths  # noqa: E402
import thumb_photos as tp  # noqa: E402


def _make_jpg(path: pathlib.Path, color: tuple[int, int, int] = (80, 120, 160), size: tuple[int, int] = (640, 480)) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, quality=90)
    return path.stat().st_size


@contextlib.contextmanager
def _isolated_env():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        media = root / "media"
        scenarios = root / "scenarios"
        media.mkdir()
        shutil.copytree(lc.SCENARIOS_DIR / "templates", scenarios / "templates")
        links_f = root / "drive_folders.json"
        links_f.write_text("{}", encoding="utf-8")

        orig = {
            "pp_media": portable_paths.MEDIA_DIR,
            "lc_media": lc.MEDIA_DIR,
            "di_media": drive_index.MEDIA_DIR,
            "di_links": drive_index.LINKS,
            "lc_scen": lc.SCENARIOS_DIR,
        }
        portable_paths.MEDIA_DIR = media
        lc.MEDIA_DIR = media
        drive_index.MEDIA_DIR = media
        drive_index.LINKS = links_f
        lc.SCENARIOS_DIR = scenarios
        try:
            yield root, media, scenarios, links_f
        finally:
            portable_paths.MEDIA_DIR = orig["pp_media"]
            lc.MEDIA_DIR = orig["lc_media"]
            drive_index.MEDIA_DIR = orig["di_media"]
            drive_index.LINKS = orig["di_links"]
            lc.SCENARIOS_DIR = orig["lc_scen"]


class TestCompareFallback(unittest.TestCase):
    def test_donor_stills_discovers_nested_and_excludes_target_frames_and_ai_slop(self):
        with _isolated_env() as (_, media, _, links_f):
            links = {
                "target_car": {"folder_id": "1", "folder_name": "16 아우디 테스트", "car_name": "아우디 테스트", "media": "0.옵틱 광각/16 아우디 테스트"},
                "donor_flat": {"folder_id": "2", "folder_name": "볼보 테스트", "car_name": "볼보 테스트"},
            }
            links_f.write_text(json.dumps(links, ensure_ascii=False), encoding="utf-8")

            # Target has mirror_before/after in review.json (must be excluded by donor_stills)
            t_raw = media / "0.옵틱 광각" / "16 아우디 테스트" / "gdrive_raw"
            sz_t = _make_jpg(t_raw / "t_mb.jpg")
            t_rev = {f"{tp.REVIEW_VERSION}|t_mb.jpg|{sz_t}": {"kind": "mirror_before", "score": 9, "mirror": [100, 100, 500, 500]}}
            (t_raw.parent / "thumb").mkdir(parents=True)
            (t_raw.parent / "thumb" / "review.json").write_text(json.dumps(t_rev), encoding="utf-8")

            # Donor flat: valid standalone photo + _frames entry (ignored) + AI slop name (ignored)
            df_raw = media / "donor_flat" / "gdrive_raw"
            sz_mb = _make_jpg(df_raw / "stock.jpg", (40, 40, 40))
            sz_fr = _make_jpg(df_raw / "_frames" / "clip_001.0s.jpg", (50, 50, 50))
            sz_slop = _make_jpg(df_raw / "kling_fake.jpg", (60, 60, 60))
            df_rev = {
                f"{tp.REVIEW_VERSION}|stock.jpg|{sz_mb}": {"kind": "mirror_before", "score": 7, "mirror": [200, 200, 800, 800]},
                f"{tp.REVIEW_VERSION}|_frames/clip_001.0s.jpg|{sz_fr}": {"kind": "mirror_after", "score": 10},
                f"{tp.REVIEW_VERSION}|kling_fake.jpg|{sz_slop}": {"kind": "mirror_after", "score": 10},
            }
            (df_raw.parent / "thumb").mkdir(parents=True)
            (df_raw.parent / "thumb" / "review.json").write_text(json.dumps(df_rev), encoding="utf-8")

            # Donor nested (unlinked directory under 0.옵틱 광각/)
            dn_raw = media / "0.옵틱 광각" / "21 벤츠 테스트" / "gdrive_raw"
            sz_ma = _make_jpg(dn_raw / "optic.jpg", (120, 180, 220))
            dn_rev = {f"{tp.REVIEW_VERSION}|optic.jpg|{sz_ma}": {"kind": "mirror_after", "score": 8, "mirror": [250, 250, 750, 750]}}
            (dn_raw.parent / "thumb").mkdir(parents=True)
            (dn_raw.parent / "thumb" / "review.json").write_text(json.dumps(dn_rev), encoding="utf-8")

            donors = make_scenario.donor_stills("target_car")
            srcs = {d["src"] for d in donors}
            self.assertEqual(
                srcs,
                {
                    "@media/donor_flat/gdrive_raw/stock.jpg",
                    "@media/0.옵틱 광각/21 벤츠 테스트/gdrive_raw/optic.jpg",
                },
            )
            for d in donors:
                self.assertTrue(lc.resolve_scene_src(t_raw, d["src"]).is_file())

    def test_fallback_on_wide1_and_other_template_comparing_scenes(self):
        with _isolated_env() as (_, media, scenarios, links_f):
            links = {
                "target_car": {"folder_id": "1", "folder_name": "16 아우디 테스트", "car_name": "아우디 테스트", "media": "0.옵틱 광각/16 아우디 테스트"},
                "donor_a": {"folder_id": "2", "folder_name": "도너 A", "car_name": "도너 A"},
            }
            links_f.write_text(json.dumps(links, ensure_ascii=False), encoding="utf-8")

            t_raw = media / "0.옵틱 광각" / "16 아우디 테스트" / "gdrive_raw"
            sz_e = _make_jpg(t_raw / "ext.jpg", (10, 20, 30))
            sz_d = _make_jpg(t_raw / "det.jpg", (30, 20, 10))
            t_review = {
                "ext.jpg": {"kind": "car_exterior", "score": 8},
                "det.jpg": {"kind": "car_detail", "score": 8},
            }

            d_raw = media / "donor_a" / "gdrive_raw"
            sz_mb = _make_jpg(d_raw / "mb.jpg", (90, 90, 90))
            sz_ma = _make_jpg(d_raw / "ma.jpg", (200, 200, 200))
            d_rev = {
                f"{tp.REVIEW_VERSION}|mb.jpg|{sz_mb}": {"kind": "mirror_before", "score": 7, "mirror": [200, 200, 700, 700]},
                f"{tp.REVIEW_VERSION}|ma.jpg|{sz_ma}": {"kind": "mirror_after", "score": 9, "mirror": [250, 250, 750, 750]},
            }
            (d_raw.parent / "thumb").mkdir(parents=True)
            (d_raw.parent / "thumb" / "review.json").write_text(json.dumps(d_rev), encoding="utf-8")

            wide1_skel = json.loads((scenarios / "templates" / "opticglass_wide1" / "skeleton.json").read_text(encoding="utf-8"))
            scenes = make_scenario.plan("target_car", t_review, wide1_skel)
            for sc in scenes[:6]:
                self.assertIn(sc["src"], {"ext.jpg", "det.jpg"})
            for sc in scenes[6:-1]:
                if sc["role"] == "compare_before":
                    self.assertEqual(sc["src"], "@media/donor_a/gdrive_raw/mb.jpg")
                elif sc["role"] == "compare_after":
                    self.assertEqual(sc["src"], "@media/donor_a/gdrive_raw/ma.jpg")
                elif sc["role"] == "split":
                    self.assertEqual(sc["src"], "@media/donor_a/gdrive_raw/mb.jpg")
                    self.assertEqual(sc["split"]["src_after"], "@media/donor_a/gdrive_raw/ma.jpg")

            # Also test non-wide1 template skeleton (e.g. porsche997_optic) with comparing scenes
            non_wide_skel = {
                "template": "porsche997_optic",
                "scenes": [
                    {"id": "s00", "role": "exterior", "start": 0.0, "dur": 4.0},
                    {"id": "s13", "role": "compare_before", "start": 4.0, "dur": 4.0},
                    {"id": "s14", "role": "compare_after", "start": 8.0, "dur": 4.0},
                    {"id": "s15", "role": "split", "start": 12.0, "dur": 4.0},
                    {"id": "s17", "role": "outro", "name": "outro", "start": 16.0, "dur": 5.0},
                ],
            }
            p_scenes = make_scenario.plan("target_car", t_review, non_wide_skel)
            self.assertEqual(p_scenes[0]["src"], "ext.jpg")
            self.assertEqual(p_scenes[1]["src"], "@media/donor_a/gdrive_raw/mb.jpg")
            self.assertEqual(p_scenes[2]["src"], "@media/donor_a/gdrive_raw/ma.jpg")
            self.assertEqual(p_scenes[3]["split"]["src_after"], "@media/donor_a/gdrive_raw/ma.jpg")

    def test_preserves_target_reference_when_present_even_with_lower_score(self):
        with _isolated_env() as (_, media, scenarios, links_f):
            links = {
                "target_car": {"folder_id": "1", "folder_name": "타겟차", "car_name": "타겟차"},
                "donor_a": {"folder_id": "2", "folder_name": "도너 A", "car_name": "도너 A"},
            }
            links_f.write_text(json.dumps(links, ensure_ascii=False), encoding="utf-8")

            t_raw = media / "target_car" / "gdrive_raw"
            _make_jpg(t_raw / "ext.jpg")
            _make_jpg(t_raw / "own_mb.jpg")
            _make_jpg(t_raw / "own_ma.jpg")
            t_review = {
                "ext.jpg": {"kind": "car_exterior", "score": 5},
                "own_mb.jpg": {"kind": "mirror_before", "score": 2, "mirror": [200, 200, 700, 700]},
                "own_ma.jpg": {"kind": "mirror_after", "score": 2, "mirror": [200, 200, 700, 700]},
            }

            d_raw = media / "donor_a" / "gdrive_raw"
            sz_mb = _make_jpg(d_raw / "donor_mb.jpg")
            sz_ma = _make_jpg(d_raw / "donor_ma.jpg")
            d_rev = {
                f"{tp.REVIEW_VERSION}|donor_mb.jpg|{sz_mb}": {"kind": "mirror_before", "score": 10},
                f"{tp.REVIEW_VERSION}|donor_ma.jpg|{sz_ma}": {"kind": "mirror_after", "score": 10},
            }
            (d_raw.parent / "thumb").mkdir(parents=True)
            (d_raw.parent / "thumb" / "review.json").write_text(json.dumps(d_rev), encoding="utf-8")

            wide1_skel = json.loads((scenarios / "templates" / "opticglass_wide1" / "skeleton.json").read_text(encoding="utf-8"))
            scenes = make_scenario.plan("target_car", t_review, wide1_skel)
            for sc in scenes:
                self.assertFalse(sc["src"].startswith(lc.MEDIA_SRC_PREFIX), f"unexpected fallback in {sc}")
                if "split" in sc and "src_after" in sc["split"]:
                    self.assertFalse(sc["split"]["src_after"].startswith(lc.MEDIA_SRC_PREFIX))

    def test_partial_missing_only_falls_back_for_missing_side(self):
        with _isolated_env() as (_, media, scenarios, links_f):
            links = {
                "target_car": {"folder_id": "1", "folder_name": "타겟차", "car_name": "타겟차"},
                "donor_a": {"folder_id": "2", "folder_name": "도너 A", "car_name": "도너 A"},
            }
            links_f.write_text(json.dumps(links, ensure_ascii=False), encoding="utf-8")

            t_raw = media / "target_car" / "gdrive_raw"
            _make_jpg(t_raw / "ext.jpg")
            _make_jpg(t_raw / "own_mb.jpg")
            t_review = {
                "ext.jpg": {"kind": "car_exterior", "score": 5},
                "own_mb.jpg": {"kind": "mirror_before", "score": 3},
            }

            d_raw = media / "donor_a" / "gdrive_raw"
            sz_mb = _make_jpg(d_raw / "donor_mb.jpg")
            sz_ma = _make_jpg(d_raw / "donor_ma.jpg")
            d_rev = {
                f"{tp.REVIEW_VERSION}|donor_mb.jpg|{sz_mb}": {"kind": "mirror_before", "score": 10},
                f"{tp.REVIEW_VERSION}|donor_ma.jpg|{sz_ma}": {"kind": "mirror_after", "score": 8},
            }
            (d_raw.parent / "thumb").mkdir(parents=True)
            (d_raw.parent / "thumb" / "review.json").write_text(json.dumps(d_rev), encoding="utf-8")

            wide1_skel = json.loads((scenarios / "templates" / "opticglass_wide1" / "skeleton.json").read_text(encoding="utf-8"))
            scenes = make_scenario.plan("target_car", t_review, wide1_skel)
            for sc in scenes:
                if sc["role"] == "compare_before":
                    self.assertEqual(sc["src"], "own_mb.jpg")
                elif sc["role"] == "compare_after":
                    self.assertEqual(sc["src"], "@media/donor_a/gdrive_raw/donor_ma.jpg")
                elif sc["role"] == "split":
                    self.assertEqual(sc["src"], "own_mb.jpg")
                    self.assertEqual(sc["split"]["src_after"], "@media/donor_a/gdrive_raw/donor_ma.jpg")

    def test_raises_short_footage_when_no_target_and_no_donor(self):
        with _isolated_env() as (_, media, scenarios, links_f):
            links_f.write_text(json.dumps({"target_car": {"folder_id": "1", "folder_name": "타겟차", "car_name": "타겟차"}}), encoding="utf-8")
            t_raw = media / "target_car" / "gdrive_raw"
            _make_jpg(t_raw / "ext.jpg")
            wide1_skel = json.loads((scenarios / "templates" / "opticglass_wide1" / "skeleton.json").read_text(encoding="utf-8"))
            with self.assertRaises(make_scenario.ShortFootage):
                make_scenario.plan("target_car", {"ext.jpg": {"kind": "car_exterior", "score": 5}}, wide1_skel)

    def test_e2e_resolve_missing_footage_prepare_clips_build_and_check(self):
        with _isolated_env() as (root, media, scenarios, links_f):
            links = {
                "audi_test": {"folder_id": "1", "folder_name": "16 아우디 테스트", "car_name": "아우디 Q5", "media": "0.옵틱 광각/16 아우디 테스트"},
                "donor_c40": {"folder_id": "2", "folder_name": "볼보 C40", "car_name": "볼보 C40"},
            }
            links_f.write_text(json.dumps(links, ensure_ascii=False), encoding="utf-8")

            t_raw = media / "0.옵틱 광각" / "16 아우디 테스트" / "gdrive_raw"
            _make_jpg(t_raw / "ext.jpg", (20, 40, 80), size=(1280, 720))
            d_raw = media / "donor_c40" / "gdrive_raw"
            sz_mb = _make_jpg(d_raw / "mb.jpg", (100, 100, 100), size=(1280, 720))
            sz_ma = _make_jpg(d_raw / "ma.jpg", (150, 200, 100), size=(1280, 720))
            (d_raw.parent / "thumb").mkdir(parents=True)
            (d_raw.parent / "thumb" / "review.json").write_text(json.dumps({
                f"{tp.REVIEW_VERSION}|mb.jpg|{sz_mb}": {"kind": "mirror_before", "score": 7, "mirror": [250, 200, 750, 800]},
                f"{tp.REVIEW_VERSION}|ma.jpg|{sz_ma}": {"kind": "mirror_after", "score": 7, "mirror": [250, 200, 750, 800]},
            }), encoding="utf-8")

            wide1_skel = json.loads((scenarios / "templates" / "opticglass_wide1" / "skeleton.json").read_text(encoding="utf-8"))
            scenes = make_scenario.plan("audi_test", {"ext.jpg": {"kind": "car_exterior", "score": 8}}, wide1_skel)
            for sc in scenes:
                if lc.ROLES[sc["role"]].get("arrows"):
                    sc["arrows"] = make_scenario.arrows_for(sc.pop("_fallback_box", None), "split" in sc)
                else:
                    sc.pop("_fallback_box", None)
                if sc["src"] != "outro":
                    self.assertTrue(make_scenario._is_static_scene(t_raw, sc))

            lines = [{"id": l["id"], "text": "아우디 Q5" if l["id"] == "lt01" else l["text"].replace("{car}", "아우디 Q5")}
                     for l in wide1_skel["lines"]]
            scen_obj = {"template": "opticglass_wide1", "car": {}, "scenes": scenes, "lines": lines}
            (scenarios / "audi_test_wide1.json").write_text(json.dumps(scen_obj, ensure_ascii=False), encoding="utf-8")

            # drive_index.missing_footage must resolve @media/ paths against MEDIA_DIR (no false missing footage)
            orig_di_work = drive_index.WORK_DIR
            drive_index.WORK_DIR = root
            try:
                self.assertEqual(drive_index.missing_footage("audi_test"), [])
            finally:
                drive_index.WORK_DIR = orig_di_work

            loaded = lc.load_scenario("audi_test_wide1")
            car = build_longform.Car("audi_test", loaded, draft_name="hermes_audi_test_optic_wide1", variant="wide1")
            car.media.mkdir(parents=True, exist_ok=True)
            # Test real clip preparation for a comparing scene + split scene using @media/ sources
            cmp_scenes = [s for s in loaded["scenes"] if s["role"] in ("compare_before", "compare_after", "split")][:3]
            prepared_cmp = lc.prepare_scene_clips(cmp_scenes, t_raw, car.media, build_longform.OUTRO_SRC)
            for pc in prepared_cmp:
                self.assertTrue(pc["path"].exists() and pc["path"].stat().st_size > 1000, f"missing clip {pc['path']}")

            # Build full CapCut draft & validate via check_text_outputs
            all_prepared = [
                {"id": x["id"], "start": x["start"], "dur": x["dur"], "path": car.media / f"lf_{x['id']}_{x['name']}.mp4",
                 "is_split_compare": "split" in x or x.get("compare", False)}
                for x in loaded["scenes"]
            ]
            stage = root / "stage"
            build_longform.build_capcut(car, all_prepared, stage_dir=stage)
            del cto.fails[:]
            cto.check_longform("audi_test", "hermes_audi_test_optic_wide1", variant="wide1", stage_dir=stage)
            self.assertEqual(cto.fails, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
