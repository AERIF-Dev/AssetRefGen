# QA and revisions

## Evidence levels
File validity means readable PNGs, requested names, native dimensions/modes/hashes and native sheet pixels. It does not certify visual consistency.
Visual review inspects EVERY view against source/master/set. Apply the selected [preset](presets.md): Quick focuses on identity, major anatomy/counts, configuration, approximate direction and cropping; Detailed also examines scale, seams, attachments, colors/materials and asymmetry more closely. Minor inconsistencies may remain explicitly documented.
Geometric verification requires a single approved shared mesh with verified fixed orthographic render settings. This skill does not produce or certify that without separate authorization.

## Unknowns and revisions
Record source evidence as visible/partial/unknown and reconstructed details as provisional. Written briefs do not supply hidden geometry. Preserve user style and exaggeration.
Snapshot selected files, QA and provenance before replacement. Keep exact requests and raw results immutable; hash ordered inputs before changing aliases. A satisfactory master need not be regenerated.
Use a bounded scope/retry budget. Compare intended and incidental changes: rounding a nose can shorten it; exposing fingers can rotate wrists; fixing perspective can change wheels/windows. When an edit makes no useful improvement or exaggerates existing hardware, retain the better prior view instead of selecting it merely because it is newer. Keep rejected results and reasons; prepared unexecuted requests have no output/task ID.
Check glove palm/back surfaces across front/back as well as finger count; repeated knuckle plates can conceal wrist rotation. Compare side-view component envelopes at the same frame scale to detect residual yaw. Side-view overlap is not proof of fusion, separation or clearance. Known physical scale and normalized image framing are distinct. Record a few stable camera landmarks (crown/base, soles or shaft/axle levels) on the master and compare them in every view. Same canvas dimensions or requested pixel coordinates do not establish matched framing; report a failed scale request rather than silently warping anatomy.
Before/after sheets retain native source panels with labels outside them. Separate resized previews from modeling inputs. Do not silently rescale/warp selected images to imply consistency.

## Provenance
Record actual tool, exposed model/settings or unexposed, full prompt/arguments, ordered input SHA-256, output/raw SHA-256 and dimensions, selection/rejection, known cost/task data. Inputs/instructions can be reproducible without deterministic pixels. Separate source copying, generation and sheet composition records.

## Decisions
Track direction, format, working-reference and final-set approval separately. Honor existing task authorization; don't invent an extra approval gate for every master inside an authorized pilot.
Deliver paths, sheets, QA, actual checks and limitations. Stop at the user's checkpoint or unresolved substantive issues.
Paid provider uploads/generation need separate authorization and a concrete access/settings/cost check. Available credentials/credits are not permission.
The existing single-asset `pack` exports an explicitly approved reference set. Batch `review-pack` packages work for review without claiming user approval, including usable partial results and an accurate missing-file report when requested. Raw generation receipts, sources and revision history remain in the asset folder; send that provenance separately when a handoff needs it. A manifest flag or CLI option must reflect real user approval, not create it.
