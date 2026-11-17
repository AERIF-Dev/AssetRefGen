"""Public CLI acceptance checks with local image fixtures; no generation calls."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from PIL import Image


CLI = Path(__file__).with_name("roster_tools.py")
REFERENCE = CLI.with_name("reference_tools.py")


def image(path, color="navy", size=(60, 40)):
    with Image.new("RGB", size, color) as panel:
        panel.save(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RosterToolsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ("a", "b"):
            (self.root / name).mkdir()
            image(self.root / name / "same.png", color="navy" if name == "a" else "red")
        self.inventory = self.root / "inventory.json"
        self.batch = self.root / "batch"
        self.data = {
            "schema_version": 1, "mode": "folder", "quality": "quick",
            "count_rationale": "Two identities: repeated vehicle views in one file and a separate prop.",
            "sources": [{"id": "sheet_a", "path": "a/same.png"}, {"id": "sheet_b", "path": "b/same.png"}],
            "assets": [
                {"id": "cutter_01", "name": "Cutter", "category": "vehicle", "style": "blue ink",
                 "master": "anchor.png", "views": ["bow", "port", "aft", "starboard"],
                 "regions": [{"source_id": "sheet_a", "box": [0, 0, 30, 40]},
                             {"source_id": "sheet_a", "box": [30, 0, 60, 40]}],
                 "identity_spec": {"shape": "long bow"}, "inferences": ["Hidden stern is inferred"],
                 "separation_rationale": "Two views show the same hull and markings."},
                {"id": "valve_02", "name": "Valve", "category": "prop_machinery", "style": "red enamel",
                 "master": "master.png", "views": ["front", "left", "back", "right", "top"],
                 "regions": [{"source_id": "sheet_b", "box": [2, 3, 58, 39]}],
                 "identity_spec": {"wheel": "round"}, "inferences": [],
                 "separation_rationale": "Separate prop, not a view of the hull."},
            ],
        }
        self.write_inventory()

    def write_inventory(self):
        self.inventory.write_text(json.dumps(self.data), encoding="utf-8")

    def run_cli(self, *args, status=0, error=None, script=CLI):
        process = subprocess.run([sys.executable, "-B", str(script), *map(str, args)],
                                 capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, status, process.stdout + process.stderr)
        if error:
            self.assertIn(error, process.stderr)
        return json.loads(process.stdout) if process.stdout else None

    def init(self):
        return self.run_cli("init", self.batch, "--inventory", self.inventory)

    def folder(self, identifier="cutter_01"):
        return self.batch / "assets" / identifier

    def adopt(self, filename, identifier="cutter_01"):
        folder = self.folder(identifier)
        count = len(list((folder / "provenance").iterdir()))
        self.run_cli("adopt", self.batch, identifier, "--file", filename, "--record-id", f"fixture_{count:03d}",
                     "--source", folder / filename, "--origin", "imported", "--notes", "Deterministic test fixture")

    def complete(self, identifier="cutter_01"):
        folder = self.folder(identifier)
        manifest = json.loads((folder / "manifest.json").read_bytes())
        for name in [manifest["master"], *(f"{view}.png" for view in manifest["required_views"])]:
            image(folder / name)
            self.adopt(name, identifier)
            self.run_cli("checkpoint", self.batch, identifier, "--qa", "pending", "--visual-reviewed", "--notes", f"Recorded {name}")
        self.run_cli("sheet", self.batch, identifier)
        return self.run_cli("checkpoint", self.batch, identifier, "--qa", "pass", "--visual-reviewed",
                            "--sheet-current", "--notes", "Fixture visual assertion; not generated art acceptance")

    def test_inventory_identity_grouping_and_original_evidence(self):
        report = self.init()
        self.assertEqual(report["counts"], {"pending": 2})
        manifest = json.loads((self.folder() / "manifest.json").read_bytes())
        self.assertEqual(len(manifest["regions"]), 2)
        self.assertEqual(len(manifest["sources"]), 1)
        self.assertEqual(manifest["identity_spec"], {"shape": "long bow"})
        self.assertEqual(manifest["category"], "vehicle")
        self.assertEqual((self.folder() / "source/source_01.png").read_bytes(), (self.root / "a/same.png").read_bytes())
        self.assertEqual((self.folder("valve_02") / "source/source_01.png").read_bytes(), (self.root / "b/same.png").read_bytes())
        for region in manifest["regions"]:
            with Image.open(self.folder() / region["crop"]) as crop:
                self.assertEqual(crop.size, (30, 40))
        before = sha(self.batch / "roster.json")
        self.init()
        self.assertEqual(sha(self.batch / "roster.json"), before)
        self.data["assets"][0]["style"] = "changed"
        self.write_inventory()
        self.run_cli("init", self.batch, "--inventory", self.inventory, status=2, error="Inventory changed")

    def test_exif_oriented_crop_and_transactional_bad_inventory(self):
        source = self.root / "oriented.jpg"
        with Image.new("RGB", (8, 4), "white") as original:
            for x in range(4):
                for y in range(4):
                    original.putpixel((x, y), (0, 0, 0))
            exif = Image.Exif()
            exif[274] = 6
            original.save(source, exif=exif, quality=100)
        self.data["mode"] = "single"
        self.data["sources"] = [{"id": "turned", "path": "oriented.jpg"}]
        self.data["assets"] = self.data["assets"][:1]
        self.data["assets"][0]["regions"] = [{"source_id": "turned", "box": [0, 4, 4, 8]}]
        self.write_inventory()
        self.init()
        with Image.open(self.folder() / "source/crop_001.png") as crop:
            self.assertEqual(crop.size, (4, 4))
            self.assertGreater(crop.getpixel((2, 2))[0], 240)
        self.assertEqual((self.folder() / "source/source_01.jpg").read_bytes(), source.read_bytes())
        self.batch = self.root / "invalid_batch"
        self.data["assets"][0]["regions"][0]["box"] = [0, 0, 8, 4]
        self.write_inventory()
        self.run_cli("init", self.batch, "--inventory", self.inventory, status=2, error="EXIF-oriented")
        self.assertFalse(self.batch.exists())
        self.assertFalse(list(self.root.glob(".invalid_batch.init-*")))

    def test_resume_partial_completion_drift_and_missing(self):
        self.init()
        partial = self.folder() / "anchor.png"
        image(partial)
        before = sha(partial)
        result = self.run_cli("resume", self.batch)
        self.assertNotIn("anchor.png", result["assets"][0]["missing"])
        self.assertEqual(sha(partial), before)
        self.assertEqual(self.run_cli("next", self.batch)["task"]["kind"], "reconcile")
        self.adopt("anchor.png")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--visual-reviewed", "--notes", "Master selected")
        image(partial, color="red")
        report = self.run_cli("status", self.batch)["assets"][0]
        self.assertEqual(report["status"], "drift")
        self.assertEqual(report["changed_or_missing"], ["anchor.png"])
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--notes", "No silent adoption",
                     status=2, error="Evidence drift")
        image(partial)
        self.assertEqual(self.complete()["status"], "complete")
        next_item = self.run_cli("next", self.batch)
        self.assertEqual(next_item["complete"], ["cutter_01"])
        self.assertEqual(next_item["next"]["id"], "valve_02")
        (self.folder() / "bow.png").unlink()
        report = self.run_cli("resume", self.batch)["assets"][0]
        self.assertEqual(report["status"], "drift")
        self.assertIn("bow.png", report["missing"])
        self.assertEqual(sha(partial), before)
        image(self.folder() / "bow.png")
        self.assertEqual(self.run_cli("status", self.batch)["assets"][0]["status"], "complete")
        (self.folder() / "port.png").write_bytes(b"broken")
        report = self.run_cli("status", self.batch)["assets"][0]
        self.assertIn("port.png", report["invalid"])
        self.assertEqual(self.run_cli("next", self.batch)["next"]["id"], "valve_02")

    def test_completion_requires_actual_qa_assertion_and_dimensions(self):
        self.init()
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pass", "--visual-reviewed",
                     "--sheet-current", "--notes", "Incomplete", status=2, error="valid required")
        folder = self.folder()
        for name in ("anchor", "bow", "port", "aft", "starboard"):
            image(folder / f"{name}.png")
        image(folder / "port.png", size=(61, 40))
        self.run_cli("sheet", self.batch, "cutter_01", status=2, error="pass file checks")
        image(folder / "port.png")
        for name in ("anchor", "bow", "port", "aft", "starboard"):
            self.adopt(f"{name}.png")
        self.run_cli("sheet", self.batch, "cutter_01")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pass", "--notes", "Missing assertion",
                     status=2, error="--visual-reviewed")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pass", "--visual-reviewed",
                     "--notes", "Missing sheet assertion", status=2, error="--sheet-current")
        report = self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "fail", "--visual-reviewed",
                              "--notes", "Geometry mismatch")
        self.assertNotEqual(report["status"], "complete")

    def test_failure_isolation_confirmation_and_no_policy_retry(self):
        self.data["assets"][0].update(status="needs_confirmation", confirmation_reason="Could be two related hulls")
        self.write_inventory()
        self.init()
        self.assertEqual(self.run_cli("next", self.batch)["next"]["id"], "valve_02")
        self.run_cli("confirm", self.batch, "cutter_01", "--notes", "Same hull", status=2, error="--human-resolved")
        self.run_cli("confirm", self.batch, "cutter_01", "--human-resolved", "--notes", "User confirmed one identity")
        self.run_cli("fail", self.batch, "cutter_01", "--kind", "generation", "--notes", "Temporary network failure")
        self.assertEqual(self.run_cli("next", self.batch)["next"]["id"], "valve_02")
        self.run_cli("retry", self.batch, "cutter_01", "--notes", "Service recovered")
        self.assertEqual(self.run_cli("next", self.batch)["next"]["id"], "cutter_01")
        self.run_cli("fail", self.batch, "cutter_01", "--kind", "service_restriction", "--notes", "Rejected by service")
        self.run_cli("retry", self.batch, "cutter_01", "--notes", "Try again", status=2, error="blocked assets stay blocked")
        self.run_cli("fail", self.batch, "cutter_01", "--kind", "generation", "--notes", "Downgrade",
                     status=2, error="cannot be downgraded")
        self.assertEqual(self.complete("valve_02")["status"], "complete")

    def test_correction_budget_provenance_and_review_archive(self):
        self.init()
        self.complete()
        self.run_cli("correction", self.batch, "cutter_01", "--file", "bow.png", "--notes", "One silhouette correction")
        old = sha(self.folder() / "bow.png")
        output = self.root / "generated.png"
        image(output, color="orange")
        request = self.root / "request.json"
        request.write_text(json.dumps({"prompt": "Fixture correction", "referenced_image_paths":
                                      [str(self.folder() / "anchor.png")]}), encoding="utf-8")
        self.run_cli("record", self.folder(), "attempt_01", "--request", request, "--output", output,
                     "--selected", "bow.png", "--snapshot", "roster_correction_01", script=REFERENCE)
        self.run_cli("sheet", self.batch, "cutter_01")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pass", "--visual-reviewed",
                     "--sheet-current", "--finish-correction", "--correction-outcome", "accepted", "--notes", "Correction reviewed")
        self.assertEqual(sha(self.folder() / "revisions/roster_correction_01/bow.png"), old)
        self.run_cli("correction", self.batch, "cutter_01", "--file", "bow.png", "--notes", "Another", status=2, error="budget exhausted")
        archive = self.root / "review.zip"
        report = self.run_cli("review-pack", self.batch, "--out", archive)
        self.assertFalse(report["user_approved"])
        with ZipFile(archive) as packaged:
            self.assertIn("batch_contact_sheet.png", packaged.namelist())
            self.assertIn("assets/cutter_01/provenance/attempt_01/request.json", packaged.namelist())
            self.assertIn("assets/cutter_01/source/crop_002.png", packaged.namelist())
            self.assertNotIn("assets/valve_02/master.png", packaged.namelist())
            self.assertEqual(packaged.read("assets/cutter_01/bow.png"), output.read_bytes())
            review = json.loads(packaged.read("review.json"))
            self.assertEqual(review["omitted"][0]["id"], "valve_02")
            manifest = json.loads(packaged.read("assets/cutter_01/manifest.json"))
            self.assertFalse(manifest["approvals"]["reference_set"])
        self.run_cli("review-pack", self.batch, "--out", archive, status=2, error="new .zip")
        self.run_cli("review-pack", self.batch, "--out", self.folder() / "review.zip", status=2, error="outside the batch")
        (self.folder() / "provenance/attempt_01/request.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.run_cli("status", self.batch)["assets"][0]["status"], "drift")

    def test_bad_paths_sources_ids_and_symlinks(self):
        for bad in ("../outside.png", "a/../a/same.png", "C:/input.png", "a\\same.png"):
            self.data["sources"][0]["path"] = bad
            self.write_inventory()
            self.run_cli("init", self.batch, "--inventory", self.inventory, status=2, error="Unsafe relative path")
            self.assertFalse(self.batch.exists())
        self.data["sources"][0]["path"] = "a/same.png"
        self.data["assets"][0]["id"] = "../escape"
        self.write_inventory()
        self.run_cli("init", self.batch, "--inventory", self.inventory, status=2, error="Unsafe name")
        self.data["assets"][0]["id"] = "cutter_01"
        self.data["assets"][1]["id"] = "CUTTER_01"
        self.write_inventory()
        self.run_cli("init", self.batch, "--inventory", self.inventory, status=2, error="Duplicate asset")
        self.data["assets"][1]["id"] = "valve_02"
        self.write_inventory()
        self.init()
        image(self.root / "a/same.png", color="green")
        self.run_cli("init", self.batch, "--inventory", self.inventory, status=2, error="source paths or bytes changed")
        # Some Windows hosts disallow symlink creation for unprivileged test processes.
        linked = self.folder() / "anchor.png"
        try:
            linked.symlink_to(self.root / "b/same.png")
        except OSError:
            return
        self.assertEqual(self.run_cli("status", self.batch)["assets"][0]["status"], "drift")
        self.assertEqual(self.run_cli("next", self.batch)["next"]["id"], "valve_02")

    def test_master_first_count_mismatch_and_partial_review(self):
        self.data.update(generation_order="all-masters-first", desired_count=7)
        self.data["assets"][0]["group"] = {"id": "harbor", "label": "Harbor equipment"}
        self.write_inventory()
        report = self.init()
        self.assertFalse(report["count_matches"])
        self.assertEqual(report["actual_count"], 2)
        first = self.run_cli("next", self.batch)["task"]
        self.assertEqual((first["asset_id"], first["kind"], first["filename"]), ("cutter_01", "master", "anchor.png"))
        image(self.folder() / "anchor.png")
        self.adopt("anchor.png")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--visual-reviewed", "--notes", "Master selected")
        self.assertEqual(self.run_cli("next", self.batch)["task"]["asset_id"], "valve_02")
        self.run_cli("fail", self.batch, "valve_02", "--kind", "generation", "--notes", "Master failed once")
        next_task = self.run_cli("next", self.batch)["task"]
        self.assertEqual((next_task["asset_id"], next_task["kind"], next_task["filename"]), ("cutter_01", "view", "bow.png"))
        image(self.folder() / "bow.png")
        self.adopt("bow.png")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--visual-reviewed", "--notes", "Bow selected")
        (self.folder() / "port.png").write_bytes(b"invalid")
        archive = self.root / "partial.zip"
        result = self.run_cli("review-pack", self.batch, "--out", archive)
        self.assertEqual(result["partial"], ["cutter_01"])
        self.assertEqual(result["completed"], [])
        with ZipFile(archive) as packaged:
            self.assertIn("locators/sheet_a.png", packaged.namelist())
            self.assertIn("galleries/group_harbor_masters.png", packaged.namelist())
            self.assertIn("galleries/category_vehicle_views.png", packaged.namelist())
            self.assertNotIn("assets/cutter_01/port.png", packaged.namelist())
            entry = json.loads(packaged.read("review.json"))["assets"][0]
            self.assertEqual(entry["invalid"], ["port.png"])
            self.assertIn("aft.png", entry["missing"])
        gallery = self.root / "gallery"
        self.run_cli("gallery", self.batch, "--out", gallery)
        self.assertTrue((gallery / "overview.png").is_file())
        self.run_cli("gallery", self.batch, "--out", gallery, status=2, error="new directory")

    def test_authorized_invented_design_and_detailed_budget(self):
        self.data.update(mode="single", quality="detailed", sources=[], desired_count=5)
        self.data["assets"] = self.data["assets"][:1]
        asset = self.data["assets"][0]
        asset.update(origin="invented", brief="An invented vessel with a brass prow.", regions=[])
        self.write_inventory()
        self.run_cli("init", self.batch, "--inventory", self.inventory, status=2, error="creative_expansion_authorized")
        self.assertFalse(self.batch.exists())
        self.data["creative_expansion_authorized"] = True
        self.write_inventory()
        self.init()
        manifest = json.loads((self.folder() / "manifest.json").read_bytes())
        self.assertEqual(manifest["origin"], "invented")
        self.assertEqual(manifest["regions"], [])
        self.assertEqual((self.folder() / "source/brief.txt").read_text(), asset["brief"])
        self.assertTrue(Path(manifest["sources"][0]["original_path"]).is_file())
        self.complete()
        for index in range(3):
            self.run_cli("correction", self.batch, "cutter_01", "--file", "anchor.png", "--notes", f"Review cycle {index + 1}")
            self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--visual-reviewed",
                         "--finish-correction", "--correction-outcome", "no-output", "--notes", "No output from corrective attempt; retained original")
        self.run_cli("correction", self.batch, "cutter_01", "--file", "anchor.png", "--notes", "Fourth", status=2, error="budget exhausted")

    def test_targeted_failure_continues_peers_and_retry_is_bounded(self):
        self.init()
        image(self.folder() / "anchor.png")
        self.adopt("anchor.png")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--visual-reviewed", "--notes", "Master reviewed")
        self.run_cli("fail", self.batch, "cutter_01", "--file", "bow.png", "--kind", "generation", "--notes", "Network error")
        self.assertEqual(self.run_cli("next", self.batch)["task"]["filename"], "port.png")
        self.run_cli("retry", self.batch, "cutter_01", "--file", "bow.png", "--notes", "Single retry")
        self.assertEqual(self.run_cli("next", self.batch)["task"]["filename"], "bow.png")
        self.run_cli("fail", self.batch, "cutter_01", "--file", "bow.png", "--kind", "generation", "--notes", "Retry also failed")
        self.run_cli("retry", self.batch, "cutter_01", "--file", "bow.png", "--notes", "No third attempt", status=2, error="budget exhausted")
        self.run_cli("fail", self.batch, "cutter_01", "--file", "port.png", "--kind", "service_restriction", "--notes", "Blocked view")
        self.run_cli("retry", self.batch, "cutter_01", "--file", "port.png", "--notes", "No bypass", status=2, error="blocked")
        self.run_cli("correction", self.batch, "cutter_01", "--file", "port.png", "--notes", "No bypass", status=2, error="blocked")
        self.assertEqual(self.run_cli("next", self.batch)["task"]["filename"], "aft.png")
        for name in ("aft.png", "starboard.png"):
            self.run_cli("fail", self.batch, "cutter_01", "--file", name, "--kind", "generation", "--notes", "Held")
        self.assertEqual(self.run_cli("next", self.batch)["task"]["asset_id"], "valve_02")
        state = json.loads((self.batch / "roster.json").read_bytes())
        self.assertEqual(state["assets"]["cutter_01"]["task_failures"]["bow.png"]["attempts"], 2)

    def test_unrecorded_master_reconciles_and_quality_failed_panel_is_not_exported(self):
        self.init()
        image(self.folder() / "anchor.png")
        self.assertEqual(self.run_cli("next", self.batch)["task"]["kind"], "reconcile")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--visual-reviewed", "--notes", "No receipt",
                     status=2, error="need generation receipts")
        self.adopt("anchor.png")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--notes", "No inspection",
                     status=2, error="--visual-reviewed")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--visual-reviewed", "--notes", "Imported master reviewed")
        image(self.folder() / "bow.png", color="red")
        self.adopt("bow.png")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "fail", "--file", "bow.png", "--visual-reviewed",
                     "--notes", "Wrong hull identity in bow")
        self.assertEqual(self.run_cli("next", self.batch)["task"]["filename"], "port.png")
        archive = self.root / "quality_partial.zip"
        self.run_cli("review-pack", self.batch, "--out", archive)
        with ZipFile(archive) as packaged:
            self.assertIn("assets/cutter_01/anchor.png", packaged.namelist())
            self.assertNotIn("assets/cutter_01/bow.png", packaged.namelist())
            self.assertIn("Wrong hull identity", packaged.read("assets/cutter_01/qa.md").decode())
            self.assertIn("galleries/all_masters.png", packaged.namelist())
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "fail", "--visual-reviewed", "--notes", "Full identity uncertainty")
        self.assertEqual(self.run_cli("next", self.batch)["task"]["asset_id"], "valve_02")
        self.run_cli("review-pack", self.batch, "--out", self.root / "held.zip", status=2, error="No usable")

    def test_partial_master_correction_settlement_and_one_call_reservation(self):
        self.data["quality"] = "detailed"
        self.write_inventory()
        self.init()
        image(self.folder() / "anchor.png")
        self.adopt("anchor.png")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--visual-reviewed", "--notes", "Master inspected")
        self.run_cli("correction", self.batch, "cutter_01", "--file", "anchor.png", "--notes", "Attempt one")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--visual-reviewed",
                     "--finish-correction", "--correction-outcome", "no-output", "--notes", "No image returned")
        self.run_cli("correction", self.batch, "cutter_01", "--file", "anchor.png", "--notes", "Attempt two")
        alternate = self.root / "alternate.png"
        image(alternate, color="orange")
        self.run_cli("adopt", self.batch, "cutter_01", "--file", "anchor.png", "--source", alternate,
                     "--origin", "imported", "--record-id", "corrected_02", "--notes", "Fixture correction output")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--visual-reviewed", "--finish-correction",
                     "--correction-outcome", "accepted", "--notes", "Master correction accepted; views not generated")
        self.assertEqual(self.run_cli("next", self.batch)["task"]["filename"], "bow.png")
        self.run_cli("correction", self.batch, "cutter_01", "--file", "anchor.png", "--notes", "Attempt three")
        self.adopt("anchor.png")
        self.run_cli("adopt", self.batch, "cutter_01", "--file", "anchor.png", "--source", alternate,
                     "--origin", "imported", "--record-id", "extra_call", "--notes", "Cannot hide two calls",
                     status=2, error="one recorded corrective attempt")
        self.run_cli("checkpoint", self.batch, "cutter_01", "--qa", "pending", "--visual-reviewed",
                     "--finish-correction", "--correction-outcome", "accepted", "--notes", "Third call accepted")

    def test_post_complete_failure_invalidates_completion(self):
        self.init()
        self.complete()
        self.assertTrue((self.folder() / "contact_preview.png").is_file())
        (self.folder() / "contact_preview.png").unlink()
        self.assertEqual(self.run_cli("next", self.batch)["task"]["kind"], "contact_sheet")
        self.run_cli("sheet", self.batch, "cutter_01")
        self.assertEqual(self.run_cli("status", self.batch)["assets"][0]["corrections"], 0)
        self.run_cli("fail", self.batch, "cutter_01", "--file", "bow.png", "--kind", "service_restriction", "--notes", "New service restriction")
        report = self.run_cli("status", self.batch)["assets"][0]
        self.assertNotEqual(report["status"], "complete")
        self.assertEqual(report["blocked_files"], ["bow.png"])
        task = self.run_cli("next", self.batch)
        self.assertNotIn("cutter_01", task["complete"])
        self.assertEqual(task["held"][0]["id"], "cutter_01")


if __name__ == "__main__":
    unittest.main()
