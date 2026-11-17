# Roster and folder orchestration

Use [roster-tools.md](roster-tools.md) for the inventory schema and commands. The helper manages files and progress; **Codex performs visual detection, identity grouping and generation through the available image tool**. It is not a standalone detector or provider daemon.

## Inventory once

1. Enumerate supported concept images in the requested folder in stable relative-path order. Inspect the whole collection before assigning identities. Exclude the current output directory, previews, generated results and unrelated files. Document unreadable/unsupported inputs rather than silently skipping them. Use nested folders when requested; record the traversal scope.
2. Inspect full images and detail regions. Count **unique designs**, not appearances. Multiple camera angles, repeated background figures, and several illustrations of one design are evidence for one asset. Similar silhouettes alone do not prove sameness: compare anatomy, face, materials, equipment and distinguishing markings. Do not merge variants with meaningful identity differences. Detect repeats across files as well as within a sheet.
3. Assign stable IDs in the first inventory and freeze them. Names may change without renumbering directories. Keep source IDs, relative source paths, original hashes and EXIF-oriented pixel boxes. Group all appearances under the same asset and note the reasoning. Create a numbered locator for each source; repeated appearances use the same asset number/ID. Preserve original bytes and separate lossless crops; a crop can retain adjacent/occluding material and is not an isolated generated master.
4. Record user-defined display groups independently from anatomy categories (for example cast, wildlife, equipment). Use anatomy category rules for generation. Record unknown/occluded details, plausible reconstruction, counts, proportions and side-specific features in the identity brief. Do not embed a particular project roster or art direction in the skill.
5. If requested count differs from visible unique designs, report the mismatch. Invent additions only when the task explicitly authorizes creative expansion. Label these `invented`, preserve their written brief and style evidence, and state their count separately. Never invent source coordinates or claim proposed geometry was visible.

For genuine ambiguity, present a compact inventory: `ID | thumbnail/source box | proposed identity/group | uncertainty`. Ask only about uncertain grouping/count/separation; keep unaffected work moving. Do not ask for routine artistic approval in an authorized unattended run. A requested fixed count does not resolve identity ambiguity by itself.

If the answer requires splitting or merging an unresolved entry, keep the current batch and all completed identities intact. The helper does not migrate a live inventory. Create a linked supplemental inventory containing only the unresolved/redefined identities, record which old IDs it supersedes, and combine both runs in the final report. Do not reinitialize and regenerate unaffected completed assets. A simple confirmation that does not change identity grouping can use `confirm` on the existing entry.

## Schedule the existing per-asset workflow

The default is `per-asset-complete`: master, inspect, four views, QA and sheet, then the next asset. Use `all-masters-first` when requested or prioritizing whole-roster coverage: generate and select each master, then derive each set. A failed/ambiguous master does not prevent other masters or views of successful masters. Preserve user group/asset priority in the inventory order; optional extras come last.

Use the shared [prompts](prompts.md), [categories](categories.md), [presets](presets.md) and [record command](tools.md). The selected master anchors all directions. Do not re-interpret the entire group image for every view. The source hierarchy is original visible evidence → crop → selected master → derived views; the master is the direct editing anchor, while original evidence still governs identity corrections.

Keep subjects complete and separate. A master can use a useful three-quarter view; in that case retain it as e.g. `master_concept.png`, and generate a distinct front. Reuse a front master as `front.png` only after inspecting it and recording that byte-for-byte reuse. Never call a crop a generated master. Establish unknown hidden anatomy once, then carry it consistently through the views.

## Checkpoint at image boundaries

Before a generation, save its exact request in the asset's pending-request area. After success: copy output out of the tool cache, record actual request/raw output using `reference_tools.py record`, select the named file, and run the batch checkpoint. Inspect the output before declaring the corresponding task usable. Keep unknown provider fields explicitly unexposed.

The filesystem can lead the manifest if interrupted between writes. Resume reconciles real PNGs and immutable provenance. If raw output exists but selection/receipt is unfinished, complete that bookkeeping rather than making a second generation call. A present but unreviewed master must be reconciled and visually checked before it can anchor directions. A prepared prompt alone is not execution evidence. Review unexpected or changed bytes; do not overwrite or silently adopt them as a fresh completion. Never reset the batch to erase failures or correction budgets.

Use one state writer per batch. Provider-supported parallel calls can return independently, but save and checkpoint results serially. A process lock is not a promise of provider concurrency or persistent background execution. At an environment limit, save remaining tasks and exact resume instructions; do not claim the run continues after the session ends.

## Review and recovery

Each selected output needs visual inspection; final QA applies the selected preset. A partial master or missing direction remains partial. Record task, error, available result, attempt count and whether transient, unusable, or service-restricted. Work through independent tasks first. A failed front view should not discard the master or other directions. Follow the bounded retry policy in [presets](presets.md).

Build per-asset native sheets in manifest order (default front, left, back, right), then resized previews for individual sets, category masters/views and all-roster masters/views. Label thumbnails with stable ID and name, show missing slots clearly, and retain native files for modeling. Galleries are navigation aids, not modeling inputs or evidence of matched physical scale.

Deliver a review ZIP when requested, without inserting an artistic approval gate. Include usable partial images and a clear completeness/missing report; do not mark partial sets ready as full sets. Original sources, raw records and revisions stay in the local batch even if omitted from a compact review ZIP. User approval remains separate; the existing approved-set export requires actual approval.
