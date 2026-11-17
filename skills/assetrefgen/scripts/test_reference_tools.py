"""Test the public CLI without charging for generation or using real asset files."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from PIL import Image, PngImagePlugin


CLI = Path(__file__).with_name("reference_tools.py").resolve()
VIEWS = ["bow", "port", "aft", "starboard", "top"]
MASTER = "forward_anchor.png"


def image(path, color=(72, 135, 87, 168), size=(59, 43), annotate=False):
    with Image.new("RGBA", size, color) as panel:
        options = {}
        if annotate:
            meta = PngImagePlugin.PngInfo()
            meta.add_text("metadata", "pixel content stays the same")
            options["pnginfo"] = meta
        panel.save(path, **options)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReferenceToolsTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.asset = self.root / "arc_cutter"
        self.source = self.root / "identity original.png"
        image(self.source)
        self.init_args = [
            "init", self.asset, "--category", "vehicle", "--style", "wood grain and blue ink",
            "--master", MASTER, "--required-views", *VIEWS[:4], "--optional-views", "top",
            "--source", self.source,
        ]
        self.run_cli(*self.init_args)

    def run_cli(self, *args, status=0, error=None):
        process = subprocess.run(
            [sys.executable, "-B", str(CLI), *(str(arg) for arg in args)],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(process.returncode, status, process.stdout + process.stderr)
        if error:
            self.assertIn(error, process.stderr)
        return json.loads(process.stdout) if process.stdout else None

    def write_set(self, optional=True):
        for name in [MASTER, *(f"{view}.png" for view in (VIEWS if optional else VIEWS[:4]))]:
            image(self.asset / name)

    def test_init_and_audit(self):
        manifest = json.loads((self.asset / "manifest.json").read_bytes())
        self.assertEqual(manifest["sources"][0]["sha256"], sha(self.source))
        self.assertEqual(sha(self.asset / manifest["sources"][0]["path"]), sha(self.source))
        self.assertEqual(manifest["required_views"], VIEWS[:4])
        self.assertIn("arc_cutter", (self.asset / "identity.md").read_text(encoding="utf-8"))
        self.run_cli(*self.init_args, status=2, error="already exists")
        self.run_cli("init", self.root / "other", "--asset-id", "../escape", "--category", "creature",
                     "--style", "paper", "--source", self.source, status=2, error="Unsafe name")
        self.run_cli("init", self.root / "overlap", "--category", "creature", "--style", "paper",
                     "--master", "front.png", "--source", self.source, status=2, error="distinct")
        self.assertFalse((self.root / "overlap").exists())
        self.run_cli("init", self.asset / "source" / "illegal_nested_asset", "--category", "creature",
                     "--style", "paper", "--source", self.source, status=2, error="preserved evidence")
        brief = self.root / "written.txt"
        brief.write_text("An inlet valve with two screws.", encoding="utf-8")
        other = self.root / "valve"
        result = self.run_cli("init", other, "--category", "prop_machinery", "--style", "paper",
                              "--brief", brief)
        self.assertEqual((other / result["manifest"]["sources"][0]["path"]).read_bytes(), brief.read_bytes())

        self.write_set(optional=False)
        report = self.run_cli("audit", self.asset)
        self.assertEqual(report["geometric_consistency"], "unverified")
        self.assertEqual(report["files"][-1]["status"], "missing")
        self.assertTrue(report["same_dimensions"])
        (self.asset / "port.png").unlink()
        (self.asset / "aft.png").write_bytes(b"corrupt image")
        image(self.asset / "starboard.png", size=(60, 43))
        report = self.run_cli("audit", self.asset, status=1)
        self.assertEqual(report["missing_required"], ["port.png"])
        self.assertEqual(report["invalid"], ["aft.png"])
        self.assertEqual(report["distinct_sizes"], [[59, 43], [60, 43]])

    def test_native_sheets_and_snapshot(self):
        self.write_set()
        image(self.asset / "top.png", size=(1910, 37))
        unchanged = {name: sha(self.asset / name) for name in (MASTER, "port.png", "top.png", "bow.png")}
        sheet = self.root / "native.png"
        preview = self.root / "preview.png"
        views = ["top", "port", "bow"]
        report = self.run_cli("sheet", self.asset, "--views", *views, "--out", sheet, "--preview-out", preview)
        self.assertEqual(report["views"], views)
        self.assertLess(report["preview"]["width"], report["contact_sheet"]["width"])
        with Image.open(sheet) as composite:
            for name, position in report["panel_positions"]["views"].items():
                x, y, w, h = (position[k] for k in ("x", "y", "width", "height"))
                with Image.open(self.asset / f"{name}.png") as panel:
                    self.assertEqual(composite.crop((x, y, x + w, y + h)).tobytes(), panel.tobytes())
        self.assertEqual({name: sha(self.asset / name) for name in unchanged}, unchanged)
        self.run_cli("sheet", self.asset, "--views", "../bow", "--out", sheet, status=2, error="Unsafe name")
        self.run_cli("sheet", self.asset, "--out", self.asset / MASTER, "--overwrite",
                     status=2, error="replace an input")
        before_source = sha(self.source)
        self.run_cli("sheet", self.asset, "--out", self.source, "--overwrite",
                     status=2, error="replace an input")
        self.assertEqual(sha(self.source), before_source)
        self.run_cli("sheet", self.asset, "--out", sheet, "--preview-out", sheet, "--overwrite",
                     status=2, error="must differ")
        self.run_cli("snapshot", self.asset, "r01")
        revision = self.asset / "revisions" / "r01"
        self.assertEqual(sha(revision / MASTER), unchanged[MASTER])
        self.run_cli("snapshot", self.asset, "R01", status=2, error="already exists")
        self.run_cli("sheet", self.asset, "--out", revision / "new.png",
                     status=2, error="preserved evidence")
        image(self.asset / "bow.png", annotate=True)
        image(self.asset / "port.png", size=(53, 44))
        report = self.run_cli("compare", "--before", revision, "--after", self.asset,
                              "--out", self.root / "comparison.png")
        self.assertEqual(report["views"], VIEWS)
        self.assertEqual(report["equality"]["bow"], {"byte_equal": False, "native_rgba_equal": True})
        self.assertEqual(report["equality"]["port"], {"byte_equal": False, "native_rgba_equal": False})
        self.assertEqual(report["equality"]["top"], {"byte_equal": True, "native_rgba_equal": True})
        plain = self.root / "plain"
        plain.mkdir()
        image(plain / "bow.png")
        self.run_cli("compare", "--before", plain, "--after", self.asset, "--views", "bow",
                     "--out", self.root / "manual_comparison.png")

    def test_requested_fifth_view_is_required_for_audit_and_pack(self):
        asset = self.root / "survey_cutter"
        init = ["init", asset, "--category", "vehicle", "--style", "ink", "--master", MASTER,
                "--source", self.source]
        self.run_cli(*init, "--required-views", *VIEWS[:3], status=2, error="at least four")
        self.assertFalse(asset.exists())
        result = self.run_cli(*init, "--required-views", *VIEWS, "--optional-views", "underside")
        self.assertEqual(result["manifest"]["required_views"], VIEWS)
        for filename in [MASTER, *(f"{view}.png" for view in VIEWS[:4])]:
            image(asset / filename)

        report = self.run_cli("audit", asset, status=1)
        self.assertEqual(report["missing_required"], ["top.png"])
        self.assertEqual(report["files"][-1]["role"], "optional")
        self.assertEqual(report["files"][-1]["status"], "missing")
        manifest = result["manifest"]
        manifest["approvals"]["reference_set"] = True
        (asset / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        archive = self.root / "survey_cutter.zip"
        pack = ["pack", asset, "--out", archive, "--reference-set-approved"]
        self.assertEqual(self.run_cli(*pack, status=1)["missing_required"], ["top.png"])
        self.assertFalse(archive.exists())

        image(asset / "top.png")
        self.assertEqual(self.run_cli("audit", asset)["missing_required"], [])
        self.run_cli(*pack)
        with ZipFile(archive) as zip_file:
            self.assertIn("top.png", zip_file.namelist())
            self.assertNotIn("underside.png", zip_file.namelist())

    def test_execution_evidence_and_pack(self):
        self.write_set()
        request = self.root / "actual_call.json"
        ordered = [self.source, self.asset / MASTER]
        request.write_bytes(json.dumps({
            "prompt": "Generate a test-only alternate view.",
            "referenced_image_paths": [str(path) for path in ordered],
            "transparent_background": True,
        }, indent=4).encode())
        output = self.root / "tool_output.png"
        image(output, color=(32, 122, 220, 42))
        raw_hash = sha(output)
        selected = self.asset / "bow.png"
        old_hash = sha(selected)
        command = ["record", self.asset, "attempt_01", "--request", request, "--output", output,
                   "--selected", selected.name]
        self.run_cli(*command, status=2, error="already exists")
        self.run_cli("snapshot", self.asset, "r01")
        selected.write_bytes(output.read_bytes())
        self.run_cli(*command, "--snapshot", "r01", status=2, error="current bytes")
        image(selected)
        observed = self.run_cli(*command, "--snapshot", "r01")
        receipt = observed["receipt"]
        self.assertEqual(receipt["model"], "unexposed")
        self.assertEqual(receipt["tool"], "image_gen.imagegen")
        self.assertEqual([item["sha256"] for item in receipt["inputs"]], [sha(path) for path in ordered])
        self.assertEqual((receipt["output"]["width"], receipt["output"]["height"]), (59, 43))
        self.assertEqual(receipt["output"]["mode"], "RGBA")
        evidence = Path(observed["record"])
        self.assertEqual((evidence / "request.json").read_bytes(), request.read_bytes())
        self.assertEqual(sha(evidence / "raw.png"), raw_hash)
        self.assertEqual(sha(output), sha(selected))
        self.assertEqual(sha(self.asset / "revisions" / "r01" / "bow.png"), old_hash)
        self.run_cli(*command, "--overwrite", status=2, error="Evidence ID already exists")
        self.run_cli("record", self.asset, "../escape", "--request", request, "--output", output,
                     status=2, error="Unsafe name")
        self.run_cli("record", self.asset, "attempt_02", "--request", request, "--output", self.source,
                     status=2, error="collides with a reference")
        self.run_cli("record", self.asset, "attempt_02", "--request", request, "--output", output,
                     "--selected", "unknown.png", status=2, error="named in the manifest")

        pack = self.root / "accepted.zip"
        self.run_cli("pack", self.asset, "--out", pack, "--reference-set-approved", status=2,
                     error="Pack requires both")
        self.assertFalse(pack.exists())
        manifest = self.asset / "manifest.json"
        data = json.loads(manifest.read_bytes())
        data["approvals"]["reference_set"] = True
        manifest.write_text(json.dumps(data), encoding="utf-8")
        self.run_cli("pack", self.asset, "--out", pack, status=2, error="Pack requires both")
        self.run_cli("pack", self.asset, "--out", pack, "--reference-set-approved")
        with ZipFile(pack) as archive:
            self.assertEqual(archive.read("bow.png"), output.read_bytes())
            self.assertTrue({"manifest.json", MASTER, "identity.md", "qa.md"} <= set(archive.namelist()))
        self.run_cli("record", self.asset, "attempt_02", "--request", request, "--output", output,
                     "--selected", "bow.png", "--overwrite", status=2, error="Clear the reference set approval")


if __name__ == "__main__":
    unittest.main()
