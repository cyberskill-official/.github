"""Tests for release script functions."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from lib.release import (
    extract_unreleased_content,
    get_latest_version,
    get_next_version,
    update_changelog,
)


def test_get_next_version_auto():
    """Test automatic patch bump."""
    assert get_next_version("1.2.3", None) == "1.2.4"


def test_get_next_version_keywords():
    """Test major/minor/patch keywords."""
    assert get_next_version("1.2.3", "major") == "2.0.0"
    assert get_next_version("1.2.3", "minor") == "1.3.0"
    assert get_next_version("1.2.3", "patch") == "1.2.4"


def test_get_next_version_explicit():
    """Test explicit semver parsing."""
    assert get_next_version("1.2.3", "2.5.0") == "2.5.0"


def test_get_next_version_invalid():
    """Test invalid version string aborts."""
    with pytest.raises(SystemExit):
        get_next_version("1.2.3", "invalid-str")


def test_extract_unreleased_content(tmp_path):
    """Test unreleased changelog parsing."""
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("## [Unreleased]\n- Add feature A\n- Fix bug B\n\n## [1.0.0]\n- Initial release", encoding="utf-8")

    res = extract_unreleased_content(str(cl))
    assert "- Add feature A\n- Fix bug B" in res


def test_extract_unreleased_content_empty_aborts(tmp_path):
    """Test missing unreleased changes triggers exit."""
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("## [Unreleased]\n\n## [1.0.0]\nOld version", encoding="utf-8")
    with pytest.raises(SystemExit):
        extract_unreleased_content(str(cl))


def test_update_changelog(tmp_path):
    """Test changelog URL stamp string format."""
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text(
        "## [Unreleased]\n"
        "- Feature\n\n"
        "## [1.0.0] — 2026-04-01\n"
        "- Initial\n\n"
        "[Unreleased]: https://repo/compare/v1.0.0...HEAD\n"
        "[1.0.0]: https://repo/releases/v1.0.0",
        encoding="utf-8",
    )

    update_changelog(str(cl), "1.1.0", "1.0.0", "2026-04-05", "https://repo")

    out = cl.read_text(encoding="utf-8")
    assert "## [1.1.0] — 2026-04-05" in out
    assert "[Unreleased]: https://repo/compare/v1.1.0...HEAD" in out
    assert "[1.1.0]: https://repo/compare/v1.0.0...v1.1.0" in out


# ---------------------------------------------------------------------------
#  get_latest_version
# ---------------------------------------------------------------------------


def test_get_latest_version_valid(tmp_path):
    """Test extracting version from a well-formed changelog."""
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text(
        "# Changelog\n\n## [Unreleased]\n\n## [2.1.0] — 2026-04-01\n- Feature\n\n## [2.0.0] — 2026-03-01\n",
        encoding="utf-8",
    )
    assert get_latest_version(str(cl)) == "2.1.0"


def test_get_latest_version_missing_file(tmp_path):
    """Test exit when changelog file is missing."""
    with pytest.raises(SystemExit):
        get_latest_version(str(tmp_path / "nonexistent.md"))


def test_get_latest_version_no_version_header(tmp_path):
    """Test exit when changelog has no semver headers."""
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("# Changelog\n\n## [Unreleased]\n- Stuff\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        get_latest_version(str(cl))


def test_extract_unreleased_content_with_subsections(tmp_path):
    """Test unreleased content with subsection headers (### Added, ### Fixed) is fully captured."""
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text(
        "## [Unreleased]\n\n"
        "### Added\n"
        "- New feature X\n\n"
        "### Fixed\n"
        "- Bug fix Y\n\n"
        "## [1.0.0] — 2026-04-01\n"
        "- Initial release\n",
        encoding="utf-8",
    )
    res = extract_unreleased_content(str(cl))
    assert "### Added" in res
    assert "- New feature X" in res
    assert "### Fixed" in res
    assert "- Bug fix Y" in res
    # Must NOT include content from the versioned section
    assert "Initial release" not in res
