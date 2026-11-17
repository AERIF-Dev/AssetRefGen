# Validation results

## v0.2.0 publication checks — 2026-11-17

The stable release promotes the validated candidate and fixes Windows short-path handling during roster initialization. The repository now contains one installable skill at `skills/assetrefgen/`, MIT licensing, public installation/contribution guides, a standalone structural validator, release-packaging tests and GitHub Actions. Proposed v0.3.0 features are recorded only in the [roadmap](ROADMAP.md).

Local Windows validation initially passed 22 tests under each of two environments: Python 3.10 with Pillow 10.1.0 (the declared minimums), and Python 3.13 with Pillow 13.0.0. Hosted Windows CI then exposed an 8.3 short-path alias mismatch in the roster staging directory. A regression test reproduced the failure locally and passed after canonicalizing the already-validated staging parent; symbolic-link and containment guards are preserved. The final suite contains **23 tests**: 18 skill-helper tests and 5 public-example/release tests. Structure validation, Python compilation and the minimum-profile dependency check also passed. Ordinary tests make no image-service calls.

After the correction, all 23 tests passed in both local Windows environments, including the real short-path regression with no skips. Trusted temporary test roots are resolved to avoid platform aliases; the dedicated Windows regression explicitly uses an 8.3 alias. The original single-asset helper remains unchanged.

```sh
python -m pip install -r requirements-dev.txt
python scripts/validate_project.py
python -m unittest discover -s skills/assetrefgen/scripts -v
python -m unittest discover -s tests -v
python scripts/build_release.py --out dist/v0.2.0
```

