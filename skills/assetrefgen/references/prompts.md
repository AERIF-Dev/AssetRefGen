# Shared prompt scaffolds

Adapt to the identity brief and chosen style. Keep exact submitted prompts and ordered input roles; these are not a style preset.

## Master
Use case: identity-preserve for source-guided edits, or appropriate generation category for a written brief.
Inputs: identity source/precise subject location; supporting style/construction evidence.
Request: complete isolated [asset], preserving [silhouette, proportions, counts, face if relevant, materials/colors, asymmetry].
Neutral configuration: [category-specific pose/state].
Camera: [master direction], level, orthographic-looking, full asset with margins.
Style: [user choice]; preserve deliberate exaggeration.
Background/light: [reference-readable treatment suited to style].
Known evidence: [visible details]. Provisional completion: [unknown areas].
Constraints: [fixed features, separable items, unwanted text/scenery, clipping].
One image; no labels inside reference. For written briefs, record invented design specifics as proposals.

## Derived view
Target: [existing view if revising]. Master: [same working anchor]. Other images: [consistent secondary/source, with explicit role].
Change only camera to [direction/projection]. Preserve identical asset, state, proportions, counts, colors/material placement, seams and side-specific details.
Match [landmark heights/framing] approximately; coordinates are requests, not guaranteed controls.
Continue [selected provisional construction] without new decoration.
One complete named view, same style/background/light.

## Targeted correction
Edit [immutable candidate]; authority [source/master].
Change only [region/mismatch] to [concrete target].
Keep [identity, geometry, pose/state, other components, camera, materials] invariant.
Inspect incidentals and reject overshoot/identity drift. A visible requested change alone does not prove success.

## Orientation and projection constraints
For asymmetric assets, specify the source-facing face, coherent coordinate handedness, and a few feature-to-view correspondences before generation. Distinguish rotating a camera from correcting the whole design's source-handedness. Keep exposed-front and closed-rear construction distinct.
For hands, state which surface faces body-forward, where the thumb lies, and the expected edge/occlusion in each view; preserve the pose rather than turning every hand toward the camera. Use landmark targets for framing, then verify the result instead of treating target coordinates as guaranteed controls.
