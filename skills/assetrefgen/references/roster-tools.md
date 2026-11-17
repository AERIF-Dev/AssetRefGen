# Roster state and recovery CLI

`scripts/roster_tools.py` extends the existing single-asset `reference_tools.py` workflow. It does not detect subjects, decide identities, call an image model, or perform visual QA. Codex inventories the inputs visually, writes the inventory, executes image generation through the supported tool, and records its actual observations. Several appearances of one design belong to one asset with several regions. Distinct designs get distinct stable IDs. A requested count is not permission to invent missing designs.

The CLI uses Python and the same Pillow dependency as `reference_tools.py`. Run the examples from the `assetrefgen` directory. One writer per batch is required; concurrent generators, checkpoint commands, or external edits are unsupported. Writes of roster state are atomic. Initialization is staged and renamed into place only after all sources, crops, locators, manifests, and state are valid. An interrupted initialization may leave a hidden staging directory; it is not a published batch and can be inspected separately. Existing batches are never replaced by `init`.

## Inventory schema

Paths in `sources` are relative to the inventory JSON's directory, use forward slashes, and must remain underneath that directory. Absolute paths, `..`, symlinks, junctions, case-colliding IDs, and unsafe output names are rejected. Sources can have identical basenames in different folders; explicit source and asset IDs control identity and output paths.

```json
{
  "schema_version": 1,
  "mode": "roster",
  "quality": "quick",
  "generation_order": "per-asset-complete",
  "desired_count": 2,
  "creative_expansion_authorized": false,
  "count_rationale": "Three visible appearances represent two distinct designs; the two hull views share markings.",
  "sources": [
    {"id": "reference_a", "path": "inputs/roster.png"}
  ],
  "assets": [
    {
      "id": "harbor_cutter_01",
      "name": "Harbor cutter",
      "origin": "source-derived",
      "category": "vehicle",
      "group": {"id": "harbor", "label": "Harbor equipment"},
      "style": "Painted wood, blue hull, brass fittings",
      "views": ["bow", "port", "aft", "starboard"],
      "master": "master_bow.png",
      "regions": [
        {"source_id": "reference_a", "box": [0, 0, 600, 600]},
        {"source_id": "reference_a", "box": [600, 0, 1200, 600]}
      ],
      "identity_spec": {"silhouette": "Long bow", "landmarks": ["Brass rail", "Blue hull"]},
      "inferences": ["Unseen stern construction is inferred from visible materials."],
      "separation_rationale": "These regions show the same hull in two views."
    },
    {
      "id": "harbor_valve_02",
      "name": "Harbor valve",
      "origin": "source-derived",
      "category": "prop_machinery",
      "group": {"id": "harbor", "label": "Harbor equipment"},
      "style": "Red enamel and dark cast iron",
      "views": ["front", "left", "back", "right", "top"],
      "master": "master_front.png",
      "regions": [{"source_id": "reference_a", "box": [0, 600, 600, 1200]}],
      "identity_spec": {"landmarks": ["Circular handwheel", "Four mounting bolts"]},
      "inferences": [],
      "separation_rationale": "A separate mechanical prop, not part of the vessel."
    }
  ]
}
```

Replace the sample path, dimensions, identities, styles, and regions with the actual visual inventory. Boxes are integer pixel `[left, top, right, bottom]`, with exclusive right/bottom edges, measured after EXIF orientation. A full-image source still needs an explicit full-image region. Exact original source bytes are copied into each asset's `source` directory. Crops are EXIF-oriented PNG derivatives; each records its source ID, box, path, and hash in the asset manifest. `locators/<source_id>.png` numbers identities in inventory order and repeats the same number/ID on every appearance of one identity.

Required fields are shown above except `quality` (defaults to `quick`), `generation_order` (defaults to `per-asset-complete`), `desired_count`, `creative_expansion_authorized` (defaults false), `origin` (defaults `source-derived`), and `group`. `mode` is `single`, `roster`, or `folder`; single requires one inventoried identity. All modes share the same recovery behavior. Folder mode does not infer one identity per file: the visual inventory still decides grouping across files. `desired_count` records a comparison with actual inventory length and never pads the roster.

