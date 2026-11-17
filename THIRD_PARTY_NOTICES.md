# Third-party notices

AssetRefGen is an independent AERIF-Dev project, released under the [MIT License](LICENSE). It is not an official OpenAI product and is not endorsed by OpenAI, Tripo, Meshy, or the Blender Foundation. Product names identify compatible workflows; no third-party code, logos, model weights, credits, or services are bundled.

## Dependencies installed separately

- [Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE) supplies image file validation, cropping and deterministic sheet composition. Pillow carries its own HPND license and notices.
- [PyYAML](https://github.com/yaml/pyyaml/blob/main/LICENSE) is used by development validation and carries its own MIT license. The installed skill's runtime helper dependency is Pillow.
- GitHub Actions use the separately maintained [checkout](https://github.com/actions/checkout) and [setup-python](https://github.com/actions/setup-python) actions. Their source is not vendored here.

Dependency licenses and notices remain with their distributions. The repository does not copy Codex's bundled Skill Creator or Skill Installer implementation; its project validator is maintained here and its install guide invokes the user's available installer.

## Example images and generation tools

The public example images were generated specifically for AssetRefGen from original written descriptions. They contain no supplied private game artwork. They are shared with this project under MIT; their [generation record](examples/generation-record.json) and [export notes](examples/PUBLIC_EXPORT.md) distinguish generated outputs, reused views, crops, and deterministic contact sheets.

The skill coordinates whichever compatible image tool is available in the active environment. Access, usage limits, credits, generated-image rights and restrictions remain governed by that tool's provider terms. No provider credentials or proprietary libraries are included.
