"""Maintain file evidence for generated asset references."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageDraw, ImageFont


CATEGORIES = ("humanoid", "creature", "weapon", "vehicle", "architecture", "prop_machinery")
DEFAULT_VIEWS = ("front", "left", "back", "right")
MANIFEST = "manifest.json"
TEMPLATES = Path(__file__).resolve().parents[1] / "assets"
PRESERVED = ("source", "provenance", "revisions")
SCOPE = "File checks only; visual review is separate and geometry is unverified."
RESERVED = {"con", "prn", "aux", "nul", *(f"{kind}{i}" for kind in ("com", "lpt") for i in range(10))}


def slug(value):
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value)
        or value.lower() in RESERVED
    ):
        raise ValueError(f"Unsafe name: {value!r} (use letters, digits, underscores, or hyphens)")
    return value


def png_name(value):
    if not isinstance(value, str) or not value.endswith(".png"):
        raise ValueError(f"Expected a plain .png filename: {value!r}")
    slug(value[:-4])
    return value


def names(values):
    if not isinstance(values, (tuple, list)):
        raise ValueError("View names must be a list")
    result = [slug(value) for value in values]
    if len({name.lower() for name in result}) != len(result):
        raise ValueError("View names must be distinct (ignoring case)")
    return result


def required_views(values):
    result = names(values)
    if len(result) < 4:
        raise ValueError("Specify at least four required views")
    return result


def asset_dir(path):
    if is_link(path) or not path.is_dir():
        raise ValueError(f"Expected an asset directory: {path}")
    return path.resolve()


def is_link(path):
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def inside(root, *parts):
    path = root
    for part in parts:
        path /= part
        if is_link(path) or not path.resolve().is_relative_to(root):
            raise ValueError(f"Path escapes its asset directory or is a symbolic link: {path}")
    return path


def regular(path):
    if not path.is_file():
        raise ValueError(f"Expected a file: {path}")
    return path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


@contextmanager
def new_dir(path):
    # mkdir itself enforces exclusivity; remove only the directory created by this call.
    path.mkdir()
    try:
        yield
    except BaseException:
        shutil.rmtree(path)
        raise


@contextmanager
def write_file(path, overwrite=False):
    if overwrite:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            try:
                yield output
                output.close()
                temporary.replace(path)
            finally:
                output.close()
                temporary.unlink(missing_ok=True)
    else:
        with path.open("xb") as output:
            try:
                yield output
                output.flush()
            except BaseException:
                output.close()
                path.unlink(missing_ok=True)
                raise


def put(path, data, overwrite=False):
    with write_file(path, overwrite) as output:
        output.write(data)


def same_path(one, other):
    return (str(one.resolve()).casefold() == str(other.resolve()).casefold()
            or (one.exists() and other.exists() and one.samefile(other)))


def load_manifest(root):
    data = json.loads(regular(inside(root, MANIFEST)).read_bytes())
    if not isinstance(data, dict):
        raise ValueError("The manifest must contain a JSON object")
    try:
        slug(data["asset_id"])
        master = png_name(data["master"])
        required = required_views(data["required_views"])
        optional = names(data["optional_views"])
        names(required + optional + [master[:-4]])
        if data["category"] not in CATEGORIES or not isinstance(data["style"], str) or not data["style"].strip():
            raise ValueError("Expected a supported category and a nonempty style")
        approvals = data["approvals"]
        if not isinstance(approvals, dict) or any(
            type(approvals.get(key)) is not bool for key in ("visual_direction", "reference_set")
        ):
            raise ValueError("The manifest must have boolean visual_direction and reference_set approvals")
    except KeyError as error:
        raise ValueError(f"Missing manifest field: {error}") from error
    return data


def view_names(manifest):
    return manifest["required_views"] + manifest["optional_views"]


def asset_pngs(manifest):
    return [manifest["master"], *(f"{name}.png" for name in view_names(manifest))]


def original_sources(manifest):
    sources = manifest.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("Manifest sources must be a list")
    paths = []
    for source in sources:
        location = source.get("original_path") if isinstance(source, dict) else None
        if not isinstance(location, str) or not location:
            raise ValueError("Manifest sources must record original paths")
        # A manifest can be moved to a host where the original path has no meaning.
        if Path(location).is_absolute():
            paths.append(Path(location))
    return paths


def reject_preserved_path(path, roots=()):
    resolved = path.resolve()
    for parent in {path.absolute(), *path.absolute().parents, resolved, *resolved.parents}:
        if parent.name.casefold() in PRESERVED and (
            (parent.parent / MANIFEST).is_file() or parent.parent in roots
        ):
            raise ValueError(f"Cannot write into preserved evidence: {path}")


def init(args):
    asset_id = slug(args.asset_id or args.asset.name)
    master = png_name(args.master)
    required = required_views(args.required_views)
    optional = names(args.optional_views)
    names(required + optional + [master[:-4]])
    if not args.style.strip():
        raise ValueError("Provide a nonempty style")
    if not args.asset.name or args.asset.exists() or is_link(args.asset):
        raise ValueError(f"Asset directory already exists: {args.asset}")
    reject_preserved_path(args.asset)
    root = args.asset.resolve()

    fields = {"asset_id": asset_id, "category": args.category, "style": args.style}
    documents = {
        name: re.sub(r"\{\{(asset_id|category|style)\}\}", lambda m: fields[m[1]],
                     (TEMPLATES / f"{name}.template.md").read_text(encoding="utf-8"))
        for name in ("identity", "qa")
    }
    data = dict(fields, master=master, required_views=required, optional_views=optional,
                sources=[], approvals={"visual_direction": False, "reference_set": False},
                geometric_consistency="unverified")
    with new_dir(root):
        for folder in PRESERVED:
            inside(root, folder).mkdir()
        seen = []
        for i, path in enumerate(args.source or [args.brief], 1):
            if any(same_path(path, prior) for prior in seen):
                raise ValueError(f"Duplicate source file: {path}")
            seen.append(path)
            contents = regular(path).read_bytes()
            if not contents:
                raise ValueError(f"Empty source file: {path}")
            if args.source:
                with Image.open(io.BytesIO(contents)) as image:
                    image.verify()
            suffix = path.suffix.lower()
            suffix = suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) else ""
            name = f"source_{i:02d}{suffix}" if args.source else "brief" + suffix
            put(inside(root, "source", name), contents)
            data["sources"].append({
                "kind": "image" if args.source else "brief",
                "path": f"source/{name}", "sha256": digest(contents),
                "original_path": str(path.resolve()),
            })
        put(inside(root, MANIFEST), json_bytes(data))
        for name, document in documents.items():
            put(inside(root, name + ".md"), document.encode("utf-8"))
    return {"asset": str(root), "manifest": data}, 0


def inspect_png(path, pixels=False):
    entry = {"filename": path.name}
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return dict(entry, status="missing"), None
    except (OSError, ValueError) as error:
        return dict(entry, status="invalid", error=str(error)), None
    entry["sha256"] = digest(data)
    try:
        with Image.open(io.BytesIO(data), formats=["PNG"]) as source:
            if getattr(source, "n_frames", 1) != 1:
                raise ValueError("Expected a still PNG")
            source.verify()
        with Image.open(io.BytesIO(data), formats=["PNG"]) as source:
            source.load()
            entry.update(status="ok", width=source.width, height=source.height,
                         mode=source.mode, png_bit_depth=data[24])
            if pixels:
                if entry["png_bit_depth"] > 8:
                    raise ValueError("Native sheet panels support PNGs with up to 8 bits per channel")
                return entry, source.convert("RGBA")
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
        entry.update(status="invalid", error=str(error))
    return entry, None


def audit_set(root, manifest):
    files = []
    for i, filename in enumerate(asset_pngs(manifest)):
        entry, _ = inspect_png(inside(root, filename))
        role = "master" if i == 0 else ("required" if i <= len(manifest["required_views"]) else "optional")
        files.append(dict(entry, role=role))
    readable = [file for file in files if file["status"] == "ok"]
    sizes = sorted({(file["width"], file["height"]) for file in readable})
    modes = sorted({file["mode"] for file in readable})
    missing = [f["filename"] for f in files if f["status"] == "missing" and f["role"] != "optional"]
    invalid = [f["filename"] for f in files if f["status"] == "invalid"]
    passed = not missing and not invalid and len(sizes) == 1
    return {
        "scope": SCOPE, "geometric_consistency": "unverified", "files": files,
        "missing_required": missing, "invalid": invalid, "distinct_sizes": sizes,
        "distinct_modes": modes, "same_dimensions": len(sizes) == 1 and not missing and not invalid,
        "file_checks_passed": passed,
    }


def audit(args):
    root = asset_dir(args.asset)
    report = audit_set(root, load_manifest(root))
    return report, int(not report["file_checks_passed"])


def output_paths(outputs, suffix, overwrite, protected):
    paths = []
    for path in filter(None, outputs):
        if (
            path.suffix.lower() != suffix or ":" in path.name
            or is_link(path) or not path.parent.is_dir()
        ):
            raise ValueError(f"Expected a {suffix} output in an existing directory: {path}")
        reject_preserved_path(path, protected)
        if any(same_path(path, other) for other in paths):
            raise ValueError("Native and preview output paths must differ")
        for protected_paths in protected.values():
            if any(same_path(path, item) for item in protected_paths):
                raise ValueError(f"Output would replace an input or reserved file: {path}")
        if path.exists() and (not overwrite or not path.is_file()):
            raise ValueError(f"Output already exists: {path}. Pass --overwrite to replace a file.")
        paths.append(path)
    return paths


def named_views(root, explicit):
    manifest_path = inside(root, MANIFEST)
    manifest = load_manifest(root) if manifest_path.exists() or explicit is None else None
    if explicit is not None:
        selected = names(explicit)
    else:
        selected = manifest["required_views"] + [
            name for name in manifest["optional_views"] if inside(root, f"{name}.png").exists()
        ]
    protected_names = set(asset_pngs(manifest) if manifest else [])
    protected_names.update(f"{name}.png" for name in selected)
    protected = [inside(root, name) for name in sorted(protected_names)]
    return selected, protected + (original_sources(manifest) if manifest else [])


def read_panels(root, views):
    entries, panels = [], []
    for name in views:
        path = inside(root, f"{name}.png")
        entry, image = inspect_png(path, pixels=True)
        if image is None:
            raise ValueError(f"Cannot read {path}: {entry.get('error', entry['status'])}")
        entries.append(dict(entry, path=str(path)))
        panels.append(image)
    return entries, panels


def native_sheet(rows, views):
    font_size = max(16, min(42, max(panel.width for row in rows.values() for panel in row) // 24))
    font = ImageFont.load_default(size=font_size)
    gutter = max(12, font_size // 2)
    header = 2 * font_size + 3 * gutter
    widths = [
        max([panel.width for panel in column] + [int(font.getlength(name.upper())) + 2 * gutter])
        for name, column in zip(views, zip(*rows.values()))
    ]
    heights = [max(panel.height for panel in row) for row in rows.values()]
    width = gutter + sum(w + gutter for w in widths)
    height = gutter + sum(header + h for h in heights)
    sheet = Image.new("RGBA", (width, height), "#18202a")
    draw = ImageDraw.Draw(sheet)
    positions = {}
    top = 0
    for (label, panels), height in zip(rows.items(), heights):
        draw.text((gutter, top + gutter), label.upper(), font=font, fill="#f2f4f8", anchor="lt")
        left = gutter
        positions[label] = {}
        for name, panel, width in zip(views, panels, widths):
            draw.text((left + width / 2, top + font_size + 2 * gutter), name.upper(),
                      font=font, fill="#f2f4f8", anchor="mt")
            x = left + (width - panel.width) // 2
            y = top + header + height - panel.height
            sheet.paste(panel, (x, y))
            positions[label][name] = {"x": x, "y": y, "width": panel.width, "height": panel.height}
            left += width + gutter
        top += header + height
    return sheet, positions


def save_sheet(outputs, rows, views, overwrite):
    def save(path, image):
        with write_file(path, overwrite) as output:
            image.save(output, format="PNG")
        return {"path": str(path), "width": image.width, "height": image.height,
                "sha256": digest(path.read_bytes())}

    sheet, positions = native_sheet(rows, views)
    with sheet:
        report = {"panel_positions": positions, "contact_sheet": save(outputs[0], sheet)}
        if len(outputs) > 1:
            with sheet.copy() as preview:
                preview.thumbnail((1800, 1200), Image.Resampling.LANCZOS)
                report["preview"] = save(outputs[1], preview)
    return report


def sheet(args):
    root = asset_dir(args.asset)
    views, protected = named_views(root, args.views)
    outputs = output_paths([args.out, args.preview_out], ".png", args.overwrite, {root: protected})
    entries, panels = read_panels(root, views)
    report = save_sheet(outputs, {"views": panels}, views, args.overwrite)
    return dict(report, scope=SCOPE, views=views, inputs=entries), 0


def compare(args):
    before = asset_dir(args.before)
    after = asset_dir(args.after)
    views, before_protected = named_views(before, args.views)
    after_views, after_protected = named_views(after, args.views)
    if views != after_views:
        raise ValueError("Manifests select different view lists. Pass --views for an explicit shared order.")
    outputs = output_paths([args.out, args.preview_out], ".png", args.overwrite,
                           {before: before_protected, after: after_protected})
    before_entries, before_panels = read_panels(before, views)
    after_entries, after_panels = read_panels(after, views)
    report = save_sheet(outputs, {"before": before_panels, "after": after_panels}, views, args.overwrite)
    equality = {
        name: {
            "byte_equal": one_entry["sha256"] == two_entry["sha256"],
            "native_rgba_equal": one.size == two.size and one.tobytes() == two.tobytes(),
        }
        for name, one, two, one_entry, two_entry in zip(
            views, before_panels, after_panels, before_entries, after_entries
        )
    }
    return dict(report, scope=SCOPE, views=views, inputs={"before": before_entries, "after": after_entries},
                equality=equality), 0


def managed_id(root, folder, identifier):
    slug(identifier)
    parent = inside(root, folder)
    if not parent.is_dir():
        raise ValueError(f"Missing evidence directory: {parent}")
    if any(path.name.casefold() == identifier.casefold() for path in parent.iterdir()):
        raise ValueError(f"Evidence ID already exists: {identifier}")
    return inside(root, folder, identifier)


def top_level_files(root):
    for path in sorted(root.iterdir()):
        if is_link(path):
            raise ValueError(f"Cannot include a symbolic link or junction: {path}")
        if path.is_file():
            yield inside(root, path.name)


def snapshot(args):
    root = asset_dir(args.asset)
    reject_preserved_path(args.asset)
    load_manifest(root)
    destination = managed_id(root, "revisions", args.revision_id)
    files = {}
    with new_dir(destination):
        for path in top_level_files(root):
            contents = path.read_bytes()
            put(inside(destination, path.name), contents)
            files[path.name] = digest(contents)
    return {"revision": str(destination), "files": files}, 0


def record(args):
    root = asset_dir(args.asset)
    reject_preserved_path(args.asset)
    manifest = load_manifest(root)
    destination = managed_id(root, "provenance", args.record_id)
    request = regular(args.request).read_bytes()
    raw = regular(args.output).read_bytes()
    if same_path(args.request, args.output):
        raise ValueError("Request and raw output must differ")
    if not raw:
        raise ValueError("Raw tool output is empty")
    with Image.open(io.BytesIO(raw)) as image:
        width, height = image.size
        mode = image.mode
        image.verify()
    parameters = json.loads(request)
    if not isinstance(parameters, dict) or not isinstance(parameters.get("prompt"), str) or not parameters["prompt"].strip():
        raise ValueError("The request must contain the actual nonempty prompt")
    if "transparent_background" in parameters and type(parameters["transparent_background"]) is not bool:
        raise ValueError("transparent_background must be a boolean when supplied")
    references = parameters.get("referenced_image_paths", [])
    if not isinstance(references, list) or any(not isinstance(path, str) or not path for path in references):
        raise ValueError("referenced_image_paths must be an ordered list of file paths")
    if parameters.get("num_last_images_to_include"):
        raise ValueError("Recordable requests must use file references so every input can be hashed")
    inputs = []
    for supplied in references:
        path = Path(supplied)
        if not path.is_absolute():
            path = args.request.parent / path
        if same_path(path, args.output) or same_path(path, args.request):
            raise ValueError(f"Request or raw output collides with a reference: {path}")
        inputs.append({"path": supplied, "resolved_path": str(path.resolve()),
                       "sha256": digest(regular(path).read_bytes())})
    if any(same_path(args.output, path) for path in original_sources(manifest)):
        raise ValueError("Raw output collides with an original source")
    if args.output.resolve().is_relative_to(inside(root, "source")):
        raise ValueError("Raw output collides with copied source evidence")
    raw_suffix = args.output.suffix.lower()
    raw_name = "raw" + (raw_suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", raw_suffix) else ".bin")
    details = {
        "status": "executed", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "tool": args.tool, "model": args.model or "unexposed", "seed": "unexposed",
        "quality": "unexposed",
        "request": {"path": "request.json", "sha256": digest(request)},
        "inputs": inputs,
        "output": {
            "path": raw_name, "sha256": digest(raw), "original_path": str(args.output.resolve()),
            "width": width, "height": height, "mode": mode,
        },
        "selection": None,
    }
    selected = None
    replace = False
    if (args.overwrite or args.snapshot) and not args.selected:
        raise ValueError("--overwrite and --snapshot require --selected")
    if args.selected:
        selected_name = png_name(args.selected)
        if selected_name not in asset_pngs(manifest):
            raise ValueError("Selection must be a master or view PNG named in the manifest")
        if manifest["approvals"]["reference_set"]:
            raise ValueError("Clear the reference set approval before changing selected files")
        selected = inside(root, selected_name)
        if same_path(selected, args.request) or same_path(selected, args.output):
            raise ValueError("Selection would replace the request or raw output")
        replace = selected.exists()
        replaced_hash = digest(regular(selected).read_bytes()) if replace else None
        if any(same_path(selected, Path(item["resolved_path"])) for item in inputs) and not args.snapshot:
            raise ValueError("Selection would overwrite a reference input; use a matching snapshot")
        if replace and not (args.overwrite or args.snapshot):
            raise ValueError("Selection already exists; use a matching --snapshot or explicit --overwrite")
        if args.snapshot:
            slug(args.snapshot)
            prior = inside(root, "revisions", args.snapshot, selected_name)
            if not replace or digest(regular(prior).read_bytes()) != replaced_hash:
                raise ValueError("Snapshot must contain the current bytes of the file being replaced")
        entry, _ = inspect_png(args.output)
        if entry["status"] != "ok" or entry["sha256"] != digest(raw):
            raise ValueError("A selected output must be a readable, unchanged still PNG")
        details["selection"] = {"filename": selected_name, "sha256": digest(raw),
                                "replaced_sha256": replaced_hash, "snapshot": args.snapshot}
    with new_dir(destination):
        put(inside(destination, "request.json"), request)
        put(inside(destination, raw_name), raw)
        put(inside(destination, "receipt.json"), json_bytes(details))
        if selected:
            put(selected, raw, replace)
    return {"record": str(destination), "receipt": details}, 0


def pack(args):
    root = asset_dir(args.asset)
    manifest = load_manifest(root)
    if not args.reference_set_approved or not manifest["approvals"]["reference_set"]:
        raise ValueError("Pack requires both approvals.reference_set: true and --reference-set-approved")
    report = audit_set(root, manifest)
    if not report["file_checks_passed"]:
        return report, 1
    files = [
        inside(root, name)
        for name in (MANIFEST, "identity.md", "qa.md", *asset_pngs(manifest))
        if inside(root, name).is_file()
    ]
    path, = output_paths([args.out], ".zip", args.overwrite, {root: files + original_sources(manifest)})
    with write_file(path, args.overwrite) as output:
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            for source in files:
                archive.write(source, source.name)
    return {"path": str(path), "files": [file.name for file in files],
            "sha256": digest(path.read_bytes()), "scope": SCOPE}, 0


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("init", help="Create an asset directory and copy source evidence")
    command.add_argument("asset", type=Path)
    command.add_argument("--asset-id")
    command.add_argument("--category", choices=CATEGORIES, required=True)
    command.add_argument("--style", required=True)
    command.add_argument("--master", default="master_front.png")
    command.add_argument("--required-views", nargs="+", default=DEFAULT_VIEWS,
                         help="At least four view names in delivery order")
    command.add_argument("--optional-views", nargs="+", default=[])
    sources = command.add_mutually_exclusive_group(required=True)
    sources.add_argument("--source", type=Path, action="append")
    sources.add_argument("--brief", type=Path)
    command.set_defaults(run=init)

    command = commands.add_parser("audit", help="Check the manifest's PNG files")
    command.add_argument("asset", type=Path)
    command.set_defaults(run=audit)

    for name, run in (("sheet", sheet), ("compare", compare)):
        command = commands.add_parser(name, help=f"Create a native resolution {name}")
        if name == "sheet":
            command.add_argument("asset", type=Path)
        else:
            command.add_argument("--before", type=Path, required=True)
            command.add_argument("--after", type=Path, required=True)
        command.add_argument("--views", nargs="+")
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--preview-out", type=Path)
        command.add_argument("--overwrite", action="store_true")
        command.set_defaults(run=run)

    command = commands.add_parser("snapshot", help="Freeze copies of the asset's top-level files")
    command.add_argument("asset", type=Path)
    command.add_argument("revision_id")
    command.set_defaults(run=snapshot)

    command = commands.add_parser("record", help="Preserve an executed tool request and raw output")
    command.add_argument("asset", type=Path)
    command.add_argument("record_id")
    command.add_argument("--request", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--selected")
    replacement = command.add_mutually_exclusive_group()
    replacement.add_argument("--snapshot")
    replacement.add_argument("--overwrite", action="store_true")
    command.add_argument("--tool", default="image_gen.imagegen")
    command.add_argument("--model")
    command.set_defaults(run=record)

    command = commands.add_parser("pack", help="Archive a file-checked, explicitly approved reference set")
    command.add_argument("asset", type=Path)
    command.add_argument("--out", type=Path, required=True)
    command.add_argument("--reference-set-approved", action="store_true")
    command.add_argument("--overwrite", action="store_true")
    command.set_defaults(run=pack)

    args = parser.parse_args()
    try:
        report, status = args.run(args)
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(cli())
