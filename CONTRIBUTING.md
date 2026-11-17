# Contributing to AssetRefGen

Start from a fresh checkout. The skill lives in [`skills/assetrefgen/`](skills/assetrefgen/SKILL.md), with workflow instructions in `references/`, Python helpers and their tests in `scripts/`, and output scaffolds in `assets/`. Project tooling lives in the root `scripts/` directory. [Public examples](examples/README.md) illustrate the Single Asset, Roster Mode, and folder workflows.

## Validate a change locally

Use Python 3.10 or later. From the repository root, run these commands in your chosen Python environment.

```sh
python -m pip install -r requirements-dev.txt
python scripts/validate_project.py
python -m unittest discover -s skills/assetrefgen/scripts -v
python -m unittest discover -s tests -v
```

Validation uses checked-in fixtures and makes no image-service calls. Add a focused regression test when changing how the helpers preserve source bytes, validate selected images, resume interrupted work, or report omissions in a review ZIP. For a documentation or workflow change, check the affected instructions against the skill and exercise the relevant command or example.

## Share reproducible examples

- Keep fixtures small. Use your own art or material you have permission to publish with the project.
- Strip personal data, machine paths, credentials, and private art or prompts before sharing files or logs. Preserve relevant image hashes and explain any provenance rebasing or redaction.
- Mark generated, imported, and simulated results accurately. State which visual checks you performed and record any remaining drift.
- Include reproduction steps and the checks you ran when opening a pull request. Existing fixtures cover the automated checks, so a paid generation run is unnecessary.
