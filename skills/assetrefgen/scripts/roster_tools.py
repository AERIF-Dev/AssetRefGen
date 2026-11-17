"""Recoverable, single-writer bookkeeping for agent-inventoried reference batches.

This tool never detects subjects, generates images, or asserts visual quality itself.
"""

import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import tempfile
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageDraw, ImageFont, ImageOps

import reference_tools as ref


STATE = "roster.json"
SHEET = "contact_sheet.png"
PREVIEW = "contact_preview.png"
DERIVED = {SHEET, PREVIEW}


def now():
    return datetime.now(timezone.utc).isoformat()


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")
    return value


def no_links(path):
    path = path.absolute()
    if any(ref.is_link(part) for part in (path, *path.parents)):
        raise ValueError(f"Symbolic links and junctions are not allowed: {path}")
    return path


def relative(root, value):
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute()
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise ValueError(f"Unsafe relative path: {value!r}")
    return ref.inside(root, *value.split("/"))


def write_json(path, data):
    no_links(path)
    ref.put(path, ref.json_bytes(data), overwrite=True)


def hash_file(path):
    return ref.digest(ref.regular(path).read_bytes())


def inventory(path):
    path = no_links(path)
    data = json.loads(ref.regular(path).read_bytes())
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Inventory requires schema_version: 1")
    if data.get("mode") not in ("single", "roster", "folder"):
        raise ValueError("mode must be single, roster, or folder")
    if data.get("quality", "quick") not in ("quick", "detailed"):
        raise ValueError("quality must be quick or detailed")
    text(data.get("count_rationale"), "count_rationale")
    if data.get("generation_order", "per-asset-complete") not in ("per-asset-complete", "all-masters-first"):
        raise ValueError("generation_order must be per-asset-complete or all-masters-first")
    if "desired_count" in data and (type(data["desired_count"]) is not int or data["desired_count"] < 1):
        raise ValueError("desired_count must be a positive integer")
    if type(data.get("creative_expansion_authorized", False)) is not bool:
        raise ValueError("creative_expansion_authorized must be boolean")
    if not isinstance(data.get("sources"), list):
        raise ValueError("sources must be a list (empty for wholly invented batches)")
    if not isinstance(data.get("assets"), list) or not data["assets"]:
        raise ValueError("assets must be a nonempty list")
    if data["mode"] == "single" and len(data["assets"]) != 1:
        raise ValueError("single mode requires exactly one inventoried identity")
    source_ids, sources, paths = set(), {}, set()
    for source in data["sources"]:
        identifier = ref.slug(source["id"])
        if identifier.casefold() in source_ids:
            raise ValueError("Duplicate source ID (ignoring case)")
        source_ids.add(identifier.casefold())
        location = relative(path.parent.resolve(), source["path"])
        if location in paths:
            raise ValueError("One source file must have one stable source ID")
        paths.add(location)
        contents = ref.regular(location).read_bytes()
        with Image.open(io.BytesIO(contents)) as original:
            original.verify()
        with Image.open(io.BytesIO(contents)) as original:
            with ImageOps.exif_transpose(original) as oriented:
                size = oriented.size
        sources[identifier] = {"original_path": str(location), "sha256": ref.digest(contents),
                               "oriented_size": list(size)}
    ids, group_labels = set(), {}
    for asset in data["assets"]:
        identifier = ref.slug(asset["id"])
        if identifier.casefold() in ids:
            raise ValueError("Duplicate asset ID (ignoring case)")
        ids.add(identifier.casefold())
        for field in ("name", "style", "separation_rationale"):
            text(asset.get(field), field)
        if asset.get("category") not in ref.CATEGORIES:
            raise ValueError(f"Unsupported category: {asset.get('category')}")
        if "group" in asset:
            group = asset["group"]
            if not isinstance(group, dict):
                raise ValueError("group must be an object with id and label")
            group_id = ref.slug(group["id"])
            label = text(group.get("label"), "group label")
            if group_id.casefold() in group_labels and group_labels[group_id.casefold()] != (group_id, label):
                raise ValueError("A group ID must use one exact spelling and display label")
            group_labels[group_id.casefold()] = (group_id, label)
        master = ref.png_name(asset["master"])
        views = ref.required_views(asset["views"])
        ref.names(views + [master[:-4], SHEET[:-4], PREVIEW[:-4]])
        if not isinstance(asset.get("identity_spec"), dict) or not asset["identity_spec"]:
            raise ValueError("identity_spec must be a nonempty object")
        if not isinstance(asset.get("inferences"), list):
            raise ValueError("inferences must be a list (empty is allowed)")
        if asset.get("status", "pending") not in ("pending", "needs_confirmation"):
            raise ValueError("Initial status must be pending or needs_confirmation")
        if asset.get("status") == "needs_confirmation":
            text(asset.get("confirmation_reason"), "confirmation_reason")
        origin = asset.get("origin", "source-derived")
        if origin not in ("source-derived", "invented"):
            raise ValueError("origin must be source-derived or invented")
        if origin == "invented":
            if not data.get("creative_expansion_authorized", False):
                raise ValueError("Invented identities require explicit creative_expansion_authorized: true")
            text(asset.get("brief"), "Invented design brief")
            if asset.get("regions"):
                raise ValueError("Invented identities use a brief, not fake source regions")
        elif not isinstance(asset.get("regions"), list) or not asset["regions"]:
            raise ValueError("Each source-derived identity requires at least one source region")
        for region in asset.get("regions", []):
            if region["source_id"] not in sources:
                raise ValueError("Region refers to an unknown source ID")
            box = region.get("box")
            width, height = sources[region["source_id"]]["oriented_size"]
            if (not isinstance(box, list) or len(box) != 4 or any(type(x) is not int for x in box)
                    or not (0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height)):
                raise ValueError("Region box must be integer xyxy within the EXIF-oriented source")
    return data, sources


