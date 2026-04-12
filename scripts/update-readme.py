#!/usr/bin/env python3
"""
Update README.md version badges and download links.

Usage:
    python scripts/update-readme.py <version> [--prerelease]

Examples:
    python scripts/update-readme.py 2.8.0              # Stable release
    python scripts/update-readme.py 2.8.0-beta.1 --prerelease  # Beta release
"""

import argparse
import re
import sys

# Semver pattern: X.Y.Z or X.Y.Z-prerelease.N
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z]+\.\d+)?$")

# Semver regex for matching existing versions in README content
# Prerelease MUST contain a dot (beta.10, alpha.1, rc.1) to avoid matching platform suffixes (win32, darwin)
SEMVER_RE = r"\d+\.\d+\.\d+(?:-[a-zA-Z]+\.[a-zA-Z0-9.]+)?"
# Shields.io escaped pattern (hyphens as --)
SEMVER_BADGE_RE = r"\d+\.\d+\.\d+(?:--[a-zA-Z]+\.[a-zA-Z0-9.]+)?"

# README section markers
BETA_BADGE_START = "<!-- BETA_VERSION_BADGE -->"
BETA_BADGE_END = "<!-- BETA_VERSION_BADGE_END -->"
BETA_DL_START = "<!-- BETA_DOWNLOADS -->"
BETA_DL_END = "<!-- BETA_DOWNLOADS_END -->"
STABLE_BADGE_START = "<!-- STABLE_VERSION_BADGE -->"
STABLE_BADGE_END = "<!-- STABLE_VERSION_BADGE_END -->"
STABLE_DL_START = "<!-- STABLE_DOWNLOADS -->"
STABLE_DL_END = "<!-- STABLE_DOWNLOADS_END -->"
REPO_URL = "https://github.com/tleub-ebp/WorkPilot-AI"

DOWNLOAD_TEMPLATE = """\
| Platform | Download |
|----------|----------|
| **Windows** | [WorkPilot-AI-{v}-win32-x64.exe]({repo}/releases/download/v{v}/WorkPilot-AI-{v}-win32-x64.exe) |
| **macOS (Apple Silicon)** | [WorkPilot-AI-{v}-darwin-arm64.dmg]({repo}/releases/download/v{v}/WorkPilot-AI-{v}-darwin-arm64.dmg) |
| **macOS (Intel)** | [WorkPilot-AI-{v}-darwin-x64.dmg]({repo}/releases/download/v{v}/WorkPilot-AI-{v}-darwin-x64.dmg) |
| **Linux** | [WorkPilot-AI-{v}-linux-x86_64.AppImage]({repo}/releases/download/v{v}/WorkPilot-AI-{v}-linux-x86_64.AppImage) |
| **Linux (Debian)** | [WorkPilot-AI-{v}-linux-amd64.deb]({repo}/releases/download/v{v}/WorkPilot-AI-{v}-linux-amd64.deb) |
| **Linux (Flatpak)** | [WorkPilot-AI-{v}-linux-x86_64.flatpak]({repo}/releases/download/v{v}/WorkPilot-AI-{v}-linux-x86_64.flatpak) |
"""


def validate_version(version: str) -> bool:
    """Validate version string matches semver format."""
    return bool(SEMVER_PATTERN.match(version))


def update_section(
    text: str, start_marker: str, end_marker: str, replacements: list
) -> str:
    """Update content between markers with given replacements."""
    pattern = f"({re.escape(start_marker)})(.*?)({re.escape(end_marker)})"

    def replace_section(match):
        section = match.group(2)
        for old_pattern, new_value in replacements:
            section = re.sub(old_pattern, new_value, section)
        return match.group(1) + section + match.group(3)

    return re.sub(pattern, replace_section, text, flags=re.DOTALL)


def replace_section_content(
    text: str, start_marker: str, end_marker: str, new_content: str
) -> str:
    """Replace entire content between markers."""
    pattern = f"({re.escape(start_marker)})(.*?)({re.escape(end_marker)})"
    return re.sub(
        pattern,
        rf"\g<1>\n{new_content}\g<3>",
        text,
        flags=re.DOTALL,
    )


