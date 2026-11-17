"""Small integration checks using original public examples. No image service calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills/assetrefgen/scripts/roster_tools.py"
REF = ROOT / "skills/assetrefgen/scripts/reference_tools.py"
E = ROOT / "examples"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PublicExamplesTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="assetrefgen-examples-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name).resolve()

    def run_cli(self, *args, code=0, cli=CLI):
        result = subprocess.run([sys.executable, "-X", "utf8", "-B", str(cli), *map(str, args)],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(code, result.returncode, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout else None

    def test_distinct_rosters_and_single_identity_multiview(self):
        cases = {"single": 1, "characters": 3, "objects": 2, "folder": 5,
                 "multiview": 1, "repeated-folder": 3}
        for name, count in cases.items():
            with self.subTest(name=name):
                inventory_path = E / f"{name}.inventory.json"
                before = sha(inventory_path)
                batch = self.work / name
                state = self.run_cli("init", batch, "--inventory", inventory_path)
                self.assertEqual(count, state["actual_count"])
                saved = json.loads((batch / "roster.json").read_bytes())
                self.assertEqual(count, len(saved["assets"]))
                spec = json.loads(inventory_path.read_bytes())
                sources = {s["id"]: E / s["path"] for s in spec["sources"]}
                for asset in spec["assets"]:
                    folder = batch / "assets" / asset["id"]
                    manifest = json.loads((folder / "manifest.json").read_bytes())
                    self.assertEqual(len(asset["regions"]), len(manifest["regions"]))
                    for source in manifest["sources"]:
                        self.assertEqual(sha(sources[source["source_id"]]), sha(folder / source["path"]))
                    for region in manifest["regions"]:
                        with Image.open(sources[region["source_id"]]) as original:
                            with ImageOps.exif_transpose(original) as oriented:
                                with oriented.crop(region["box"]) as expected:
                                    with Image.open(folder / region["crop"]) as actual:
                                        self.assertEqual(expected.convert("RGBA").tobytes(), actual.convert("RGBA").tobytes())
                self.assertEqual(before, sha(inventory_path))
                repeat = self.run_cli("init", batch, "--inventory", inventory_path)
                self.assertEqual(state["actual_count"], repeat["actual_count"])

    def test_real_single_output_integrity_and_no_mirroring(self):
        folder = E / "kiln-traveler"
        report = self.run_cli("audit", folder, cli=REF)
        self.assertTrue(report["file_checks_passed"])
        self.assertEqual(sha(folder / "master_front.png"), sha(folder / "front.png"))
        with Image.open(folder / "left.png") as left, Image.open(folder / "right.png") as right:
            self.assertNotEqual(ImageOps.mirror(left).tobytes(), right.tobytes())
        with Image.open(folder / "contact_sheet.png") as native, Image.open(folder / "contact_preview.png") as preview:
            expected = native.copy()
            expected.thumbnail((1800, 1200), Image.Resampling.LANCZOS)
            self.assertEqual(expected.tobytes(), preview.tobytes())

    def test_resume_imports_existing_outputs_without_regeneration(self):
        batch = self.work / "single"
        asset_id = "kiln-traveler"
        self.run_cli("init", batch, "--inventory", E / "single.inventory.json")
        folder = batch / "assets" / asset_id
        originals = E / asset_id
        for index, name in enumerate(("master_front.png", "front.png", "left.png", "back.png", "right.png")):
            before = {p.name: sha(p) for p in folder.glob("*.png")}
            self.run_cli("adopt", batch, asset_id, "--file", name, "--record-id", f"import-{index}",
                         "--source", originals / name, "--origin", "reused" if name == "front.png" else "imported",
                         "--notes", "Reuse reviewed public demo; no service call in this test.")
            # Simulate the interruption window between selected output and checkpoint.
            self.run_cli("resume", batch)
            task = self.run_cli("next", batch)["task"]
            self.assertEqual("reconcile", task["kind"])
            self.assertEqual(name, task["filename"])
            self.run_cli("checkpoint", batch, asset_id, "--qa", "pending", "--visual-reviewed",
                         "--notes", "Public demo selection has already been visually reviewed; minor Quick caveats retained.")
            for old, digest in before.items():
                self.assertEqual(digest, sha(folder / old))
            self.assertEqual(sha(originals / name), sha(folder / name))
        self.run_cli("sheet", batch, asset_id)
        self.run_cli("checkpoint", batch, asset_id, "--qa", "pass", "--visual-reviewed", "--sheet-current",
                     "--notes", "Reused actual reviewed demo; orthographic geometry unverified and small seam/hand drift remains.")
        all_hashes = {p.relative_to(batch).as_posix(): sha(p) for p in batch.rglob("*") if p.is_file()}
        self.run_cli("resume", batch)
        next_work = self.run_cli("next", batch)
        self.assertIsNone(next_work["task"])
        self.assertEqual([asset_id], next_work["complete"])
        self.assertEqual(all_hashes, {p.relative_to(batch).as_posix(): sha(p) for p in batch.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main(verbosity=2)
