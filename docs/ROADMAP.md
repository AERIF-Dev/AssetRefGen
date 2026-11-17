# AssetRefGen v0.3.0 roadmap

Status: proposed follow-up work, recorded 2026-11-17. These features are not part of v0.2.0 and will be developed and tested separately after its publication. This roadmap is not a promise that the proposed visual rules or equipment extraction already run automatically.

## 1. Standardized humanoid poses

Make one consistent neutral A-pose the default for humanoid modeling references:

- Front: palms face the camera, with thumbs outward.
- Back: backs of the hands face the camera, preserving exactly the same wrist and arm orientation as the front.
- Sides: anatomically consistent projections of that same fixed pose; do not rotate wrists or arms to expose extra hand details.
- Support T-pose and alternative conventions when requested.

Add a small original visual pose guide with clearly labeled correct and incorrect examples. Define the conventions precisely enough to avoid camera-relative/anatomical-side confusion. Test all four directions together; do not claim exact geometry from independent image generation.

## 2. Additional reference views

Keep front, left, back and right as the standard output. Extend optional-view selection for top, bottom, three-quarter, close-ups and category-specific directions. Choose extras according to anatomy and modeling needs, after the base turnaround unless the user explicitly prioritizes an extra.

The v0.2.0 helpers already accept additional named views. This planned work makes their selection and guidance easier and more category-aware; it does not replace the four-view baseline.

## 3. Equipment / Sub-Asset Mode

Support separately requested references for visible clothing, armor, jewelry, accessories, tools, held objects and other detachable components.

- Inventory selected items and distinguish separate objects from body features, integrated mesh detail and ambiguous attachments.
- Preserve source appearance and proportions; assign stable item IDs and record parent-character relationships.
- Generate one isolated master and appropriate directional views per selected item using the shared reference workflow.
- Support character-only output and character-plus-equipment extraction. Do not remove equipment or expand the asset count silently.
- Record uncertain construction and separation assumptions; ask only about genuinely consequential ambiguity.

Acceptance should include mixed equipment, repeated/shared components, an interrupted extraction batch, parent/child identity tracking and a case where a decorative detail must remain part of the body.

## 4. Visual reference library

Create a small, original, style-neutral set of examples covering good/bad A-poses, T-poses, four-view consistency, roster separation and equipment extraction. Label correct/incorrect intent clearly and make the examples reusable without imposing their art style on source concepts.

Keep `SKILL.md` concise. Store detailed guidance and visuals in supporting files and load them only when relevant. Add no private production imagery or project-specific lore.

## 5. Preserve the current workflow

Single, Roster, Batch, Quick, Detailed and Resume must continue to work. Fast temporary prototyping remains a core acceptance criterion. Keep Quick as the efficient default with bounded correction effort; do not introduce production-quality consistency requirements, exhaustive QA or repeated artistic approval checkpoints by default.

Retain source preservation, provenance, stable IDs, per-image checkpoints, failure isolation, resumed-file reuse and honest geometric limitations. Extend existing mechanisms rather than creating a separate pipeline.

## Proposed delivery order

1. Finish and verify v0.2.0 publication.
2. Specify pose conventions and author the small visual guides.
3. Add optional-view guidance without delaying base sets.
4. Design and implement parent/child equipment inventories and extraction.
5. Run focused new tests and all existing regression suites before a separate v0.3.0 review.

No v0.3.0 implementation, generation run, release date or acceptance is implied by this document.
