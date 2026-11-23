"""
Concurrency, Thread-Safety, and Stress Harness for OpticGlass Video Automation Pipeline.
Empirical verification suite for Challenger 1.
"""

import concurrent.futures
import json
import os
import pathlib
import sys
import tempfile
import threading
import time
import unittest

# Ensure work directory is in sys.path
WORK_DIR = pathlib.Path(__file__).resolve().parent
if str(WORK_DIR) not in sys.path:
    sys.path.insert(0, str(WORK_DIR))

import longform_common as lc
import make_scenario as ms
import gdrive_pipeline as gp


class TestAtomicWriteJsonConcurrency(unittest.TestCase):
    """Stress test atomic_write_json under high multithreaded and multiprocess concurrency."""

    def setUp(self):
        self.test_dir = pathlib.Path(tempfile.mkdtemp(prefix="test_atomic_json_"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_high_concurrency_same_file(self):
        """20 concurrent threads writing distinct payloads to the SAME destination path."""
        target_file = self.test_dir / "target.json"
        num_threads = 20
        iterations = 5
        barrier = threading.Barrier(num_threads)
        errors = []

        def worker(thread_id):
            try:
                for it in range(iterations):
                    barrier.wait(timeout=10.0)
                    data = {
                        "thread_id": thread_id,
                        "iteration": it,
                        "timestamp": time.time_ns(),
                        "payload": [x for x in range(100)],
                    }
                    lc.atomic_write_json(target_file, data)
            except Exception as e:
                errors.append((thread_id, e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30.0)

        self.assertEqual(len(errors), 0, f"Thread errors encountered: {errors}")
        self.assertTrue(target_file.exists(), "Target file must exist after writes")

        # Verify final file is valid JSON
        with open(target_file, "r", encoding="utf-8") as f:
            final_data = json.load(f)
        self.assertIn("thread_id", final_data)
        self.assertIn("payload", final_data)
        self.assertEqual(len(final_data["payload"]), 100)

        # Verify no temp files leaked
        tmp_files = list(self.test_dir.glob("*.tmp"))
        self.assertEqual(len(tmp_files), 0, f"Leaked temp files found: {tmp_files}")

    def test_extreme_concurrency_and_temp_cleanup(self):
        """50 concurrent threads hammering atomic_write_json on the same file."""
        target_file = self.test_dir / "hammer.json"
        num_threads = 50
        errors = []

        def hammer(tid):
            try:
                data = {"tid": tid, "ts": time.time_ns(), "blob": "A" * 5000}
                lc.atomic_write_json(target_file, data)
            except Exception as e:
                errors.append((tid, e))

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as ex:
            futs = [ex.submit(hammer, i) for i in range(num_threads)]
            concurrent.futures.wait(futs)

        self.assertEqual(len(errors), 0, f"Errors in 50-thread hammer: {errors}")
        self.assertTrue(target_file.exists())
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("tid", data)
        self.assertEqual(len(data["blob"]), 5000)

        # Verify no temp files leaked
        tmp_files = list(self.test_dir.glob("*.tmp"))
        self.assertEqual(len(tmp_files), 0, f"Leaked temp files found: {tmp_files}")

    def test_multiprocess_atomic_write_concurrency(self):
        """Separate Python processes concurrently calling atomic_write_json on the same file."""
        import subprocess
        target_file = self.test_dir / "multiprocess_target.json"
        num_procs = 5
        py_code = f"""
import sys, time, pathlib
sys.path.insert(0, r"{WORK_DIR}")
import longform_common as lc
target = pathlib.Path(r"{target_file}")
for i in range(10):
    lc.atomic_write_json(target, {{"proc_pid": "{os.getpid()}", "iteration": i, "payload": "X" * 1000}})
    time.sleep(0.01)
"""
        procs = [
            subprocess.Popen([sys.executable, "-c", py_code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for _ in range(num_procs)
        ]
        for p in procs:
            out, err = p.communicate(timeout=30)
            self.assertEqual(p.returncode, 0, f"Process failed with stderr: {err.decode('utf-8', errors='replace')}")

        self.assertTrue(target_file.exists())
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("proc_pid", data)
        self.assertEqual(len(data["payload"]), 1000)

        tmp_files = list(self.test_dir.glob("*.tmp"))
        self.assertEqual(len(tmp_files), 0, f"Leaked temp files after multiprocess run: {tmp_files}")


class TestGetMovMetaCachedConcurrency(unittest.TestCase):
    """Stress test get_mov_meta_cached thread safety and cache coherency."""

    def setUp(self):
        self.test_dir = pathlib.Path(tempfile.mkdtemp(prefix="test_mov_meta_"))
        # Create dummy MOV files
        self.mov_files = []
        for i in range(5):
            p = self.test_dir / f"clip_{i}.mov"
            p.write_bytes(b"\x00" * 1024)  # 1KB dummy
            self.mov_files.append(p)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_concurrent_cache_access_and_population(self):
        """Multiple threads concurrently calling get_mov_meta_cached on the same & different files."""
        # Mock cv2.VideoCapture so we don't need real H.264 video streams for probing
        import cv2

        class MockCap:
            def __init__(self, path):
                self.path = path
            def get(self, prop):
                if prop == cv2.CAP_PROP_FRAME_COUNT:
                    return 300
                elif prop == cv2.CAP_PROP_FPS:
                    return 30
                elif prop == cv2.CAP_PROP_FRAME_WIDTH:
                    return 3840
                elif prop == cv2.CAP_PROP_FRAME_HEIGHT:
                    return 2160
                return 0
            def release(self):
                pass

        orig_cap = cv2.VideoCapture
        cv2.VideoCapture = MockCap
        try:
            num_threads = 25
            barrier = threading.Barrier(num_threads)
            results = []
            errors = []

            def worker(tid):
                try:
                    barrier.wait(timeout=10.0)
                    mov_f = self.mov_files[tid % len(self.mov_files)]
                    meta = lc.get_mov_meta_cached(mov_f)
                    results.append((tid, mov_f.name, meta))
                except Exception as e:
                    errors.append((tid, e))

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=30.0)

            self.assertEqual(len(errors), 0, f"Errors in concurrent get_mov_meta_cached: {errors}")
            self.assertEqual(len(results), num_threads)
            for tid, name, meta in results:
                self.assertEqual(meta, (10000000, 3840, 2160))

            # Verify the cache file is intact and valid JSON
            cache_file = self.test_dir / ".mov_meta_cache.json"
            self.assertTrue(cache_file.exists())
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)

            # Each of the 5 files should have an entry in the cache
            self.assertEqual(len(cache), 5)
            for p in self.mov_files:
                st = p.stat()
                key = f"{p.name}:{st.st_mtime_ns}:{st.st_size}"
                self.assertIn(key, cache)
                self.assertEqual(cache[key], [10000000, 3840, 2160])
        finally:
            cv2.VideoCapture = orig_cap


class TestBoundedThreadExecution(unittest.TestCase):
    """prepare_scene_clips order and build_if_stale under two writers."""

    def test_prepare_scene_clips_order_preservation(self):
        """prepare_scene_clips must preserve exact scene order."""
        scenes = [
            {"id": f"s{i:02d}", "name": f"test_{i}", "src": "outro", "start": i * 3.0, "dur": 3.0}
            for i in range(12)
        ]
        # Mock build_if_stale and trim_video_16x9
        test_dir = pathlib.Path(tempfile.mkdtemp(prefix="test_order_"))
        try:
            raw_dir = test_dir / "raw"
            raw_dir.mkdir()
            media_dir = test_dir / "media"
            media_dir.mkdir()
            outro_src = raw_dir / "outro.mp4"
            outro_src.write_bytes(b"\x00" * 1024)

            # Patch build_if_stale to simulate random latency
            import random
            orig_build_if_stale = lc.build_if_stale

            def mock_build_if_stale(out_p, builder, dur_s, deps, key=""):
                time.sleep(random.uniform(0.005, 0.02))
                out_p.write_bytes(b"\x00" * 20000)
                return True

            lc.build_if_stale = mock_build_if_stale
            try:
                res = lc.prepare_scene_clips(scenes, raw_dir, media_dir, outro_src)
                self.assertEqual(len(res), len(scenes))
                for i, r in enumerate(res):
                    self.assertEqual(r["id"], f"s{i:02d}", f"Scene order violated at index {i}: expected s{i:02d}, got {r['id']}")
                    self.assertEqual(r["start"], i * 3.0)
            finally:
                lc.build_if_stale = orig_build_if_stale
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_build_if_stale_same_out_two_threads(self):
        """Two runs of the same car building one clip at once: both finish, the clip is one writer's whole bytes, no .part left."""
        test_dir = pathlib.Path(tempfile.mkdtemp(prefix="test_stale_"))
        try:
            out_p = test_dir / "lf_s01_x.mp4"
            barrier = threading.Barrier(2)
            errors = []

            def slow_builder(tag):
                def build(part, dur_s):
                    with open(part, "wb") as f:
                        for _ in range(20):
                            f.write(tag * 1000)
                            time.sleep(0.005)
                return build

            def worker(tag):
                try:
                    barrier.wait(timeout=10.0)
                    self.assertTrue(lc.build_if_stale(out_p, slow_builder(tag), 1.0, []))
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=worker, args=(t,)) for t in (b"A", b"B")]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=30.0)
            self.assertEqual(errors, [])
            self.assertIn(out_p.read_bytes(), (b"A" * 20000, b"B" * 20000))
            self.assertEqual(list(test_dir.glob("*.part*")), [])
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_make_scenario_has_os(self):
        """make_scenario's clip-building path uses os (it once failed with a missing import on every new car)."""
        self.assertIs(ms.os, os)


class TestLockIntegrityAndDeadlockFreedom(unittest.TestCase):
    """Stress test absence of deadlocks across all modules."""

    def test_gauge_lock_no_deadlock(self):
        """gp.gauge's at() callback must safely output without deadlocking across multiple concurrent callers."""
        at = gp.gauge({"step_a": 50, "step_b": 50})
        num_threads = 20

        def log_worker(tid):
            for i in range(10):
                step = "step_a" if i < 5 else "step_b"
                at(step, (i % 5) / 5.0, f"Thread {tid} step {i}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as ex:
            futs = [ex.submit(log_worker, tid) for tid in range(num_threads)]
            concurrent.futures.wait(futs, timeout=10.0)
            for f in futs:
                self.assertIsNone(f.exception())


if __name__ == "__main__":
    unittest.main()