Anatomy categories remain `humanoid`, `creature`, `weapon`, `vehicle`, `architecture`, and `prop_machinery`. Custom `group` labels are independent display categories; the safe group `id` controls gallery filenames. One exact group ID spelling must use one label. IDs and view names use ASCII letters, digits, underscores, or hyphens, up to 64 characters, excluding Windows reserved names. Master filenames end in `.png`; views must be distinct and include at least four names. `contact_sheet` is reserved. Names, styles, view terminology, and asset counts are never inferred from a canned roster.

For a genuinely authorized invented design, set root `creative_expansion_authorized: true`, asset `origin: "invented"`, and an inline nonempty `brief` string. Omit regions or use `[]`; do not fabricate source boxes. The CLI preserves that brief in `briefs/<asset_id>.txt` and the asset's `source/brief.txt`. Wholly invented batches use `sources: []`. Codex must only set authorization after the user actually permits creative expansion. `identity_spec`, `inferences`, and `separation_rationale` remain required.

For unresolved grouping or identity, set asset `status: "needs_confirmation"` and a nonempty `confirmation_reason`. This prevents scheduling that asset while unaffected assets continue. Only use `confirm` after the human resolves the ambiguity. If their resolution changes the inventory (such as merging or splitting assets), initialize a supplemental batch containing only the resolved, unfinished identities. Preserve completed IDs and their existing outputs in the original batch. Do not silently change IDs or regenerate completed work. Record the relationship between batches in their count/separation rationales and final delivery notes.

## Initialize and select work

```powershell
python scripts/roster_tools.py init output/harbor_batch --inventory work/harbor_inventory.json
python scripts/roster_tools.py status output/harbor_batch
python scripts/roster_tools.py next output/harbor_batch
python scripts/roster_tools.py resume output/harbor_batch
```

Create `output` first. Repeating `init` with the same inventory, source paths, and source bytes is idempotent. A changed inventory or changed source causes an error. `status`/`resume` reconcile the preserved batch files without requiring the original source folder to remain available. They do not rewrite files or silently trust a changed selection. The stored inventory is immutable; its fingerprint is verified on every command.

`next` returns a concrete `task` with stable `asset_id`, `kind`, `filename`, and destination `path`. Kinds are `master`, `view`, `contact_sheet`, `visual_qa`, `reconcile`, and `settle_correction`. The `next` member contains that asset's full status. A `null` task means there is no runnable work; inspect `held`, not merely `complete`. Missing selected filenames are reported in manifest order. Valid uncheckpointed images are preserved and produce a `reconcile` task; finish provenance and visual bookkeeping before using them as anchors or generating dependents. Changed or missing previously recorded images produce drift and are held.

`per-asset-complete` finishes an asset before advancing. `all-masters-first` schedules every eligible missing master first, then missing views for assets whose masters succeeded. A failed or ambiguous asset is held, so it cannot repeatedly block healthy assets. No command calls generation automatically.

## Record each image and checkpoint

Use the existing record machinery with the actual tool request and its raw output. Do not reconstruct a request from a planned prompt after the fact. Model and seed remain unexposed when the tool does not reveal them.

```powershell
python scripts/reference_tools.py record output/harbor_batch/assets/harbor_cutter_01 master_01 --request work/master_request.json --output work/master_result.png --selected master_bow.png
python scripts/roster_tools.py checkpoint output/harbor_batch harbor_cutter_01 --qa pending --visual-reviewed --notes "Master saved; hull markings checked; reverse views still pending."
python scripts/roster_tools.py next output/harbor_batch
```

Repeat the record/checkpoint sequence after **every** selected image, including each view. Requests, raw output, selected image hashes, and available provenance are preserved. New selections require a matching generation receipt or honest import/reuse receipt and `--visual-reviewed` after actual inspection. Checkpointing does not replace selected files. A pending checkpoint may record a valid partial set; it does not declare completion. Never write an output over an original or crop. `qa.md` retains cumulative observations and `progress.md` summarizes saved state; `roster.json` remains authoritative, and `status` checks current disk integrity.

