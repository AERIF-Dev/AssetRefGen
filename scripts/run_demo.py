"""Build/resume a small review demo using already generated public images; no service calls."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "examples"
CLI = ROOT / "skills/assetrefgen/scripts/roster_tools.py"


def run(*args):
    result = subprocess.run([sys.executable, "-X", "utf8", "-B", str(CLI), *map(str, args)],
                            capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)


def copy_once(source, destination):
    if destination.exists():
        if source.read_bytes() != destination.read_bytes():
            raise ValueError(f"Existing demonstration file differs: {destination}")
    else:
        shutil.copyfile(source, destination)


def build():
    batch = E / "demo-batch"
    state = run("resume", batch) if batch.exists() else run("init", batch, "--inventory", E / "characters.inventory.json")
    first = next(a for a in state["assets"] if a["id"] == "kiln-traveler")
    if first["status"] != "complete":
        for i, name in enumerate(("master_front.png", "front.png", "left.png", "back.png", "right.png")):
            destination = batch / "assets/kiln-traveler" / name
            if not destination.exists():
                run("adopt", batch, "kiln-traveler", "--file", name, "--source", E / "kiln-traveler" / name,
                    "--origin", "reused" if name == "front.png" else "imported", "--record-id", f"demo-import-{i}",
                    "--notes", "Imported already generated and visually reviewed public example. No image service call in demo builder.")
            run("checkpoint", batch, "kiln-traveler", "--qa", "pending", "--visual-reviewed",
                "--notes", f"{name}: matches the reviewed public kiln identity; minor brick/hand/pose drift accepted in Quick.")
        run("sheet", batch, "kiln-traveler")
        run("checkpoint", batch, "kiln-traveler", "--qa", "pass", "--visual-reviewed", "--sheet-current",
            "--notes", "All four directions and sheet visually reviewed against source/master; provisional rear, minor brick and hand variation; geometry unverified.")
    before = {p.relative_to(batch).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in batch.rglob("*") if p.is_file()}
    status = run("resume", batch)
    next_work = run("next", batch)
    after = {p.relative_to(batch).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in batch.rglob("*") if p.is_file()}
    if before != after or "kiln-traveler" not in next_work["complete"]:
        raise ValueError("Resume modified or failed to skip completed demonstration work")
    gallery = E / "demo-gallery"
    archive = E / "demo-review.zip"
    if not gallery.exists():
        run("gallery", batch, "--out", gallery)
    if not archive.exists():
        run("review-pack", batch, "--out", archive)
    locators = E / "locators"
    locators.mkdir(exist_ok=True)
    copy_once(batch / "locators/characters.png", locators / "characters.png")
    with tempfile.TemporaryDirectory(prefix="assetrefgen-objects-") as temporary:
        objects = Path(temporary) / "objects"
        run("init", objects, "--inventory", E / "objects.inventory.json")
        copy_once(objects / "locators/objects.png", locators / "objects.png")
    report = {"purpose": "Small import/recovery demonstration; no new service calls",
              "counts": status["counts"], "next_asset": next_work["task"]["asset_id"],
              "next_kind": next_work["task"]["kind"], "all_saved_files_unchanged_by_resume": before == after,
              "intentionally_ungenerated": ["pond-courier", "moth-keeper"],
              "review_zip": "demo-review.zip", "gallery": "demo-gallery/overview.png"}
    (E / "demo-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    build()