def section_has_links(text: str, start_marker: str, end_marker: str) -> bool:
    """Check if a section already contains download links."""
    pattern = f"{re.escape(start_marker)}(.*?){re.escape(end_marker)}"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        return False
    return "WorkPilot-AI-" in match.group(1)


def _update_or_generate_downloads(content, start, end, version, semver):
    """Update existing download links or generate them if the section is empty."""
    if section_has_links(content, start, end):
        return update_section(content, start, end, [
            (rf"WorkPilot-AI-{semver}", f"WorkPilot-AI-{version}"),
            (rf"download/v{semver}/", f"download/v{version}/"),
        ])
    return replace_section_content(content, start, end, DOWNLOAD_TEMPLATE.format(v=version, repo=REPO_URL))


def _update_beta(content, version, version_badge, semver, semver_badge):
    """Update beta sections of README."""
    print(f"Updating BETA section to {version} (badge: {version_badge})")

    badge_line = f'[![Beta](https://img.shields.io/badge/beta-{version_badge}-orange?style=flat-square)]({REPO_URL}/releases/tag/v{version})\n'
    if section_has_links(content, BETA_BADGE_START, BETA_BADGE_END):
        content = re.sub(
            rf"beta-{semver_badge}-orange", f"beta-{version_badge}-orange", content
        )
        content = update_section(
            content, BETA_BADGE_START, BETA_BADGE_END,
            [(rf"tag/v{semver}\)", f"tag/v{version})")],
        )
    else:
        content = replace_section_content(content, BETA_BADGE_START, BETA_BADGE_END, badge_line)

    content = _update_or_generate_downloads(content, BETA_DL_START, BETA_DL_END, version, semver)
    return content


def _update_stable(content, version, version_badge, semver, semver_badge):
    """Update stable sections of README."""
    print(f"Updating STABLE section to {version} (badge: {version_badge})")

    # Stable version badge
    stable_badge = f'[![Stable](https://img.shields.io/badge/stable-{version_badge}-blue?style=flat-square)]({REPO_URL}/releases/tag/v{version})\n'
    if section_has_links(content, STABLE_BADGE_START, STABLE_BADGE_END):
        content = update_section(content, STABLE_BADGE_START, STABLE_BADGE_END, [
            (rf"stable-{semver_badge}-blue", f"stable-{version_badge}-blue"),
            (rf"tag/v{semver}\)", f"tag/v{version})"),
        ])
    else:
        content = replace_section_content(content, STABLE_BADGE_START, STABLE_BADGE_END, stable_badge)

    # Download links
    content = _update_or_generate_downloads(content, STABLE_DL_START, STABLE_DL_END, version, semver)

    # Remove "no stable release yet" notice
    content = re.sub(r"> No stable release yet\.[^\n]*\n\n?", "", content)

    return content


def update_readme(version: str, is_prerelease: bool) -> bool:
    """
    Update README.md with new version.

    Returns:
        True if changes were made, False otherwise
    """
    version_badge = version.replace("-", "--")

    with open("README.md") as f:
        original_content = f.read()

    if is_prerelease:
        content = _update_beta(original_content, version, version_badge, SEMVER_RE, SEMVER_BADGE_RE)
    else:
        content = _update_stable(original_content, version, version_badge, SEMVER_RE, SEMVER_BADGE_RE)

    if content == original_content:
        print("No changes needed")
        return False

    with open("README.md", "w") as f:
        f.write(content)

    print(f"README.md updated for {version} (prerelease={is_prerelease})")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Update README.md version badges and download links"
    )
    parser.add_argument("version", help="Version string (e.g., 2.8.0 or 2.8.0-beta.1)")
    parser.add_argument(
        "--prerelease", action="store_true", help="Mark as prerelease version"
    )
    args = parser.parse_args()

    if not validate_version(args.version):
        print(f"ERROR: Invalid version format: {args.version}", file=sys.stderr)
        print(
            "Expected format: X.Y.Z or X.Y.Z-prerelease.N (e.g., 2.8.0 or 2.8.0-beta.1)",
            file=sys.stderr,
        )
        sys.exit(1)

    is_prerelease = args.prerelease or ("-" in args.version)

    try:
        update_readme(args.version, is_prerelease)
    except FileNotFoundError:
        print("ERROR: README.md not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
