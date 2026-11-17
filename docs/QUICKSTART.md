# AssetRefGen quickstart

## Start with your art

1. Install and select `$assetrefgen` in Codex. For a local trial from a source checkout, point Codex to `skills/assetrefgen/SKILL.md`. [Install guide](INSTALL.md)
2. Attach the concept art, provide a written brief, or give Codex the path to your sources. Include any design features that must survive across every view, such as the position of an asymmetric latch or the number of wheels. For measurements that matter, provide dimensions or a scale reference.
3. Ask for the references you need and give Codex an output location if your project has a preferred layout.

```text
$assetrefgen Make a separate modeling reference set for each subject in this sheet. Keep the original style and put the results in reference-output/.
```

## Choose by the number of subjects

- **Single asset.** Use one image, several images of one subject, or a written brief. A single contact sheet with a front and back of the same character still describes one asset.
- **Roster Mode.** Use one sheet with distinct subjects and request a set for each. Codex inspects the sheet and records the identities, then uses them to guide separate sets. Tell it when two figures represent alternate poses, an outfit change, or separate variants you want modeled.
- **Folder batch.** Point Codex at a folder of source images. It checks for individual assets and rosters. Give it a scope such as “all PNGs in `concepts/`” or name specific files if some should be skipped.

When identities or boundaries are ambiguous, Codex shows a compact inventory for clarification. A numbered source locator maps the inventory to positions on the source, including repeated appearances. Confirmed appearances of one design share one identity while retaining their separate source regions. If the requested count exceeds the distinct subjects found, Codex reports the difference. An explicit request to design additional subjects authorizes expansion, and those designs are identified as additions in the records.

A batch you authorize can proceed through its clear subjects without individual approval prompts. Final reference-set approval is recorded separately.

## Pick the review depth and order

**Quick** or **Quick Prototype** is the default. It limits major correction work to one attempt per asset. **Detailed** allows up to three major correction attempts per asset. Both modes include a visual review of the selected views. You can specify priorities such as “check silhouettes and attachment points” or request particular extra views.

Ask for **all masters first** if you want the run to establish a master for every available subject before deriving views. Once those masters have been checked, an authorized run advances to views unless you ask it to pause. Ask to **complete each asset before starting the next** to review full sets as they become ready.

## Review and resume

Start with the contact sheet and the per-asset `qa.md`. Use the native PNGs to check side-specific details, component counts, and material continuity. A file check verifies properties such as PNG readability and dimensions. Visual consistency and geometry require separate review.

Resume against the same output folder to pick up unfinished work. Codex uses the saved progress and validates the existing files before skipping completed work. Failed work remains visible, and unaffected assets can proceed within the original scope. If the session stops, ask Codex to resume using the checkpoint in a later session.

> Resume the batch in `reference-output/`. Keep valid completed views and retry unfinished assets within the original scope.

Use the master overview to compare subjects at a glance and category galleries to review characters, creatures, vehicles, and props in groups. If some assets are unfinished, a requested review ZIP includes usable partial results with an accurate list of missing or rejected images. Native modeling inputs remain separate from the resized previews.

See [more prompts](SAMPLE_PROMPTS.md) or read the [file helper reference](../skills/assetrefgen/references/tools.md).
