# Production workflow incorporated into v0.2.0

This comparison abstracts a user-supplied production orchestration prompt and the user's report of a roughly 5.5-hour, 36-design run. The private source image, project lore and generated production files are not included or independently audited here. The reported run is useful operational experience, not a measured benchmark of this candidate.

| Behavior | Existing single-asset workflow | v0.2.0 improvement |
| --- | --- | --- |
| Single identity, selected master, directional views | Already supported | Retained shared scripts and source→master→views process |
| Identity, anatomy, axes and provisional hidden details | Category guidance already present | Clearer flying/unusual-species rules and compact Quick identity records |
| Raw requests, source bytes, hashes, revisions and native sheets | Already supported per asset | Roster manifest, task checkpoints and recoverable queues around the same helpers |
| Group image inventory and repeat recognition | Required custom orchestration | Built into instructions; stable IDs, multiple source regions per identity, numbered locators |
| Folder concepts and cross-file duplicate designs | Required custom orchestration | Stable inventory across files, including rosters and alternate-angle sheets |
| Unattended Quick Prototype | Generic QA/review guidance | Explicit Quick default, finite correction budget, no phase-by-phase artistic approval in authorized scope |
| All masters first / complete each asset | Required long-prompt scheduling | Saved selectable generation order with automatic phase continuation |
| Failure isolation and resume | Per-asset file evidence existed | Per-image failure/retry state, recovered-image reconciliation and preserved completed files |
| User-defined category galleries and all-roster overview | Individual sheets existed | Master/view galleries and partial review packaging with missing-file reporting |
| Invented replacements for duplicate slots | Task-specific creative authorization | Explicit origin and authorization fields; count mismatch alone never authorizes invention |

Quick uses a stricter one-correction-per-asset cap than the supplied production prompt's per-view suggestion, preserving the original feature request. Detailed permits up to three recorded attempts per asset. Neither mode promises exact geometric consistency.

## Current boundaries

- Codex performs visual inventory and calls available image tools. The Python helper does not independently detect subjects, generate images, or run a provider daemon.
- No guaranteed background execution beyond the active session, provider concurrency, fixed throughput, seeds, or deterministic regenerated pixels.
- No automatic 3D-model service jobs, rigging, modeling, engine integration, publishing, or paid-provider fallback.
- Identity changes that split/merge an unresolved entry require preserving the original run and a linked supplemental inventory; automatic migration of a live inventory is not implemented.
- The new candidate is tested on small original fixtures. The long production run was not repeated. See [test results](TEST_RESULTS.md).
