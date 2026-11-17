---
name: assetrefgen
description: Generate identity-anchored modeling references for a single asset, every distinct subject in a roster image, or a folder of concepts. Supports Quick and Detailed presets, four directional views, grouped galleries, and interrupted batch resume. Use for reference images, not mesh generation or gameplay implementation.
metadata:
  version: "0.2.0"
---

# Asset Reference Generator

Turn a short request into complete, organized reference sets. Preserve source identity, style and deliberate exaggeration. Use the same source → selected master → directional views → QA workflow for every asset. Never substitute crops or placeholders for generated masters.

## Route the request

- **Single:** one subject or written brief, including a sheet with several angles of that same subject. Existing [single-asset commands](references/tools.md) remain supported.
- **Roster:** distinct subjects in one image. **Batch:** multiple images from a folder, each potentially a roster. Read [roster workflow](references/roster.md) and [roster commands](references/roster-tools.md).
- **Resume:** locate the existing batch manifest in the requested project, reconcile real files, then continue unfinished tasks. Do not initialize a replacement batch. Ask for the intended batch only if several plausible runs exist.
- Default to **Quick**, including “Quick Mode,” “Quick Prototype,” and temporary Tripo/Meshy references. “Detailed” selects deeper inspection. Read [presets](references/presets.md); carry the chosen preset into every asset.

“Process this entire roster/folder” authorizes the requested subjects and normal generation phases. Continue without artistic approval between subjects, masters or views. Respect explicit review checkpoints. If count, duplicate grouping or separation is genuinely ambiguous, show a compact numbered inventory and request only the needed decision; continue unaffected subjects. A requested count does not authorize invented replacements.

## Establish identity

Read project instructions and inspect all relevant images, including small background subjects. Separate identity evidence from style references. For rosters, group repeated appearances and alternate angles of one identity under one stable ID; record every source location and crop. Preserve original bytes and create a numbered source locator.

Apply [category rules](references/categories.md). Record silhouette, proportions, anatomy/component counts, colors/materials, asymmetry, pose/state, axes and unknowns in `identity.md`. Hidden reconstruction is provisional and must stay consistent. A written brief or explicitly authorized expansion creates a proposed design, not observed source geometry. Use four appropriate directions; never force human poses onto other anatomy or assume fit-to-frame images establish world scale.

## Generate and derive

Use available built-in image generation/editing by default; consult imagegen instructions where present. Inspect local edit targets before calling the tool. If unavailable, preserve the queue and state the blocker. Never silently switch to a paid API/CLI fallback or circumvent a rejected generation.

Use [prompt scaffolds](references/prompts.md) to create one complete isolated master. Check major identity, anatomy and orientation against its source before propagating it; a usable master can be selected automatically within an authorized run. This does not set user-approval flags. A three-quarter master stays a separate master; generate a real front view. Reuse the master bytes as a directional view only if it already depicts that exact direction and configuration; record the reuse.

Derive each view using that same selected master as the primary identity anchor. Source crops and consistent prior views can be secondary evidence. Rotate the camera, not the design; preserve pose/state, anatomy, proportions, components and asymmetry. Do not mirror one side to fabricate the other. For a requested source-handedness correction, validate and propagate the corrected master first.

Support **per-asset-complete** and **all-masters-first** orders. Choose the latter when requested or when roster coverage is the priority; continue into views automatically. Save the order and any category priority in the inventory. Process manageable chunks with one writer to a batch state file; use parallel generation only when the actual provider supports it.

Save exact requests before execution. Immediately copy every successful output into the project, record raw bytes and exposed generation information with the existing record helper, then checkpoint after **each view/master and each asset**. Unknown model, seed, settings, cost or task ID stay unexposed. On interruption, inspect files and receipts before regenerating; preserve valid partial results, completed sets and revision history.

## Inspect and deliver

Audit files and visually inspect each output under the selected [preset](references/presets.md), following [QA and revisions](references/quality.md). Quick permits minor inconsistencies and at most one targeted major-error correction per asset; Detailed permits up to three. Snapshot before replacement, preserve rejected evidence, and do not select a worse revision. Mark unusable outputs incomplete. Record per-task failures and continue independent work; retry transient failures only within a finite recorded budget, never policy rejections.

Create individual native contact sheets plus separate previews, category master/view galleries and a full-roster overview. Deliver source locator, manifests, concise QA, actual counts, usable/complete/incomplete lists, and an exact resume command. Package requested ZIPs as **review packages**, including usable partial sets with missing-file reports. Packaging is not artistic approval; the existing approved-set export remains separately gated.

File validity, visual consistency and verified geometry are separate. Generated views are orthographic-looking, not exact projections of a shared mesh. Do not order 3D jobs, rig assets, start gameplay work or publish without separate authorization. Do not promise unattended continuation beyond the actual executing session; leave a durable checkpoint when runtime limits interrupt it.
