"""Validate the published project and independently installable skill."""
import re

import yaml

from build_release import ROOT, SKILL_NAME, SKILL_PREFIX, check_content, public_files, release_version, standalone_files


def validate_skill(entries, version):
    skill_entry = f"{SKILL_PREFIX}SKILL.md"
    skills = sorted(name for name in entries if name.rsplit("/", 1)[-1] == "SKILL.md")
    if skills != [skill_entry]:
        raise ValueError(f"Expected exactly one public skill at {skill_entry}, found {skills}")

    lines = entries[skill_entry].decode("utf-8").splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError(f"{skill_entry} requires YAML frontmatter")
    end = lines.index("---", 1)
    frontmatter = yaml.safe_load("\n".join(lines[1:end]))
    if not isinstance(frontmatter, dict) or not "\n".join(lines[end + 1:]).strip():
        raise ValueError(f"{skill_entry} requires a frontmatter mapping and instructions")
    name = frontmatter.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
        raise ValueError(f"{skill_entry} has an invalid skill name")
    if name != SKILL_NAME:
        raise ValueError(f"{skill_entry} name must match its directory")
    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise ValueError(f"{skill_entry} requires a nonempty description of at most 1024 characters")
    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("version") != version:
        raise ValueError(f"{skill_entry} metadata.version must match VERSION ({version})")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in metadata.items()):
        raise ValueError(f"{skill_entry} metadata must map strings to strings")

    for file in (
        "LICENSE", "agents/openai.yaml", "assets/identity.template.md", "assets/qa.template.md",
        "scripts/reference_tools.py", "scripts/roster_tools.py", "scripts/requirements.txt",
    ):
        if not entries.get(f"{SKILL_PREFIX}{file}"):
            raise ValueError(f"Missing or empty skill resource: {SKILL_PREFIX}{file}")
    agent_path = f"{SKILL_PREFIX}agents/openai.yaml"
    agent = yaml.safe_load(entries[agent_path])
    interface = agent.get("interface") if isinstance(agent, dict) else None
    if not isinstance(interface, dict) or not all(
        isinstance(interface.get(key), str) and interface[key].strip()
        for key in ("display_name", "short_description", "default_prompt")
    ):
        raise ValueError(f"{agent_path} requires display_name, short_description and default_prompt")
    if f"${SKILL_NAME}" not in interface["default_prompt"]:
        raise ValueError(f"{agent_path} default_prompt must reference ${SKILL_NAME}")


def main():
    try:
        version = release_version()
        candidates = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "skills").rglob("SKILL.md"))
        if candidates != [f"{SKILL_PREFIX}SKILL.md"]:
            raise ValueError(f"Expected a single skill in skills/, found {candidates}")
        entries = public_files()
        validate_skill(entries, version)
        check_content(entries)
        check_content(standalone_files(entries), stage="standalone skill", scope=f"{SKILL_NAME}/")
    except (OSError, ValueError, yaml.YAMLError) as error:
        raise SystemExit(str(error)) from error
    print(f"Validated {SKILL_NAME} {version} metadata, resources and public package links.")


if __name__ == "__main__":
    main()
