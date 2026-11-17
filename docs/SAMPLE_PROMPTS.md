# Sample prompts

Select `$assetrefgen` in Codex and attach or point to the corresponding art. If you are trying a source checkout, give Codex the path to [`skills/assetrefgen/SKILL.md`](../skills/assetrefgen/SKILL.md).

## Short invocations

```text
$assetrefgen Make four views of this character.
$assetrefgen Process this entire roster.
$assetrefgen Process every creature in this image for 3D modeling.
$assetrefgen Process the characters and creatures in Quick Mode. Make a master and four views for each, and package a review ZIP.
$assetrefgen Generate references for all 36 designs, grouped by category.
$assetrefgen Process the concept art in concepts/ and save it in reference-output/.
$assetrefgen Resume my unfinished roster in reference-output/.
$assetrefgen Create detailed modeling references for this entire lineup.
```

Counts are checked against unique source identities. Requesting 36 designs does not authorize inventing replacements if the image contains fewer.

## One asset from several views

> Make a modeling reference set from these panels. All three show the same terracotta robot. Preserve the cream face inset, short chimney, and pale blue chest badge.

## One asset from a written brief

> Make reference views for a freestanding copper signal lantern with a six-sided frame, amber glass, a dark hexagonal base, and one arched handle. Use a neutral background and include a top view. Record any details you need to invent.

## Roster Mode for a lineup

> Make a separate modeling reference set for each subject in this lineup. Use the quick pass and keep the storybook style.

## Mixed character and creature roster

> Make a separate reference set for each distinct character and creature on this sheet. Group repeated appearances of the same design and label their positions on a numbered source locator. If you find fewer than ten distinct designs, tell me how many are present and use the designs backed by the source.

## Mixed objects with specific priorities

> Make reference sets for the teal rover and the copper lantern in Detailed Mode. Check the rover's four wheels, front bumper, and fixed sensor mast. Give the lantern a top view so I can see the frame shape.

## Resolve an ambiguous sheet

> Read this sheet and give me a short inventory before generating. The first two panels might be front and rear views of the same creature. Flag any overlap or cropped details.

## Process a folder

> Create reference sets for the subjects in the PNGs in `concepts/`. Some files are lineups and some are individual assets. Use quick mode and save the sets to `reference-output/`.

## Make all masters first

> Use Quick Prototype. Make and check the masters first, then proceed through the views. Include a master overview and separate galleries for characters and creatures.

## Finish each set in turn

> Finish the master, views, and QA for each asset before starting the next. Start with the kiln robot, then the moth keeper.

## Resume a batch

> Resume the batch in `reference-output/` using the same inputs. Reuse valid completed files, continue unfinished assets, and report anything still blocked.

## Package completed work for review

> Package the completed sets for review and include a list of anything missing, with the reason and the next step for each omitted asset.

## Prepare work without generation

> Inspect these concepts and prepare the inventory, view lists, and image prompts. Stop before generating images.
