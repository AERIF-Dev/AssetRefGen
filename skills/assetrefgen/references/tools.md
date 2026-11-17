# Reference file tools

These existing per-asset helpers are shared by all modes. Use [roster state tools](roster-tools.md) for automated ordering, checkpoint/recovery, presets and review ZIPs. The wrapper also accepts `mode: single`; use that when one asset needs resumable state or a requested review ZIP without final artistic approval. The accepted-set `pack` below retains its original approval contract.

Run `scripts/reference_tools.py` with Python 3.10+ and Pillow 10.1+. In the examples below, run from the skill directory or replace the script path with the installed script's path. Asset paths can be absolute or relative to your working directory. If Pillow is missing, install `scripts/requirements.txt` in the project's Python environment.

Use `python scripts/reference_tools.py --help` or `python scripts/reference_tools.py COMMAND --help` for options. Results are JSON on stdout. File checks that do not pass exit with status 1. Invalid arguments, unsafe paths and other workflow errors exit with status 2.

## Initialize from supplied evidence

```text
python scripts/reference_tools.py init arc_cutter --category vehicle --style "ink and wash" --master forward_anchor.png --required-views bow port aft starboard top --optional-views underside --source concept.png --source markings.png
python scripts/reference_tools.py init inlet_valve --category prop_machinery --style "neutral product render" --brief written_brief.md
```

The asset path must be new and its parent must exist. The asset ID defaults to the new directory's name. Use `--asset-id` to set it explicitly. The master defaults to `master_front.png` and the required views default to `front left back right`. Specify at least four required view names in delivery order. Put any additional views needed for delivery in `--required-views` so the audit checks for them, and use `--optional-views` for supplemental views. IDs and view stems use ASCII letters, digits, underscores or hyphens. Names that differ only by case collide. Use `--source` for each source image, or `--brief` for the file containing the brief.

The tool creates `manifest.json`, `identity.md`, `qa.md`, and the `source/`, `revisions/` and `provenance/` folders. Copied inputs retain their original bytes; the manifest records their paths, original paths and SHA-256 hashes. Complete the two Markdown templates with findings and decisions. The manifest contains `asset_id`, `category`, `style`, `master`, `required_views`, `optional_views`, `sources`, `approvals` and `geometric_consistency`. Both approval booleans (`visual_direction` and `reference_set`) start false, and `geometric_consistency` starts `unverified`.

## Freeze and record generation

```text
python scripts/reference_tools.py snapshot arc_cutter r01_before_port_edit
python scripts/reference_tools.py record arc_cutter try_01 --request port_call.json --output tool_output.png --selected port.png --snapshot r01_before_port_edit
python scripts/reference_tools.py record arc_cutter try_02 --request second_call.json --output alternate.png
```

`snapshot` copies the current top-level files byte for byte into `revisions/REVISION_ID/` and prints their hashes. Earlier snapshots, sources and generation records stay where they are. The CLI treats these evidence directories as write-once and never reuses a revision or record ID.

`record` logs an **already executed** request. Save the exact request arguments as a JSON object with its nonempty `prompt`, ordered `referenced_image_paths` when used, and `transparent_background` if supplied. Prefer absolute reference paths; relative paths are interpreted from the JSON file's directory. Use files rather than implicit conversation images so inputs can be hashed. Record immediately and use immutable input paths for edits so the hashes reflect the bytes sent.

The command copies the exact request bytes and raw image bytes into `provenance/RECORD_ID/`. The receipt includes the tool, ordered input hashes, raw image hash, dimensions and Pillow mode, and any selection. The default tool is `image_gen.imagegen`. Set `--tool` for a different tool and set `--model` only when the tool exposes the actual model. The built-in tool leaves model, seed and quality unexposed. If another provider returns a seed, quality, task ID or cost, record the actual value and the record ID in `qa.md` or a separate provenance note. Log prepared or skipped requests as notes with their true status.

Omit `--selected` to preserve a raw candidate without changing the working set. A selection must be a still PNG and use a master or view filename from the manifest. In normal revisions, pass `--snapshot REVISION_ID` to replace an existing selection; the snapshot must contain the current bytes of that file. An explicit `--overwrite` can replace a selected file when it isn't a referenced input. The request and raw output paths cannot also be the selected path. Clear set approval before changing selections and get fresh approval for a changed set.

## Inspect and compare

```text
python scripts/reference_tools.py audit arc_cutter
python scripts/reference_tools.py sheet arc_cutter --views bow port aft starboard top --out arc_cutter/native.png --preview-out arc_cutter/preview.png
python scripts/reference_tools.py compare --before arc_cutter/revisions/r01_before_port_edit --after arc_cutter --views bow port aft starboard top --out arc_cutter/compare.png --preview-out arc_cutter/compare_preview.png
```

`audit` checks still PNG readability, dimensions, Pillow mode, PNG bit depth and file SHA-256. The master and required views must exist. Missing optional views are allowed; optional files that exist must also be valid and match the common canvas dimensions. Mode variation is reported and allowed. These are file checks only; the audit always reports geometry as unverified.

With no `--views`, a sheet uses the manifest's order: required views, then present optional views. A comparison uses that same order and asks for an explicit shared list if the two orders differ. Pass `--views` to use an alternate order or to compare directories without manifests. Any explicitly requested view must exist. Each panel keeps its original pixel dimensions and decoded RGBA pixel values, including alpha, with labels in the gutters. Panels can have different dimensions. Sheets reject 16-bit PNG panels to avoid silently reducing their precision; the audit still reports them. The separate optional preview fits within 1800 × 1200 pixels.

The sheet result records each panel rectangle and both input and output hashes. Comparisons report byte equality and exact decoded RGBA pixel equality per named view; no resizing, perceptual tolerance or color profile transforms enter that equality check. Inspect the individual PNGs and complete visual QA separately. Output directories must exist and output paths must differ from each other and the input aliases. Existing sheets need `--overwrite`; preserved evidence cannot be replaced by sheet outputs.

## Optional ZIP

```text
python scripts/reference_tools.py pack arc_cutter --out arc_cutter_accepted.zip --reference-set-approved
```

Run only after obtaining explicit reference-set approval and recording it in the QA file and as manifest `approvals.reference_set: true`. Packaging requires the flag, the manifest approval and a passing file audit. The ZIP contains the selected master and available named views, the manifest, and the identity and QA documents. Sources, historical candidates and snapshots are omitted; the manifest still retains original source paths. A ZIP does not start a 3D handoff.

Run the file-only CLI fixtures with `python -B scripts/test_reference_tools.py`.
