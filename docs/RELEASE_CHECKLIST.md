# Release checklist

Use this checklist for `v0.2.0`, promoted from the validated `0.2.0-rc.1` candidate. Record actual check results, scope, and unresolved issues in [test results](TEST_RESULTS.md).

Preparation checks below were completed by the agent on 2026-11-17. They are separate from the owner's approval to install or publish. The source-gallery subjects beyond the kiln demonstration were intentionally not fully generated.

## Review the candidate

- [x] Check that `VERSION`, the changelog, and package filenames agree.
- [x] Use small regression fixtures for single-asset, roster, and folder inputs. Include a sheet with several views of one subject, a roster with repeated appearances, and a sheet with distinct subjects.
- [x] Check that the source and identity notes support the selected views. Review contact sheets and native PNGs for orientation, proportions, asymmetry, and component counts. Record material drift and provisional design details.
- [x] Run the reference and roster helper tests and the skill structure validator. Record what each check covers.
- [x] Exercise checkpoint and resume with existing valid files and an interrupted or failed asset. Confirm the valid work is reused and progress on unaffected assets is preserved.
- [x] Check both production orders on a small roster. Verify that the numbered locator and gallery labels match the inventory. Check a partial review package for usable sets and an accurate omission list.
- [x] Review generation-unavailable instructions and document the lack of a live provider-outage trial. Report file checks and visual checks distinctly.
- [x] Review the [gallery](../examples/gallery.png) and supporting examples for original shareable art and accurate labels. Check public exports for private imagery, credentials, and machine-specific absolute paths. Exact local receipts remain outside public ZIPs.

## Review the ZIP files

- [x] Extract the candidate full-project ZIP to a fresh directory. Verify that the skill folder, documentation, and public examples are present and that local links resolve. Repeat for the stable download as part of final public verification.
- [x] Extract the candidate standalone-skill ZIP to a fresh directory. Verify that its `assetrefgen/` folder contains `SKILL.md` and the referenced scripts, templates, and supporting files. Stable package mapping is covered by automated release tests.
- [x] Inspect both archives for virtual environments, caches, private input files, credentials, and machine-specific paths. Verify that the release archives are readable and their reported checksums match.
- [x] Confirm the instructions support review in place, optional installation to a single discovery location, and rollback with an existing installation.

## Before optional global installation

- [ ] Obtain owner approval of the candidate, back up the working skill outside discovery, then intentionally replace it. The installed working skill is unchanged by this task.

## Before any public release

- [x] Owner authorized promotion and publication of the tested candidate, with MIT as the default license. Copyright holder: verified repository owner AERIF-Dev, year 2026. Dependency notices are documented.
- [x] Owner explicitly authorized commit, push, version tag and GitHub release to `AERIF-Dev/AssetRefGen`.
- [x] Preserve proposed v0.3.0 work as documentation only; keep runtime behavior at the tested v0.2.0 scope.

## Final public verification

Complete against the exact published commit and release. GitHub's workflow and release pages provide the authoritative hosted state.

- [ ] Push the reviewed public files to `main` without force and verify the fetched commit.
- [ ] Confirm all hosted validation jobs pass before tagging stable v0.2.0.
- [ ] Verify README rendering and public gallery-image responses.
- [ ] Run the official skill installer against the public tagged directory into an isolated test destination.
- [ ] Download published assets, verify checksums, extract both ZIPs and confirm required files.
- [ ] Confirm no private source art, machine-specific paths, secrets or development outputs were published.