For an explicitly imported image, a reused master/front image, or a landed image whose original generation receipt is unavailable, preserve honest local-file evidence instead of fabricating a generation call:

```powershell
python scripts/roster_tools.py adopt output/harbor_batch harbor_cutter_01 --file bow.png --source output/harbor_batch/assets/harbor_cutter_01/master_bow.png --origin reused --record-id bow_reuse_01 --notes "Reuse the approved-looking bow master as the front view; no new generation call."
python scripts/roster_tools.py checkpoint output/harbor_batch harbor_cutter_01 --qa pending --visual-reviewed --notes "Reused bow inspected at full resolution."
```

`adopt` records `local.imported` or `local.reused`, the source hash, copied bytes, and notes. It can reconcile an already selected identical file without rewriting it. Replacing different selected bytes requires a correction reservation. Missing historical generation provenance remains missing; a local import receipt is explicitly not a generation receipt.

When all selected images pass file checks:

```powershell
python scripts/roster_tools.py sheet output/harbor_batch harbor_cutter_01
python scripts/roster_tools.py checkpoint output/harbor_batch harbor_cutter_01 --qa pass --visual-reviewed --sheet-current --notes "Visually reviewed every view and sheet: hull proportions, rail position, blue markings, bow/stern direction, framing, and background are consistent. Hidden stern remains inferred."
```

`sheet` delegates to the existing native contact sheet implementation, writes `contact_sheet.png` and a bounded `contact_preview.png`, and does not alter selected panels. A complete set needs its master, all four-or-more requested views, matching image dimensions, both readable sheets, matching provenance, unchanged recorded evidence, no active task failures or unusable images, and a fresh explicit visual QA pass. `--visual-reviewed` asserts actual visual inspection, not just a file audit. `--sheet-current` asserts the sheet depicts the selected views. These assertions are the operator's responsibility; Python cannot establish identity consistency or correct viewpoint. A QA pass is **not user approval**, and the manifest's approval flags remain false. Geometry remains unverified.

Use `--qa fail --file aft.png --visual-reviewed --notes "...specific defect..."` to mark a particular view unusable while independent views continue. The failed selection and derived sheets containing it are excluded from usable review exports. Without `--file`, a failed QA review holds the entire set because the uncertain scope is unknown. It is not repeatedly scheduled for visual QA. Do not label a quality-limited result complete. A later explicit real review can resolve a full-set hold, or a bounded correction may be required. Targeted unusable images require a successful bounded correction before full-set completion.

## Failures, ambiguity, corrections

```powershell
python scripts/roster_tools.py fail output/harbor_batch harbor_valve_02 --file left.png --kind generation --notes "Transient service error; no selected output returned."
python scripts/roster_tools.py retry output/harbor_batch harbor_valve_02 --file left.png --notes "Single deliberate retry after service recovered."
python scripts/roster_tools.py fail output/harbor_batch harbor_valve_02 --file right.png --kind service_restriction --notes "Service rejected this view request."
python scripts/roster_tools.py confirm output/harbor_batch harbor_cutter_01 --human-resolved --notes "User confirmed these two appearances are one design."
```

Failure kinds are `generation`, `io`, `quality`, and `service_restriction`. Target a filename so a failed view does not stop independent directions. A failed master holds its dependent views while other assets continue. Transient generation/I/O failures allow at most one deliberate `retry` per filename (two total attempts), with persisted attempt counts; `next` never retries automatically. Quality failures require the correction budget, not a transient retry. Omitting `--file` records a legacy asset-wide hold with one transient retry maximum. Service restrictions become `blocked`, cannot be downgraded, and cannot be retried or corrected by this CLI. A later rejection also invalidates earlier complete state. Do not bypass a rejection by changing providers or disguising the same request. Confirmation only applies to an asset initialized as `needs_confirmation` and must record the human's actual resolution.

Start a correction **before** changing a selected image:

