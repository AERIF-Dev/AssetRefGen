# Install AssetRefGen

Use either the Codex skill installer or the standalone ZIP to install `assetrefgen` v0.2.0. The [release page](https://github.com/AERIF-Dev/AssetRefGen/releases/tag/v0.2.0) lists the downloads and SHA-256 checksums.

The v0.2.0 helpers passed validation on Windows and Linux. The macOS installation path below follows Codex's documented discovery rules. Installation and runtime on macOS remain unverified. [Validation results](TEST_RESULTS.md)

If you already use AssetRefGen, find its current folder before installing a new copy. Check the project’s `.agents/skills`, your user skill directory, and any folder used by your installer. For an upgrade, move the entire old `assetrefgen` folder to a backup outside all skill discovery directories. A renamed folder inside a discovery directory can still expose the same skill name. [Codex skill discovery](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)

## Method A · Codex skill installer

Paste this request into Codex.

```text
$skill-installer Install assetrefgen from https://github.com/AERIF-Dev/AssetRefGen/tree/v0.2.0/skills/assetrefgen
```

Follow the destination reported by your installer. Some Codex skill-installer versions use `$CODEX_HOME/skills`, which defaults to `~/.codex/skills`. Keep one discovered copy of AssetRefGen and use that folder for the dependency step below.

## Method B · Copy the standalone skill folder

1. Download and extract the [standalone skill ZIP](https://github.com/AERIF-Dev/AssetRefGen/releases/download/v0.2.0/assetrefgen-0.2.0-skill.zip). It contains an `assetrefgen/` folder with `SKILL.md` at its root. If you already have the full project ZIP or a source checkout, use its [`skills/assetrefgen/`](../skills/assetrefgen/SKILL.md) folder instead.
2. Copy the entire `assetrefgen` folder to your user skill directory. Create the directory if needed. The resulting file path should match the table for your platform.

| Platform | User skill path |
| --- | --- |
| Windows | `%USERPROFILE%\.agents\skills\assetrefgen\SKILL.md` |
| macOS and Linux | `~/.agents/skills/assetrefgen/SKILL.md` |

For project-only discovery, copy the same folder under your project's `.agents/skills/`. [Codex skill discovery](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)

## Install the file-helper dependency

Use Python 3.10 or later in an environment that Codex can run. From the installed `assetrefgen` folder, install Pillow 10.1 or later using the skill's requirements file.

```sh
python -m pip install -r scripts/requirements.txt
```

Use `python3` if that is the name of your Python 3 command. From a source checkout, the same file is at `skills/assetrefgen/scripts/requirements.txt`.

## Check the installation

Open a new Codex session, type `$assetrefgen`, and select the skill. The Codex CLI and IDE extension also expose the skill picker through `/skills`. If an update fails to appear, restart Codex and check for duplicate installations using the folders above. [Codex skill usage](https://learn.chatgpt.com/docs/build-skills)

If you want to inspect the release first, extract either archive outside your skill directories and read the skill's `SKILL.md`, references, scripts, and templates. To try the extracted copy, point Codex directly to its `SKILL.md` and work in a disposable output folder.

To roll back, move the current version out of discovery and restore the old folder to its original location. Open a fresh session and verify the restored copy appears in the skill picker.

Image generation depends on the tools and access available to the active session. AssetRefGen can prepare inventories and prompts when an image tool is unavailable. A paid fallback requires your explicit authorization.

Continue with the [quickstart](QUICKSTART.md).
