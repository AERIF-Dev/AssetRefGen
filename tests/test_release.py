"""Exercise release packaging from the public tree without using an image service."""
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from scripts.build_release import ROOT, PUBLIC_EXAMPLES, SKILL_PREFIX, build, check_content, release_version


class ReleaseTest(unittest.TestCase):
    def test_release_archives_and_checksums(self):
        work = ROOT / "tmp"
        work.mkdir(exist_ok=True)
        with TemporaryDirectory(prefix="release-test-", dir=work) as directory:
            out = Path(directory)
            results = build(out)
            version = release_version()
            full_name = f"AssetRefGen-{version}.zip"
            skill_name = f"assetrefgen-{version}-skill.zip"
            self.assertEqual({full_name, skill_name}, set(results))
            self.assertEqual(results, json.loads((out / "package-report.json").read_bytes()))
            checksums = {}
            with ZipFile(out / full_name) as full, ZipFile(out / skill_name) as skill:
                for archive, name in ((full, full_name), (skill, skill_name)):
                    with self.subTest(archive=name):
                        self.assertIsNone(archive.testzip())
                        paths = archive.namelist()
                        self.assertEqual(len(paths), len(set(paths)))
                        for member in archive.infolist():
                            path = PurePosixPath(member.filename)
                            self.assertFalse(path.is_absolute())
                            self.assertFalse(PureWindowsPath(member.filename).drive)
                            self.assertNotIn("..", path.parts)
                            self.assertNotIn("\\", member.filename)
                            self.assertFalse(stat.S_ISLNK(member.external_attr >> 16))
                        checksum = hashlib.sha256((out / name).read_bytes()).hexdigest()
                        checksums[name] = checksum
                        self.assertEqual(checksum, results[name]["sha256"])
                        self.assertEqual(len(paths), results[name]["files"])
                        self.assertEqual((out / name).stat().st_size, results[name]["bytes"])

                full_paths = set(full.namelist())
                self.assertTrue({
                    "README.md", "LICENSE", "CONTRIBUTING.md", "THIRD_PARTY_NOTICES.md", ".gitattributes",
                    ".github/workflows/validate.yml", "requirements-dev.txt", "scripts/validate_project.py",
                }.issubset(full_paths))
                self.assertEqual({f"examples/{name}" for name in PUBLIC_EXAMPLES},
                                 {name for name in full_paths if name.startswith("examples/")})
                self.assertEqual((ROOT / "examples/kiln-traveler/front.png").read_bytes(),
                                 full.read("examples/kiln-traveler/front.png"))
                portable = json.loads(full.read("examples/single.inventory.json"))
                for source in portable["sources"]:
                    self.assertIn(f"examples/{source['path']}", full_paths)
                mapped_skill = {name.removeprefix("skills/"): name for name in full_paths if name.startswith(SKILL_PREFIX)}
                self.assertEqual(set(mapped_skill), set(skill.namelist()))
                self.assertTrue({"assetrefgen/SKILL.md", "assetrefgen/LICENSE"}.issubset(mapped_skill))
                for name, original in mapped_skill.items():
                    self.assertEqual(full.read(original), skill.read(name))

            self.assertEqual(
                "".join(f"{checksums[name]}  {name}\n" for name in (full_name, skill_name)),
                (out / "SHA256SUMS.txt").read_text(encoding="utf-8"),
            )
            before = {path.name: path.stat().st_mtime_ns for path in out.iterdir()}
            with self.assertRaisesRegex(ValueError, "already exists"):
                build(out)
            self.assertEqual(before, {path.name: path.stat().st_mtime_ns for path in out.iterdir()})

    def test_public_content_validation(self):
        check_content({
            "README.md": b"[docs](docs/) [guide](docs/Basic%20Guide.md#start)",
            "docs/Basic Guide.md": b"# Start",
        })
        with self.assertRaisesRegex(ValueError, "Broken local link"):
            check_content({"README.md": b"[missing](missing.md)"})
        with self.assertRaisesRegex(ValueError, "Broken local link"):
            check_content({"assetrefgen/SKILL.md": b"[parent](..)"}, scope="assetrefgen/")
        with self.assertRaisesRegex(ValueError, "Machine-specific path"):
            check_content({"examples/config.json": rb'{"path":"C:\\Users\\local\\file.png"}'})
        with self.assertRaisesRegex(ValueError, "Possible credential"):
            check_content({"examples/config.json": b'{"token":"ghp_' + b"a" * 36 + b'"}'})


if __name__ == "__main__":
    unittest.main()
