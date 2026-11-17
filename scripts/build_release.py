"""Build the public source and standalone skill ZIPs."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import posixpath
import re
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "assetrefgen"
SKILL_PREFIX = f"skills/{SKILL_NAME}/"
ROOT_FILES = (
    ".github/workflows/validate.yml", ".gitattributes", ".gitignore", "CHANGELOG.md", "CONTRIBUTING.md",
    "LICENSE", "README.md", "THIRD_PARTY_NOTICES.md", "VERSION", "requirements-dev.txt",
)
PUBLIC_EXAMPLES = (
    "PUBLIC_EXPORT.md", "README.md", "gallery.png", "generation-record.json",
    "characters.inventory.json", "folder.inventory.json", "multiview.inventory.json",
    "objects.inventory.json", "repeated-folder.inventory.json", "single.inventory.json",
    "locators/characters.png", "locators/objects.png",
    "requests/characters-source.json", "requests/kiln-back.json", "requests/kiln-left.json",
    "requests/kiln-master.json", "requests/kiln-right.json", "requests/objects-source.json",
    "sources/characters.png", "sources/objects.png", "sources/single-character.png",
    "kiln-traveler/back.png", "kiln-traveler/contact_preview.png",
    "kiln-traveler/contact_sheet.png", "kiln-traveler/front.png", "kiln-traveler/identity.md",
    "kiln-traveler/left.png", "kiln-traveler/manifest.json", "kiln-traveler/master_front.png",
    "kiln-traveler/qa.md", "kiln-traveler/right.png", "kiln-traveler/source/source_01.png",
)


def selected_files():
    chosen = [ROOT / name for name in ROOT_FILES]
    chosen.extend(ROOT / "examples" / name for name in PUBLIC_EXAMPLES)
    skill = ROOT / SKILL_PREFIX
    chosen.extend(skill / name for name in ("LICENSE", "SKILL.md", "agents/openai.yaml"))
    for folder, patterns in (
        (skill / "assets", ("*.md",)),
        (skill / "references", ("*.md",)),
        (skill / "scripts", ("*.py", "requirements.txt")),
        (ROOT / "docs", ("*.md",)),
        (ROOT / "scripts", ("*.py",)),
        (ROOT / "tests", ("test_*.py",)),
    ):
        chosen.extend(path for pattern in patterns for path in folder.glob(pattern) if path.is_file())
    return sorted(chosen)


def release_version():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.]+)?", version):
        raise ValueError("Invalid VERSION")
    return version


def export_bytes(path):
    contents = path.read_bytes()
    relative = path.relative_to(ROOT).as_posix()
    if relative.startswith("examples/") and path.suffix == ".json":
        document = json.loads(contents)

        def rebase(value):
            if isinstance(value, dict):
                return {k: rebase(v) for k, v in value.items()}
            if isinstance(value, list):
                return [rebase(v) for v in value]
            if isinstance(value, str):
                original = Path(value)
                if original.is_absolute():
                    original = original.resolve()
                    if original.is_relative_to(ROOT):
                        return Path(os.path.relpath(original, path.parent)).as_posix()
                    raise ValueError(f"External path cannot be included in public example: {path.name}")
                if PureWindowsPath(value).anchor:
                    raise ValueError(f"Machine-specific path cannot be included in public example: {path.name}")
            return value

        portable = rebase(document)
        if portable != document:
            contents = (json.dumps(portable, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return contents


def check_content(entries, *, stage="public source", scope=""):
    failures = []
    directories = {parent.as_posix() for name in entries for parent in Path(name).parents}
    for name, contents in entries.items():
        if not name.endswith((".md", ".json", ".yaml", ".yml", ".txt")):
            continue
        text = contents.decode("utf-8")
        if re.search(r"(?:\b[A-Za-z]:[\\/]|/Users/|/home/[^ ]+/)", text):
            failures.append(f"Machine-specific path: {name}")
        if re.search(r"\b(?:github_pat_[A-Za-z0-9_]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{30,})\b", text):
            failures.append(f"Possible credential: {name}")
        if not name.endswith(".md"):
            continue
        for target in re.findall(r"\]\(\s*(?:<([^>]+)>|([^\s)]+))", text):
            link = urlsplit(target[0] or target[1])
            if link.scheme or link.netloc or not link.path:
                continue
            normalized = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(link.path)))
            in_scope = normalized.startswith(scope) or normalized == scope.rstrip("/")
            if not in_scope or (normalized not in entries and normalized not in directories):
                failures.append(f"Broken local link: {name} -> {link.path}")
    if failures:
        raise ValueError(f"{stage}:\n" + "\n".join(failures))


def public_files():
    entries = {}
    for path in selected_files():
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError(f"Do not package symlinks: {path.relative_to(ROOT)}")
        entries[path.relative_to(ROOT).as_posix()] = export_bytes(path)
    return entries


def standalone_files(entries):
    return {
        name.removeprefix("skills/"): contents
        for name, contents in entries.items()
        if name.startswith(SKILL_PREFIX)
    }


def build(out):
    version = release_version()
    out = out.resolve()
    if not out.is_relative_to(ROOT):
        raise ValueError("Release packages must be written inside the project")
    entries = public_files()
    check_content(entries)
    standalone = standalone_files(entries)
    check_content(standalone, stage="standalone skill", scope=f"{SKILL_NAME}/")
    packs = {
        f"AssetRefGen-{version}.zip": entries,
        f"{SKILL_NAME}-{version}-skill.zip": standalone,
    }
    checksum_name = "SHA256SUMS.txt"
    report_name = "package-report.json"
    for name in (*packs, checksum_name, report_name):
        if (out / name).exists():
            raise ValueError(f"Release artifact already exists: {name}; use a new output directory")
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    with ExitStack() as cleanup:
        for name, files in packs.items():
            destination = out / name
            with ZipFile(destination, "x", ZIP_DEFLATED) as archive:
                cleanup.callback(destination.unlink, missing_ok=True)
                for filename, data in sorted(files.items()):
                    entry = ZipInfo(filename)
                    entry.create_system = 3
                    entry.external_attr = 0o100644 << 16
                    archive.writestr(entry, data, compress_type=ZIP_DEFLATED)
            with ZipFile(destination) as archive:
                bad = archive.testzip()
                if bad:
                    raise ValueError(f"ZIP CRC failed: {bad}")
                for filename, data in files.items():
                    if archive.read(filename) != data:
                        raise ValueError(f"Archive differs: {filename}")
            results[name] = {
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "bytes": destination.stat().st_size,
                "files": len(files),
                "crc": "pass",
            }
        checksums = "".join(f"{info['sha256']}  {name}\n" for name, info in results.items())
        for name, data in ((checksum_name, checksums), (report_name, json.dumps(results, indent=2) + "\n")):
            destination = out / name
            with destination.open("x", encoding="utf-8", newline="\n") as stream:
                cleanup.callback(destination.unlink, missing_ok=True)
                stream.write(data)
        cleanup.pop_all()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    print(json.dumps(build(args.out), indent=2))