```powershell
python scripts/roster_tools.py correction output/harbor_batch harbor_cutter_01 --file aft.png --notes "Correct the aft rail height once against the master."
python scripts/reference_tools.py record output/harbor_batch/assets/harbor_cutter_01 aft_correction_01 --request work/aft_fix_request.json --output work/aft_fix.png --selected aft.png --snapshot roster_correction_01
python scripts/roster_tools.py checkpoint output/harbor_batch harbor_cutter_01 --qa pending --visual-reviewed --finish-correction --correction-outcome accepted --notes "Corrected aft inspected and accepted; sheet and full-set review pending."
python scripts/roster_tools.py sheet output/harbor_batch harbor_cutter_01
python scripts/roster_tools.py checkpoint output/harbor_batch harbor_cutter_01 --qa pass --visual-reviewed --sheet-current --notes "Aft correction and regenerated contact sheet visually checked."
```

The command snapshots current top-level asset files, increments the persisted correction count, and invalidates previous QA. **One reservation permits exactly one corrective service call for one target filename**, not an unlimited cycle. Quick allows one corrective call per asset; Detailed allows three. Settle every attempted correction explicitly with `checkpoint --finish-correction --correction-outcome accepted|rejected|no-output`, accurate notes, and a truthful QA status. `accepted` needs one recorded output, a valid target, and actual visual review; `no-output` cannot accompany changed selections or a recorded output. Rejected replacements remain unusable. A rejected or no-output attempt still spends its reservation. Partial-master corrections can settle with `--qa pending` before the views exist, allowing the next counted Detailed attempt. The CLI checks that only the reserved panel changes and no more than one new provenance receipt appears; `adopt` also refuses a second recorded attempt under the same reservation. Generation remains an external tool call, so the operator must obey the reservation before calling it. An exhausted budget is a reported limitation, not permission for extra automatic attempts.

Drift must be investigated. Restore exact recorded bytes from retained provenance/revisions when an accidental deletion or corruption occurred. A planned changed selection requires starting a correction while original files still match. `checkpoint` will not silently adopt unexplained edits. A damaged asset does not prevent other assets from being scheduled. Corrupt batch state or changed shared locator/brief evidence stops the batch for investigation. These tools are integrity bookkeeping, not tamper-proof storage.

## Preview and package useful results

```powershell
python scripts/roster_tools.py gallery output/harbor_batch --out output/harbor_gallery_01
python scripts/roster_tools.py review-pack output/harbor_batch --out output/harbor_review_01.zip
```

Both outputs must be new paths outside the batch. The gallery contains an overview, all-masters and all-views sheets, and separate master/view images for each anatomy category and custom group. Cells show working names, stable IDs, and explicit missing/held slots. Usable partial selections carry a review label. Native selected images remain unchanged. The ZIP includes the same overview/galleries, per-asset original sources, crops, identity manifest, cumulative `qa.md`, usable selections, sheets when current and usable, snapshots, available generation/import evidence, source locators, inventory, and `review.json`. Evidence subdirectories can contain rejected historical outputs; these are forensic records, not selected usable deliverables. Review archives include source evidence and local receipt paths and should be sanitized separately for public release.

Partial results are included by default. `review.json` records each asset's exact state, QA notes, requested missing files, invalid files, drift, failed/blocked tasks, unusable selections, packaged selection filenames, and assets with no usable selections. Missing/corrupt, unacknowledged changed, uncheckpointed, unprovenanced, blocked, and quality-failed selections are excluded; recorded usable peers survive. Full-set failed QA holds that set's selected outputs until resolved. `completed` and `partial` in command output distinguish actual results. A review ZIP does not claim user approval. The separate accepted-set `reference_tools.py pack` still requires its existing explicit user approval gates.

Run focused local regression checks with:

```powershell
python -B -m unittest discover -s scripts -p test_roster_tools.py -v
```

Tests use tiny deterministic image fixtures, including EXIF crops, multi-region identities, same-name sources, interrupted partial sets, hash drift, error isolation, protected paths, master-first scheduling, invented-design authorization, correction budgets, and partial review packaging. They do not substitute for live generation or human visual acceptance.