def source_locators(staging, data, sources):
    """Visual index only: subject decisions and boxes are supplied by the agent."""
    folder = staging / "locators"
    folder.mkdir()
    hashes = {}
    for source_id, source in sources.items():
        with Image.open(source["original_path"]) as original:
            with ImageOps.exif_transpose(original) as oriented:
                panel = oriented.convert("RGB")
        with panel:
            draw = ImageDraw.Draw(panel)
            font = ImageFont.load_default(size=max(12, min(32, panel.width // 35)))
            for number, asset in enumerate(data["assets"], 1):
                for region in asset.get("regions", []):
                    if region["source_id"] != source_id:
                        continue
                    x0, y0, x1, y1 = region["box"]
                    draw.rectangle((x0, y0, x1 - 1, y1 - 1), outline="#ff4f6d", width=max(2, panel.width // 400))
                    label = f"{number:02d} {asset['id']}"
                    bounds = draw.textbbox((x0 + 3, y0 + 3), label, font=font)
                    draw.rectangle(bounds, fill="#18202a")
                    draw.text((x0 + 3, y0 + 3), label, font=font, fill="white")
            destination = folder / f"{source_id}.png"
            panel.save(destination, format="PNG")
            hashes[f"locators/{source_id}.png"] = hash_file(destination)
    return hashes


def fingerprint(data):
    return ref.digest(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def evidence(root):
    """Hash every evidence file, checking links before traversing directories."""
    found = {}

    def walk(folder):
        for child in sorted(folder.iterdir()):
            no_links(child)
            if child.is_dir():
                walk(child)
            elif child.is_file():
                found[child.relative_to(root).as_posix()] = hash_file(child)
            else:
                raise ValueError(f"Unsupported evidence entry: {child}")

    for name in ("source", "provenance", "revisions"):
        folder = ref.inside(root, name)
        if folder.is_dir():
            walk(folder)
    for name in ("manifest.json", "identity.md"):
        found[name] = hash_file(ref.inside(root, name))
    return found


def init(args):
    data, sources = inventory(args.inventory)
    target = no_links(args.batch)
    if target.exists():
        root, state = load(target)
        if state["inventory_sha256"] != fingerprint(data):
            raise ValueError("Inventory changed; use a new batch or resolve the existing inventory explicitly")
        if state["sources"] != sources:
            raise ValueError("Original source paths or bytes changed since initialization")
        return status(SimpleNamespace(batch=root))
    if not target.parent.is_dir():
        raise ValueError("Batch parent directory must already exist")
    ref.reject_preserved_path(target)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.init-", dir=target.parent))
    try:
        (staging / "assets").mkdir()
        (staging / "briefs").mkdir()
        state = {"schema_version": 1, "inventory_sha256": fingerprint(data), "sources": sources,
                 "mode": data["mode"], "quality": data.get("quality", "quick"),
                 "generation_order": data.get("generation_order", "per-asset-complete"),
                 "desired_count": data.get("desired_count"),
                 "count_rationale": data["count_rationale"], "created_at": now(), "assets": {}}
        ref.put(staging / "inventory.json", ref.json_bytes(data))
        state["batch_evidence"] = source_locators(staging, data, sources)
        for item in data["assets"]:
            root = staging / "assets" / item["id"]
            selected_sources = list(dict.fromkeys(region["source_id"] for region in item.get("regions", [])))
            brief = None
            if item.get("origin") == "invented":
                brief = staging / "briefs" / f"{item['id']}.txt"
                ref.put(brief, item["brief"].encode("utf-8"))
                state["batch_evidence"][f"briefs/{brief.name}"] = hash_file(brief)
            ref.init(SimpleNamespace(asset=root, asset_id=item["id"], category=item["category"],
                                     style=item["style"], master=item["master"], required_views=item["views"],
                                     optional_views=[], brief=brief,
                                     source=[Path(sources[s]["original_path"]) for s in selected_sources]))
            manifest = ref.load_manifest(root)
            manifest.update(name=item["name"], identity_spec=item["identity_spec"],
                            origin=item.get("origin", "source-derived"), group=item.get("group"),
                            inferences=item["inferences"], separation_rationale=item["separation_rationale"],
                            regions=[])
            if brief:
                manifest["sources"][0]["original_path"] = str(target.resolve() / "briefs" / brief.name)
            for source_id, entry in zip(selected_sources, manifest["sources"]):
                entry["source_id"] = source_id
                entry["oriented_size"] = sources[source_id]["oriented_size"]
            for index, region in enumerate(item.get("regions", []), 1):
                crop_name = f"source/crop_{index:03d}.png"
                with Image.open(sources[region["source_id"]]["original_path"]) as original:
                    with ImageOps.exif_transpose(original) as oriented:
                        with oriented.crop(region["box"]) as crop:
                            if crop.mode not in ("RGB", "RGBA", "L", "LA"):
                                crop = crop.convert("RGBA")
                            crop.save(root / crop_name, format="PNG")
                manifest["regions"].append(dict(region, crop=crop_name, sha256=hash_file(root / crop_name)))
            write_json(root / "manifest.json", manifest)
            identity = (f"# {item['name']}\n\nStable ID: {item['id']}\n\n"
                        f"{item['separation_rationale']}\n\nIdentity specification:\n\n"
                        f"```json\n{json.dumps(item['identity_spec'], ensure_ascii=False, indent=2)}\n```\n\n"
                        f"Inferences (not source facts):\n\n```json\n"
                        f"{json.dumps(item['inferences'], ensure_ascii=False, indent=2)}\n```\n")
            ref.put(root / "identity.md", identity.encode("utf-8"), overwrite=True)
            state["assets"][item["id"]] = {
                "name": item["name"], "category": item["category"], "group": item.get("group"),
                "origin": item.get("origin", "source-derived"), "gate": item.get("status", "pending"),
                "confirmation_reason": item.get("confirmation_reason"), "files": {},
                "evidence": evidence(root), "qa": {"status": "pending", "notes": "Not visually reviewed"},
                "corrections": 0, "correction_pending": False, "events": [],
                "task_failures": {}, "retry_count": 0, "unusable": [], "qa_hold": False,
                "sheet_stale": False,
            }
        write_json(staging / STATE, state)
        write_documents(staging, state)
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return status(SimpleNamespace(batch=target))


def load(path):
    root = ref.asset_dir(no_links(path))
    state = json.loads(ref.regular(ref.inside(root, STATE)).read_bytes())
    if state.get("schema_version") != 1 or not isinstance(state.get("assets"), dict):
        raise ValueError("Invalid roster state")
    saved = json.loads(ref.regular(ref.inside(root, "inventory.json")).read_bytes())
    if fingerprint(saved) != state["inventory_sha256"]:
        raise ValueError("Stored inventory drift; do not silently resume a changed inventory")
    for name, expected in state.get("batch_evidence", {}).items():
        if hash_file(relative(root, name)) != expected:
            raise ValueError(f"Batch evidence drift: {name}")
    for identifier in state["assets"]:
        ref.slug(identifier)
    return root, state


def assess(root, identifier, entry):
    folder = ref.inside(root, "assets", identifier)
    try:
        manifest = ref.load_manifest(folder)
        audit = ref.audit_set(folder, manifest)
        sheet, _ = ref.inspect_png(ref.inside(folder, SHEET))
        preview, _ = ref.inspect_png(ref.inside(folder, PREVIEW))
        files = {file["filename"]: file for file in audit["files"] + [sheet, preview]}
        hashes = {name: file["sha256"] for name, file in files.items() if file["status"] == "ok"}
        actual_evidence = evidence(folder)
        provenance = {}
        for name in actual_evidence:
            if name.startswith("provenance/") and name.endswith("/receipt.json"):
                receipt_path = relative(folder, name)
                receipt = json.loads(receipt_path.read_bytes())
                request = relative(receipt_path.parent, receipt["request"]["path"])
                raw = relative(receipt_path.parent, receipt["output"]["path"])
                if hash_file(request) != receipt["request"]["sha256"] or hash_file(raw) != receipt["output"]["sha256"]:
                    raise ValueError(f"Invalid provenance hashes: {name}")
                provenance[receipt["output"]["sha256"]] = name
        drift = [name for name, sha in entry["files"].items() if hashes.get(name) != sha]
        evidence_drift = [name for name, sha in entry["evidence"].items() if actual_evidence.get(name) != sha]
        missing = [name for name, file in files.items() if file["status"] == "missing"]
        invalid = [name for name, file in files.items() if file["status"] == "invalid"]
        qa_current = entry["qa"].get("files") == hashes
        active_failures = any(f["status"] in ("failed", "blocked") for f in entry["task_failures"].values())
        missing_provenance = [name for name, sha in hashes.items() if name not in DERIVED and sha not in provenance]
        complete = (audit["file_checks_passed"] and sheet["status"] == "ok" and preview["status"] == "ok" and not drift
                    and not evidence_drift and entry["qa"]["status"] == "pass" and qa_current
                    and not entry["correction_pending"] and not entry["qa_hold"]
                    and not entry["unusable"] and not entry["sheet_stale"] and not active_failures and not missing_provenance)
        gate = entry["gate"]
        state = gate if gate != "pending" else (
            "drift" if evidence_drift or (drift and not entry["correction_pending"]) else
            "quality_hold" if entry["qa_hold"] else
            "complete" if complete else "invalid" if invalid else
            "pending" if missing else "needs_visual_qa")
        return {"id": identifier, "name": entry["name"], "status": state,
                "category": entry["category"], "group": entry["group"], "origin": entry["origin"],
                "master": manifest["master"], "views": manifest["required_views"],
                "gate": gate, "unusable": entry["unusable"], "qa_hold": entry["qa_hold"],
                "task_failures": entry["task_failures"],
                "failed_files": [n for n, f in entry["task_failures"].items() if f["status"] == "failed"],
                "blocked_files": [n for n, f in entry["task_failures"].items() if f["status"] == "blocked"],
                "uncheckpointed": [name for name in hashes if name not in DERIVED and entry["files"].get(name) != hashes[name]],
                "unprovenanced": missing_provenance,
                "sheet_stale": entry["sheet_stale"],
                "missing": missing, "invalid": invalid, "changed_or_missing": drift,
                "evidence_drift": evidence_drift, "files": files, "hashes": hashes,
                "evidence": actual_evidence, "file_checks_passed": audit["file_checks_passed"],
                "qa": entry["qa"], "corrections": entry["corrections"],
                "correction_pending": entry["correction_pending"],
                "confirmation_reason": entry.get("confirmation_reason"),
                "error": entry.get("error")}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {"id": identifier, "name": entry["name"], "status": "drift", "error": str(error),
                "missing": [], "invalid": [], "changed_or_missing": [], "evidence_drift": [str(error)]}


def reports(root, state):
    return [assess(root, identifier, entry) for identifier, entry in state["assets"].items()]


def public(report):
    return {key: value for key, value in report.items() if key not in ("hashes", "evidence", "files")}


def qa_document(identifier, entry):
    lines = [f"# QA: {entry['name']} ({identifier})", "", f"Status: {entry['qa']['status']}",
             f"Gate: {entry['gate']}", f"Corrections used: {entry['corrections']}", "",
             entry["qa"]["notes"], "", "## Recorded observations", ""]
    lines.extend(f"- {event['at']} | {event['action']}: {event['notes']}" for event in entry["events"])
    lines.extend(["", "File checks do not establish visual or geometric consistency. User approval is separate.", ""])
    return "\n".join(lines).encode("utf-8")


def write_documents(root, state):
    lines = ["# Batch progress", "", "Last saved checkpoints; run status for current disk integrity.", "",
             f"Generation order: {state['generation_order']}",
             f"Inventoried: {len(state['assets'])}; requested: {state['desired_count']}", "",
             "| Asset | Gate | QA | Recorded images | Corrections |", "|---|---|---|---:|---:|"]
    for identifier, entry in state["assets"].items():
        ref.put(ref.inside(root, "assets", identifier, "qa.md"), qa_document(identifier, entry), overwrite=True)
        label = entry["name"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {identifier}: {label} | {entry['gate']} | {entry['qa']['status']} | {len(entry['files'])} | {entry['corrections']} |")
    ref.put(ref.inside(root, "progress.md"), ("\n".join(lines) + "\n").encode("utf-8"), overwrite=True)


def status(args):
    root, state = load(args.batch)
    assets = reports(root, state)
    return {"batch": str(root), "assets": [public(asset) for asset in assets],
            "generation_order": state["generation_order"], "desired_count": state["desired_count"],
            "actual_count": len(assets), "count_matches": state["desired_count"] in (None, len(assets)),
            "count_rationale": state["count_rationale"],
            "counts": {label: sum(a["status"] == label for a in assets)
                       for label in sorted({a["status"] for a in assets})},
            "scope": ref.SCOPE}, 0


def next_asset(args):
    root, state = load(args.batch)
    assets = reports(root, state)
    tasks = []
    for asset in assets:
        if (asset["status"] == "complete" or (asset["status"] == "drift" and set(asset["changed_or_missing"]) - DERIVED)
                or asset.get("gate") != "pending"
                or asset.get("qa_hold") or asset["evidence_drift"]):
            continue
        held = set(asset["failed_files"] + asset["blocked_files"] + asset["unusable"]) | (set(asset["invalid"]) - DERIVED)
        missing = asset["missing"]
        unrecorded = [name for name in asset["uncheckpointed"] + asset["unprovenanced"] if name not in held]
        if unrecorded:
            kind, filename = "reconcile", unrecorded[0]
        elif asset["correction_pending"]:
            kind, filename = "settle_correction", state["assets"][asset["id"]].get("correction_target")
        elif asset["master"] in held:
            continue
        elif asset["master"] in missing:
            kind, filename = "master", asset["master"]
        else:
            views = [f"{view}.png" for view in asset["views"] if f"{view}.png" in missing and f"{view}.png" not in held]
            if views:
                kind, filename = "view", views[0]
            elif held or any(name not in DERIVED for name in missing):
                continue
            elif DERIVED.intersection(missing + asset["invalid"] + asset["changed_or_missing"]) or asset["sheet_stale"]:
                kind, filename = "contact_sheet", SHEET
            else:
                kind, filename = "visual_qa", None
        task = {"asset_id": asset["id"], "kind": kind, "filename": filename,
                "path": str(ref.inside(root, "assets", asset["id"], filename)) if filename else None}
        tasks.append((asset, task))
    if state["generation_order"] == "all-masters-first":
        tasks.sort(key=lambda pair: not (pair[1]["kind"] == "master" or
                                       (pair[1]["kind"] == "reconcile" and pair[1]["filename"] == pair[0]["master"])))
    return {"next": public(tasks[0][0]) if tasks else None, "task": tasks[0][1] if tasks else None,
            "held": [public(asset) for asset in assets if asset["status"] != "complete"
                     and asset["id"] not in {a["id"] for a, _ in tasks}],
            "complete": [asset["id"] for asset in assets if asset["status"] == "complete"]}, 0


def selected(args):
    root, state = load(args.batch)
    identifier = ref.slug(args.asset_id)
    if identifier not in state["assets"]:
        raise ValueError(f"Unknown asset ID: {identifier}")
    entry = state["assets"][identifier]
    return root, state, entry, assess(root, identifier, entry)


def save(root, state, entry, action, notes):
    entry["events"].append({"at": now(), "action": action, "notes": notes})
    state["updated_at"] = now()
    write_json(ref.inside(root, STATE), state)
    write_documents(root, state)


def checkpoint(args):
    root, state, entry, report = selected(args)
    text(args.notes, "QA notes")
    if entry["gate"] != "pending":
        raise ValueError(f"Asset is {entry['gate']}; resolve its gate before checkpointing")
    if report["evidence_drift"] or (report["changed_or_missing"] and not entry["correction_pending"]):
        raise ValueError("Evidence drift; restore recorded bytes or begin a correction before changing selections")
    if args.file and args.file not in report["files"]:
        raise ValueError("--file must name a selected image in this asset")
    if report["uncheckpointed"] and not args.visual_reviewed:
        raise ValueError("New selections require --visual-reviewed after actual per-image inspection")
    if report["unprovenanced"]:
        raise ValueError("Selections need generation receipts or explicit adopt evidence: " + ", ".join(report["unprovenanced"]))
    if entry["correction_pending"]:
        target = entry["correction_target"]
        changes = {name for name in set(entry["correction_baseline"]) | set(report["hashes"])
                   if entry["correction_baseline"].get(name) != report["hashes"].get(name) and name not in DERIVED}
        new_records = [name for name in report["evidence"] if name.endswith("/receipt.json")
                       and name not in entry["correction_evidence_baseline"]]
        if changes - {target} or len(new_records) > 1:
            raise ValueError("One correction reservation permits one recorded corrective attempt for its target only")
        if changes and not new_records:
            raise ValueError("A correction selection requires its own recorded attempt")
        if args.finish_correction:
            if not args.correction_outcome:
                raise ValueError("Settling requires --correction-outcome accepted, rejected, or no-output")
            if args.correction_outcome == "accepted" and (len(new_records) != 1 or target not in report["hashes"]):
                raise ValueError("An accepted correction requires one recorded output and a valid target selection")
            if args.correction_outcome == "accepted":
                folder = ref.inside(root, "assets", args.asset_id)
                receipt = json.loads(relative(folder, new_records[0]).read_bytes())
                if receipt["output"]["sha256"] != report["hashes"][target]:
                    raise ValueError("The accepted correction must select the recorded corrective output")
            if args.correction_outcome == "no-output" and (changes or new_records):
                raise ValueError("no-output cannot settle a recorded or changed correction output")
        if args.qa == "pass" and not args.finish_correction:
            raise ValueError("Settle the correction explicitly with --finish-correction and its outcome")
    elif args.finish_correction:
        raise ValueError("No correction reservation is pending")
    if args.finish_correction and not args.visual_reviewed:
        raise ValueError("Settling a correction requires --visual-reviewed and truthful outcome notes")
    if args.qa == "pass" and (not args.visual_reviewed or not report["file_checks_passed"]
                              or report["missing"] or report["invalid"] or entry["sheet_stale"]):
        raise ValueError("QA pass requires --visual-reviewed, valid required views + master, and contact sheet")
    if args.qa == "pass" and not args.sheet_current:
        raise ValueError("QA pass requires --sheet-current confirming the sheet depicts the selected views")
    entry["files"] = report["hashes"]
    entry["evidence"] = report["evidence"]
    entry["qa"] = {"status": args.qa, "notes": args.notes, "at": now(),
                   "visual_reviewed": args.visual_reviewed, "sheet_current": args.sheet_current,
                   "files": report["hashes"]}
    if args.visual_reviewed and args.qa != "fail":
        for name, failure in entry["task_failures"].items():
            if failure["status"] == "pending" and name in report["hashes"]:
                failure["status"] = "resolved"
    if args.qa == "fail":
        if args.file:
            entry["unusable"] = sorted(set(entry["unusable"]) | {args.file})
        else:
            entry["qa_hold"] = True
    if args.finish_correction:
        target = entry["correction_target"]
        entry["correction_pending"] = False
        if args.correction_outcome == "rejected" and target in changes:
            entry["unusable"] = sorted(set(entry["unusable"]) | {target})
        if args.correction_outcome == "accepted" and args.qa != "fail" and target in report["hashes"]:
            entry["unusable"] = [name for name in entry["unusable"] if name != target]
            if entry["task_failures"].get(target, {}).get("status") != "blocked":
                if target in entry["task_failures"]:
                    entry["task_failures"][target]["status"] = "resolved"
            entry["qa_hold"] = False
        entry["last_correction_outcome"] = args.correction_outcome
    if args.qa == "pass":
        if entry["unusable"] or any(f["status"] in ("failed", "blocked") for f in entry["task_failures"].values()):
            raise ValueError("Resolve failed or unusable images before passing full-set QA")
        entry["correction_pending"] = False
        entry["qa_hold"] = False
    save(root, state, entry, "checkpoint", args.notes)
    return public(assess(root, args.asset_id, entry)), 0


def transition(args):
    root, state, entry, report = selected(args)
    text(args.notes, "notes")
    filename = getattr(args, "file", None)
    if filename and filename not in report.get("files", {}):
        raise ValueError("--file must name a selected image in this asset")
    if filename and args.command in ("fail", "retry"):
        previous = entry["task_failures"].get(filename, {})
        if args.command == "fail":
            if previous.get("status") == "blocked":
                raise ValueError("A service restriction cannot be downgraded or retried")
            entry["task_failures"][filename] = {
                "status": "blocked" if args.kind == "service_restriction" else "failed",
                "kind": args.kind, "notes": args.notes, "at": now(),
                "retry_count": previous.get("retry_count", 0), "attempts": previous.get("retry_count", 0) + 1}
            if args.kind == "quality":
                entry["unusable"] = sorted(set(entry["unusable"]) | {filename})
            entry["qa"] = {"status": "pending", "notes": f"Task held: {filename}. {args.notes}"}
        else:
            if previous.get("status") != "failed" or previous.get("kind") == "quality":
                raise ValueError("Only a transient failed task can retry; blocked and quality tasks cannot")
            if previous.get("retry_count", 0) >= 1:
                raise ValueError("Transient retry budget exhausted (one retry per task)")
            previous.update(status="pending", retry_count=1, attempts=2, notes=args.notes, at=now())
        save(root, state, entry, f"{args.command} {filename}", args.notes)
        return public(assess(root, args.asset_id, entry)), 0
    if args.command == "fail":
        if entry["gate"] == "blocked" and args.kind != "service_restriction":
            raise ValueError("A service restriction cannot be downgraded to a retryable failure")
        entry["gate"] = "blocked" if args.kind == "service_restriction" else "failed"
        entry["error"] = {"kind": args.kind, "notes": args.notes, "at": now()}
    elif args.command == "retry":
        if entry["gate"] != "failed":
            raise ValueError("Only a non-policy failed asset can be deliberately retried; blocked assets stay blocked")
        if entry["retry_count"] >= 1 or entry.get("error", {}).get("kind") == "quality":
            raise ValueError("Retry budget exhausted or quality correction required")
        entry["retry_count"] += 1
        entry["gate"] = "pending"
    elif args.command == "confirm":
        if entry["gate"] != "needs_confirmation":
            raise ValueError("Asset is not waiting for confirmation")
        if not args.human_resolved:
            raise ValueError("Confirmation requires --human-resolved and the user's resolution in --notes")
        entry["gate"] = "pending"
    elif args.command == "correction":
        if not filename or filename in DERIVED:
            raise ValueError("A correction requires --file naming the master or one requested view")
        if entry["task_failures"].get(filename, {}).get("status") == "blocked":
            raise ValueError("A blocked service restriction cannot be corrected or retried")
        quality_failure = entry["gate"] == "failed" and entry.get("error", {}).get("kind") == "quality"
        if (entry["gate"] != "pending" and not quality_failure) or report["evidence_drift"] or report["changed_or_missing"]:
            raise ValueError("Resolve gates or drift before starting a correction")
        if entry["correction_pending"]:
            raise ValueError("A correction is already in progress")
        limit = 1 if state["quality"] == "quick" else 3
        if entry["corrections"] >= limit:
            raise ValueError(f"Correction budget exhausted ({limit}); report the limitation")
        number = entry["corrections"] + 1
        folder = ref.inside(root, "assets", args.asset_id)
        revision = f"roster_correction_{number:02d}"
        # A crash after snapshot but before the state write is recoverable iff bytes still match.
        destination = ref.inside(folder, "revisions", revision)
        if destination.exists():
            current = {p.name: hash_file(p) for p in ref.top_level_files(folder)}
            previous = {p.name: hash_file(p) for p in ref.top_level_files(destination)}
            if any(current.get(name) != sha for name, sha in previous.items()):
                raise ValueError("Existing correction snapshot differs from the current selection")
            for name in current.keys() - previous.keys():
                ref.put(ref.inside(destination, name), ref.regular(ref.inside(folder, name)).read_bytes())
        else:
            ref.snapshot(SimpleNamespace(asset=folder, revision_id=revision))
        entry["files"] = report["hashes"]
        entry["evidence"] = evidence(folder)
        entry["corrections"] = number
        entry["gate"] = "pending"
        entry["correction_pending"] = True
        entry["correction_target"] = filename
        entry["correction_baseline"] = report["hashes"]
        entry["correction_evidence_baseline"] = list(report["evidence"])
        entry["sheet_stale"] = True
        entry["qa"] = {"status": "pending", "notes": args.notes}
    save(root, state, entry, args.command, args.notes)
    return public(assess(root, args.asset_id, entry)), 0


def sheet(args):
    root, state, entry, report = selected(args)
    if entry["gate"] != "pending" or report["evidence_drift"]:
        raise ValueError("Resolve asset gate or evidence drift before creating its sheet")
    if set(report["changed_or_missing"]) - DERIVED and not entry["correction_pending"]:
        raise ValueError("Restore selections or start a correction before rebuilding the sheet")
    folder = ref.inside(root, "assets", args.asset_id)
    destination = ref.inside(folder, SHEET)
    preview = ref.inside(folder, PREVIEW)
    derived_damage = DERIVED.intersection(report["missing"] + report["invalid"] + report["changed_or_missing"])
    if destination.exists() and preview.exists() and not (entry["correction_pending"] or entry["sheet_stale"] or derived_damage):
        raise ValueError("Contact sheet already exists; preserve it or start a correction")
    if not report["file_checks_passed"]:
        raise ValueError("All selected views and master must pass file checks before making a sheet")
    result = ref.sheet(SimpleNamespace(asset=folder, views=None, out=destination,
                                      preview_out=preview, overwrite=destination.exists() or preview.exists()))
    entry["files"][SHEET] = hash_file(destination)
    entry["files"][PREVIEW] = hash_file(preview)
    entry["sheet_stale"] = False
    save(root, state, entry, "sheet", "Rebuilt contact sheet from current selected views; visual review pending")
    return result


def adopt(args):
    """Record actual local import/reuse, never fabricate an image service execution."""
    root, state, entry, report = selected(args)
    if entry["gate"] != "pending" or report["evidence_drift"]:
        raise ValueError("Resolve gate or evidence drift before importing")
    if args.file not in report["files"] or args.file in DERIVED:
        raise ValueError("--file must be a master or requested view")
    if entry["task_failures"].get(args.file, {}).get("status") == "blocked":
        raise ValueError("Cannot import over a service-blocked task")
    if entry["correction_pending"]:
        new_records = [name for name in report["evidence"] if name.endswith("/receipt.json")
                       and name not in entry["correction_evidence_baseline"]]
        if args.file != entry["correction_target"] or new_records:
            raise ValueError("One correction reservation permits one recorded corrective attempt for its target only")
    source = no_links(args.source)
    inspected, _ = ref.inspect_png(source)
    if inspected["status"] != "ok":
        raise ValueError("Import requires a readable still PNG")
    folder = ref.inside(root, "assets", args.asset_id)
    selected_path = ref.inside(folder, args.file)
    exists = selected_path.exists()
    same = exists and hash_file(selected_path) == inspected["sha256"]
    if exists and not same and (not entry["correction_pending"] or entry["correction_target"] != args.file):
        raise ValueError("Replacing a selection requires a correction reservation for that file")
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        output, request = temp / "import.png", temp / "request.json"
        ref.put(output, source.read_bytes())
        ref.put(request, ref.json_bytes({"prompt": f"Local file {args.origin}: {args.notes}",
                                        "operation": args.origin, "referenced_image_paths": [str(source)]}))
        result = ref.record(SimpleNamespace(asset=folder, record_id=args.record_id, request=request,
                                           output=output, selected=None if same else args.file,
                                           snapshot=f"roster_correction_{entry['corrections']:02d}" if exists and not same else None,
                                           overwrite=False, tool=f"local.{args.origin}", model="not-applicable"))
    return result


def usable_files(report):
    """Keep intact selections even when another view failed; hold unacknowledged drift."""
    if report.get("qa_hold"):
        return {}
    excluded = set(report["changed_or_missing"] + report.get("unusable", []) + report.get("unprovenanced", [])
                   + report.get("blocked_files", []) + report.get("failed_files", []) + report.get("uncheckpointed", []))
    if (report.get("sheet_stale") or report.get("unusable") or report.get("blocked_files")
            or report.get("failed_files") or report.get("uncheckpointed") or report.get("unprovenanced")
            or report.get("changed_or_missing")):
        excluded.update(DERIVED)
    return {name: sha for name, sha in report.get("hashes", {}).items() if name not in excluded}


def gallery_images(root, assets):
    collections = {"overview": [], "all_masters": [], "all_views": []}
    for report in assets:
        if "master" not in report:
            continue
        usable = usable_files(report)
        for name in [report["master"], *(f"{view}.png" for view in report["views"])]:
            location = ref.inside(root, "assets", report["id"], name) if name in usable else None
            marker = "" if location else " [MISSING / HELD]"
            item = (report["name"], report["id"], name[:-4] + marker, location)
            collections["overview"].append(item)
            role = "masters" if name == report["master"] else "views"
            collections[f"all_{role}"].append(item)
            keys = [f"category_{report['category']}_{role}"]
            if report.get("group"):
                keys.append(f"group_{ref.slug(report['group']['id'])}_{role}")
            for key in keys:
                collections.setdefault(key, []).append(item)
    result = {}
    font = ImageFont.load_default(size=17)
    for name, items in collections.items():
        if not items:
            continue
        columns = min(4, len(items))
        panel = Image.new("RGB", (columns * 320, ((len(items) + columns - 1) // columns) * 260 + 42), "#18202a")
        with panel:
            draw = ImageDraw.Draw(panel)
            draw.text((12, 10), f"{name.replace('_', ' ')} | REVIEW / partials included", font=font, fill="white")
            for index, (label, identifier, view, path) in enumerate(items):
                x, y = index % columns * 320, index // columns * 260 + 42
                draw.text((x + 8, y + 2), label[:30], font=font, fill="white")
                draw.text((x + 8, y + 21), identifier[:32], font=font, fill="#c4cdd8")
                draw.text((x + 8, y + 40), view[:32], font=font, fill="#c4cdd8")
                if path is None:
                    draw.rectangle((x + 8, y + 66, x + 312, y + 250), outline="#737d8d", width=2)
                    draw.text((x + 30, y + 135), "MISSING / HELD", font=font, fill="#ffb8b8")
                    continue
                with Image.open(path) as source:
                    thumb = source.convert("RGBA")
                    thumb.thumbnail((304, 184), Image.Resampling.LANCZOS)
                    panel.paste(thumb, (x + (320 - thumb.width) // 2, y + 66), thumb)
                    thumb.close()
            buffer = io.BytesIO()
            panel.save(buffer, format="PNG")
            result[f"{name}.png"] = buffer.getvalue()
    return result


def gallery(args):
    root, state = load(args.batch)
    assets = reports(root, state)
    rendered = gallery_images(root, assets)
    if not rendered:
        raise ValueError("No usable selections to preview")
    target = no_links(args.out)
    if target.exists() or not target.parent.is_dir() or target.resolve().is_relative_to(root):
        raise ValueError("Gallery requires a new directory outside the batch with an existing parent")
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.gallery-", dir=target.parent))
    try:
        for name, data in rendered.items():
            ref.put(staging / name, data)
        ref.put(staging / "review.json", ref.json_bytes({"assets": [public(a) for a in assets], "scope": ref.SCOPE}))
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"path": str(target), "files": list(rendered), "scope": ref.SCOPE}, 0


def review_pack(args):
    root, state = load(args.batch)
    assets = reports(root, state)
    included = [report for report in assets if usable_files(report)]
    if not included:
        raise ValueError("No usable assets to package for review")
    destination = no_links(args.out)
    if destination.resolve().is_relative_to(root):
        raise ValueError("Review ZIP must be outside the batch to protect evidence")
    if destination.suffix.lower() != ".zip" or not destination.parent.is_dir() or destination.exists():
        raise ValueError("Review ZIP requires a new .zip path in an existing directory")
    for source in state["sources"].values():
        if ref.same_path(destination, Path(source["original_path"])):
            raise ValueError("Review ZIP would overwrite an input")
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with ZipFile(temporary_path, "w", ZIP_DEFLATED) as archive:
            for report in included:
                folder = ref.inside(root, "assets", report["id"])
                # Include originals, crops, selections, and exact available generation evidence.
                files = (set(report["evidence"]) - set(report["evidence_drift"])) | set(usable_files(report))
                for name in sorted(files):
                    archive.write(relative(folder, name), f"assets/{report['id']}/{name}")
                archive.writestr(f"assets/{report['id']}/qa.md", qa_document(report["id"], state["assets"][report["id"]]))
            for name, data in gallery_images(root, assets).items():
                archive.writestr("batch_contact_sheet.png" if name == "overview.png" else f"galleries/{name}", data)
            for name in state.get("batch_evidence", {}):
                archive.write(relative(root, name), name)
            archive.writestr("review.json", ref.json_bytes({
                "purpose": "Review package; not user approval or a geometrically verified model sheet",
                "created_at": now(), "scope": ref.SCOPE,
                "assets": [dict(public(report), packaged_files=sorted(usable_files(report))) for report in included],
                "omitted": [public(report) for report in assets if not usable_files(report)],
            }))
            archive.writestr("inventory.json", ref.regular(ref.inside(root, "inventory.json")).read_bytes())
        # Single-writer contract; never replace an existing review archive.
        if destination.exists():
            raise ValueError("Review output appeared during packaging")
        temporary_path.rename(destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return {"path": str(destination), "sha256": hash_file(destination),
            "completed": [report["id"] for report in included if report["status"] == "complete"],
            "partial": [report["id"] for report in included if report["status"] != "complete"],
            "user_approved": False}, 0


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, run in (("init", init), ("status", status), ("resume", status), ("next", next_asset),
                      ("checkpoint", checkpoint), ("fail", transition), ("retry", transition),
                      ("confirm", transition), ("correction", transition), ("sheet", sheet),
                      ("adopt", adopt), ("gallery", gallery), ("review-pack", review_pack)):
        command = commands.add_parser(name)
        command.add_argument("batch", type=Path)
        command.set_defaults(run=run)
        if name == "init":
            command.add_argument("--inventory", type=Path, required=True)
        if name in ("checkpoint", "fail", "retry", "confirm", "correction", "sheet", "adopt"):
            command.add_argument("asset_id")
        if name in ("checkpoint", "fail", "retry", "confirm", "correction", "adopt"):
            command.add_argument("--notes", required=True)
        if name in ("checkpoint", "fail", "retry", "correction", "adopt"):
            command.add_argument("--file", required=name in ("correction", "adopt"))
        if name == "checkpoint":
            command.add_argument("--qa", choices=("pending", "pass", "fail"), required=True)
            command.add_argument("--visual-reviewed", action="store_true")
            command.add_argument("--sheet-current", action="store_true")
            command.add_argument("--finish-correction", action="store_true")
            command.add_argument("--correction-outcome", choices=("accepted", "rejected", "no-output"))
        if name == "adopt":
            command.add_argument("--record-id", required=True)
            command.add_argument("--source", type=Path, required=True)
            command.add_argument("--origin", choices=("imported", "reused"), required=True)
        if name == "fail":
            command.add_argument("--kind", choices=("service_restriction", "generation", "io", "quality"), required=True)
        if name == "confirm":
            command.add_argument("--human-resolved", action="store_true")
        if name in ("review-pack", "gallery"):
            command.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        report, result = args.run(args)
    except (OSError, ValueError, KeyError, TypeError, SyntaxError, Image.DecompressionBombError) as error:
        parser.error(str(error))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    raise SystemExit(cli())