The default Validate workflow runs on pushes and pull requests for Windows and Linux. The required jobs passed on the exact v0.2.0 release commit, `f7503e44379da7aeffa6e0da2744ed54c980aa74`. [Release commit CI run](https://github.com/AERIF-Dev/AssetRefGen/actions/runs/44131068273)

| Hosted environment | Result |
| --- | --- |
| Windows, Python 3.13 | 23 passed, including the Windows short-path regression |
| Linux, Python 3.10, Pillow 10.1.0 | 22 passed, 1 Windows-only short-path test skipped |
| macOS, including Apple Silicon | Unverified. Neither architecture ran during release qualification. |

GitHub canceled the Intel job `134190080741` after multiple runner-acquisition attempts. The retry was still queued when the release gate was set. The release gate requires Windows and Linux. The manual `macOS compatibility` workflow is available for follow-up testing. [macOS compatibility workflow](https://github.com/AERIF-Dev/AssetRefGen/actions/workflows/validate-macos.yml)

The release archives include the complete skill and license. Packaging enforces a public-file allowlist, checks internal links, verifies ZIP readback and CRC, and emits SHA-256 checksums. The archive contents exclude development outputs, exact local receipts and private source material.

On Windows, the extracted standalone skill passed roster initialization in a clean Python 3.13/Pillow 13.0.0 environment. Before tagging, all 17 files installed by the official Codex installer from public commit `cf50d4f` matched the standalone ZIP byte for byte.

## Public release verification — 2026-11-17

GitHub published v0.2.0 at 16:58:04 UTC on commit `f7503e44379da7aeffa6e0da2744ed54c980aa74`. [GitHub release](https://github.com/AERIF-Dev/AssetRefGen/releases/tag/v0.2.0)

- The official Codex installer installed the skill from the public `v0.2.0` tag into an isolated destination. All 17 installed files matched the standalone ZIP byte for byte, and the helper's `--help` loaded in a clean environment.
- Anonymous downloads succeeded for both ZIPs and `SHA256SUMS.txt`. The SHA-256 values matched the published checksums, both archives passed CRC checks, and the extracted contents matched the corresponding local packages. The full project ZIP contained 74 files and passed the structural validator. The standalone skill ZIP contained 17 files.
- The public allowlist and privacy checks passed. A fresh public clone passed the byte audit for all 74 files.

The published ZIPs retain the documentation checkpoint from the tagged source. This page and the [release checklist](RELEASE_CHECKLIST.md) record the postpublication evidence.

## Candidate validation retained below — 0.2.0-rc.1

Date: 2026-11-17. Platform: Windows, Python 3.13.7. Candidate integration used Pillow 13.0.0 and PyYAML 6.0.3 in a project-local virtual environment. Minimum supported versions and other operating systems were not exercised during this earlier candidate pass; see the publication checks above for later evidence.

## Automated checks

| Check | Result | Evidence scope |
| --- | --- | --- |
| Existing `test_reference_tools.py` | 4/4 pass | Original source preservation, image audit, native sheets, snapshots, generation receipts and approved-set ZIP behavior |
| New `test_roster_tools.py` | 13/13 pass | Inventory grouping, exact originals/EXIF crops, stable paths, ambiguity, mixed categories, schedules, resume, drift, targeted failures, bounded retries/corrections, provenance, partial ZIP and preview recovery |
| Public example integration | 3/3 pass, including six inventory subcases | One character, three-design roster, mixed objects, folder, multi-angle identity, cross-file repeats; actual live PNG integrity; interrupted per-image imports and complete-set resume |
| Independent focused regression review | 4 targeted checks pass plus a correction-hash probe | The reviewer reproduced the earlier failures and verified their fixes; no blocker remained in that scope |
| Python syntax | 9 files parsed | Helper scripts, regression tests and public packaging/example tools |
| Skill Creator `quick_validate.py` | Pass | Skill frontmatter, naming and scaffold checks; not a behavioral certificate |

Final parent runs: 17 helper tests in 57.428 seconds, 3 public integration tests in 23.007 seconds. The legacy `reference_tools.py`, its test file, and its requirements file remain byte-for-byte equal to the installed working originals. No installed skill file was written.

```powershell
python -X utf8 -B -m unittest discover -s skills/assetrefgen/scripts -p "test_*.py" -v
python -X utf8 -B -m unittest discover -s tests -p "test_*.py" -v
python -X utf8 path/to/skill-creator/scripts/quick_validate.py skills/assetrefgen
```

Use `-X utf8` for the external Skill Creator validator on Windows: its default-encoding read failed under cp1252 on Unicode punctuation; it passed under UTF-8. No change to the external validator was needed.

## Small live generation and visual checks

Six actual built-in image calls created two original source rosters, one isolated kiln-character front master, and three derived directions. The front view reused suitable master bytes; this was not counted as another generation. No correction calls were needed. [Generation record](../examples/generation-record.json), [gallery](../examples/gallery.png), [native sheet](../examples/kiln-traveler/contact_sheet.png), [visual QA](../examples/kiln-traveler/qa.md).

The selected master/front/left/back/right are readable 1254 × 1254 RGB PNGs. The native sheet is 5121 × 1422, and the separate preview is 1800 × 500. Tests verify that the preview is the documented resize of the native sheet and that the right image is not a mirrored copy of the left. Model/version, seed, provider quality and cost were unexposed and remain so in records.

Visual inspection found the intended identity and approximate directions, complete framing and coherent provisional rear construction. Minor brick-seam, hand and pose differences remain, with slight residual perspective in side views. These are usable Quick prototype references, not validated shared-mesh orthographic renders.

An independent reviewer, without consulting the prepared inventories, identified three distinct designs in the character/creature roster, two in the mixed-object roster, and one across the four-angle sheet. The kiln design also matches across the lineup and its turnaround. Numbered source locators and the partial master-gallery layout were visually checked.

## Recovery demonstration

`python scripts/run_demo.py` imports the already generated public set into a three-design example batch; it makes no image-service calls. One set is complete and two subjects are intentionally ungenerated. `resume` and `next` left all saved file hashes unchanged and scheduled the next missing master, skipping the completed set. The generated gallery shows missing slots explicitly; the local review ZIP distinguishes completed selections from missing work. Local demo outputs are excluded from the public bundle; the builder is included for reproduction.

The tests also simulate interruption after a selected output lands but before its checkpoint. The next task is reconciliation, not another generation or use of an unreviewed master. Known valid files survive. A targeted failed direction does not stop independent directions; a failed master holds its dependents. Policy-rejected tasks cannot be retried or relabeled as a recoverable service error.

## Review findings resolved

- Replaced asset-wide-only failure handling with per-file holds and one persisted transient retry.
- Added explicit reconciliation and provenance checks before a recovered image is accepted.
- Made each correction reservation one target/one recorded attempt, with accepted/rejected/no-output settlement even before views exist.
- Excluded rejected, blocked, unreviewed or unprovenanced selections and stale derived sheets from usable exports.
- Preserved completed identities when ambiguous grouping needs a linked supplemental inventory.
- Added native/preview sheet recovery, cumulative QA records, readable progress and galleries labeled with names, IDs and missing slots.

## Packaging checks

The release builder passed its allowlist, local-link, machine-path, ZIP CRC and archived-byte checks. It rebases public example paths and excludes exact local receipts, caches, virtual environments and private inputs. Both review archives were extracted to fresh locations; the standalone skill passed Skill Creator validation, the relocated live example passed its file audit, and the relocated four-angle inventory initialized as one identity. Package checksums and byte counts are written beside the ZIPs. Final review status is recorded in the release checklist.

## Limits

The user-reported long production run informed the workflow; its private outputs were not audited or included. No 180-image rerun was performed. This candidate has no measured large-roster throughput benchmark, live provider-outage recovery trial, cross-platform qualification or guaranteed background execution after a session ends. Unavailable-provider behavior is explicit in the skill and was reviewed as an instruction path, not induced against the live service. Human final artistic acceptance remains pending.

The helper is a single-writer state manager. Codex still supplies visual inventory and image-tool calls. Automatic live-inventory split/merge migration is unsupported; the documented supplemental-run flow preserves completed work. See [workflow comparison](WORKFLOW_COMPARISON.md).
