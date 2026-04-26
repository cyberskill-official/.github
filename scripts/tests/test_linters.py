"""Tests for scripts/lib/linters.py — annotation helpers, validators, and health checks."""

import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.linters import (
    _escape_annotation_data,
    check_action_readmes,
    check_breaking_changes,
    check_community_health,
    check_integration_ids,
    check_readme_actions,
    get_required_input_names,
    gh_annotation,
    validate_changelog,
    validate_codeowners,
    validate_settings,
)

# ---------------------------------------------------------------------------
#  _escape_annotation_data
# ---------------------------------------------------------------------------


def test_escape_annotation_data_percent():
    assert _escape_annotation_data("100%") == "100%25"


def test_escape_annotation_data_newlines():
    assert _escape_annotation_data("line1\nline2\rline3") == "line1%0Aline2%0Dline3"


def test_escape_annotation_data_mixed():
    assert _escape_annotation_data("a%b\nc\rd") == "a%25b%0Ac%0Dd"


def test_escape_annotation_data_clean_string():
    assert _escape_annotation_data("no special chars") == "no special chars"


# ---------------------------------------------------------------------------
#  gh_annotation
# ---------------------------------------------------------------------------


def test_gh_annotation_error(capsys):
    gh_annotation("error", "something broke")
    captured = capsys.readouterr()
    assert captured.out.strip() == "::error::something broke"


def test_gh_annotation_warning(capsys):
    gh_annotation("warning", "be careful")
    captured = capsys.readouterr()
    assert captured.out.strip() == "::warning::be careful"


def test_gh_annotation_notice(capsys):
    gh_annotation("notice", "FYI")
    captured = capsys.readouterr()
    assert captured.out.strip() == "::notice::FYI"


def test_gh_annotation_invalid_level():
    with pytest.raises(ValueError, match="level must be one of"):
        gh_annotation("debug", "should fail")


def test_gh_annotation_escapes_message(capsys):
    gh_annotation("error", "line1\nline2")
    captured = capsys.readouterr()
    assert "%0A" in captured.out
    assert "\n" not in captured.out.split("::error::")[1].strip()


# ---------------------------------------------------------------------------
#  validate_codeowners
# ---------------------------------------------------------------------------


def test_validate_codeowners_valid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    co = tmp_path / "CODEOWNERS"
    co.write_text("* @org/core\ndocs/ @org/docs\n")
    assert validate_codeowners(str(co)) is True


def test_validate_codeowners_missing_owner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    co = tmp_path / "CODEOWNERS"
    co.write_text("docs/\n")  # Missing owner
    assert validate_codeowners(str(co)) is False


def test_validate_codeowners_invalid_owner_format(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    co = tmp_path / "CODEOWNERS"
    co.write_text("* badowner\n")  # No @ prefix
    assert validate_codeowners(str(co)) is False


def test_validate_codeowners_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert validate_codeowners(str(tmp_path / "nonexistent")) is False


def test_validate_codeowners_comments_and_blank_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    co = tmp_path / "CODEOWNERS"
    co.write_text("# Comment\n\n* @org/core\n# Another comment\n\n")
    assert validate_codeowners(str(co)) is True


# ---------------------------------------------------------------------------
#  validate_changelog
# ---------------------------------------------------------------------------


def test_validate_changelog_valid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text(
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.0.0] — 2026-01-01\n- Initial\n\n"
        "[Unreleased]: https://github.com/org/repo/compare/v1.0.0...HEAD\n"
        "[1.0.0]: https://github.com/org/repo/releases/tag/v1.0.0\n"
    )
    assert validate_changelog(str(cl)) is True


def test_validate_changelog_missing_unreleased(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("# Changelog\n\n## [1.0.0] — 2026-01-01\n- Initial\n")
    assert validate_changelog(str(cl)) is False


def test_validate_changelog_no_versions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("# Changelog\n\n## [Unreleased]\n- Something\n")
    assert validate_changelog(str(cl)) is False


def test_validate_changelog_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert validate_changelog(str(tmp_path / "nonexistent")) is False


# ---------------------------------------------------------------------------
#  validate_settings
# ---------------------------------------------------------------------------


def test_validate_settings_valid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sf = tmp_path / "settings.yml"
    sf.write_text(
        yaml.dump(
            {
                "rulesets": [
                    {
                        "name": "Test",
                        "enforcement": "active",
                        "bypass_actors": [{"actor_type": "OrganizationAdmin", "bypass_mode": "always"}],
                        "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
                    }
                ]
            }
        )
    )
    assert validate_settings(str(sf)) is True


def test_validate_settings_invalid_enforcement(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sf = tmp_path / "settings.yml"
    sf.write_text(
        yaml.dump({"rulesets": [{"name": "Bad", "enforcement": "invalid_value", "rules": [{"type": "deletion"}]}]})
    )
    assert validate_settings(str(sf)) is False


def test_validate_settings_invalid_actor_type(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sf = tmp_path / "settings.yml"
    sf.write_text(
        yaml.dump(
            {
                "rulesets": [
                    {
                        "name": "Bad",
                        "bypass_actors": [{"actor_type": "UnknownType", "bypass_mode": "always"}],
                        "rules": [{"type": "deletion"}],
                    }
                ]
            }
        )
    )
    assert validate_settings(str(sf)) is False


def test_validate_settings_invalid_rule_type(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sf = tmp_path / "settings.yml"
    sf.write_text(yaml.dump({"rulesets": [{"name": "Bad", "rules": [{"type": "made_up_type"}]}]}))
    assert validate_settings(str(sf)) is False


def test_validate_settings_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert validate_settings(str(tmp_path / "nonexistent")) is False


def test_validate_settings_missing_rulesets_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sf = tmp_path / "settings.yml"
    sf.write_text(yaml.dump({"other_key": "value"}))
    assert validate_settings(str(sf)) is False


def test_validate_settings_invalid_bypass_mode(tmp_path, monkeypatch):
    """Test invalid bypass_mode value is rejected."""
    monkeypatch.chdir(tmp_path)
    sf = tmp_path / "settings.yml"
    sf.write_text(
        yaml.dump(
            {
                "rulesets": [
                    {
                        "name": "Bad",
                        "bypass_actors": [{"actor_type": "OrganizationAdmin", "bypass_mode": "never"}],
                        "rules": [{"type": "deletion"}],
                    }
                ]
            }
        )
    )
    assert validate_settings(str(sf)) is False


# ---------------------------------------------------------------------------
#  check_community_health
# ---------------------------------------------------------------------------


def test_check_community_health_all_present(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    for f in ["CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "ARCHITECTURE.md"]:
        (docs / f).write_text(f"# {f}\n")
    assert check_community_health() is True


def test_check_community_health_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    for f in ["CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md"]:
        (docs / f).write_text(f"# {f}\n")
    # Missing ARCHITECTURE.md
    assert check_community_health() is False


# ---------------------------------------------------------------------------
#  get_required_input_names
# ---------------------------------------------------------------------------


def test_get_required_input_names_mixed():
    inputs = {
        "TOKEN": {"required": True, "description": "Auth"},
        "MODE": {"required": False, "description": "Mode"},
        "HOST": {"required": True, "description": "Host"},
    }
    result = get_required_input_names(inputs)
    assert result == ["HOST", "TOKEN"]


def test_get_required_input_names_none_required():
    inputs = {
        "A": {"required": False},
        "B": {"description": "Only desc"},
    }
    assert get_required_input_names(inputs) == []


def test_get_required_input_names_empty():
    assert get_required_input_names({}) == []


# ---------------------------------------------------------------------------
#  check_breaking_changes — edge cases
# ---------------------------------------------------------------------------


def test_breaking_changes_no_change(tmp_path):
    data = {"inputs": {"FOO": {"required": True}}, "outputs": {"bar": {"description": "bar"}}}
    base = tmp_path / "base.yml"
    pr = tmp_path / "pr.yml"
    base.write_text(yaml.dump(data))
    pr.write_text(yaml.dump(data))
    assert check_breaking_changes(str(base), str(pr)) is True


def test_breaking_changes_base_missing(tmp_path):
    """When base file doesn't exist (new action), no breaking change."""
    pr = tmp_path / "pr.yml"
    pr.write_text(yaml.dump({"inputs": {"NEW": {"required": True}}}))
    assert check_breaking_changes(str(tmp_path / "nonexistent.yml"), str(pr)) is True


def test_breaking_changes_pr_deleted(tmp_path):
    """When PR file doesn't exist (action deleted), that's breaking."""
    base = tmp_path / "base.yml"
    base.write_text(yaml.dump({"inputs": {"FOO": {"required": True}}}))
    assert check_breaking_changes(str(base), str(tmp_path / "nonexistent.yml")) is False


def test_breaking_changes_added_required_with_default(tmp_path):
    """Adding a new required input WITH a default is not breaking."""
    base = tmp_path / "base.yml"
    pr = tmp_path / "pr.yml"
    base.write_text(yaml.dump({"inputs": {"A": {"required": True}}}))
    pr.write_text(
        yaml.dump(
            {
                "inputs": {
                    "A": {"required": True},
                    "B": {"required": True, "default": "fallback"},
                }
            }
        )
    )
    assert check_breaking_changes(str(base), str(pr)) is True


def test_breaking_changes_added_required_without_default(tmp_path):
    """Adding a new required input WITHOUT a default is breaking."""
    base = tmp_path / "base.yml"
    pr = tmp_path / "pr.yml"
    base.write_text(yaml.dump({"inputs": {"A": {"required": True}}}))
    pr.write_text(yaml.dump({"inputs": {"A": {"required": True}, "B": {"required": True}}}))
    assert check_breaking_changes(str(base), str(pr)) is False


def test_breaking_changes_empty_inputs_and_outputs(tmp_path):
    """Actions with no inputs or outputs should pass."""
    base = tmp_path / "base.yml"
    pr = tmp_path / "pr.yml"
    base.write_text(yaml.dump({"name": "Test"}))
    pr.write_text(yaml.dump({"name": "Test"}))
    assert check_breaking_changes(str(base), str(pr)) is True


def test_breaking_changes_removed_output(tmp_path):
    """Removing an output is a breaking change."""
    base = tmp_path / "base.yml"
    pr = tmp_path / "pr.yml"
    base.write_text(
        yaml.dump(
            {
                "inputs": {"FOO": {"required": True}},
                "outputs": {"result": {"description": "The result"}, "status": {"description": "Status"}},
            }
        )
    )
    pr.write_text(
        yaml.dump(
            {
                "inputs": {"FOO": {"required": True}},
                "outputs": {"result": {"description": "The result"}},
            }
        )
    )
    assert check_breaking_changes(str(base), str(pr)) is False


# ---------------------------------------------------------------------------
#  check_readme_actions
# ---------------------------------------------------------------------------


def test_check_readme_actions_all_documented(tmp_path, monkeypatch):
    """All actions documented in README should pass."""
    monkeypatch.chdir(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("# Actions\n\n- build\n- test\n")
    os.makedirs("actions/build", exist_ok=True)
    os.makedirs("actions/test", exist_ok=True)
    assert check_readme_actions(str(docs / "README.md")) is True


def test_check_readme_actions_missing_action(tmp_path, monkeypatch):
    """Undocumented actions should cause failure."""
    monkeypatch.chdir(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("# Actions\n\n- build\n")
    os.makedirs("actions/build", exist_ok=True)
    os.makedirs("actions/deploy", exist_ok=True)
    assert check_readme_actions(str(docs / "README.md")) is False


# ---------------------------------------------------------------------------
#  check_action_readmes
# ---------------------------------------------------------------------------


def test_check_action_readmes_all_present(tmp_path, monkeypatch):
    """Actions with README.md should pass."""
    monkeypatch.chdir(tmp_path)
    action_dir = tmp_path / "actions" / "my-action"
    action_dir.mkdir(parents=True)
    (action_dir / "action.yml").write_text(yaml.dump({"name": "Test"}))
    (action_dir / "README.md").write_text("# Test\n")
    assert check_action_readmes() is True


def test_check_action_readmes_missing(tmp_path, monkeypatch):
    """Actions without README.md should fail."""
    monkeypatch.chdir(tmp_path)
    action_dir = tmp_path / "actions" / "my-action"
    action_dir.mkdir(parents=True)
    (action_dir / "action.yml").write_text(yaml.dump({"name": "Test"}))
    assert check_action_readmes() is False


# ---------------------------------------------------------------------------
#  check_integration_ids
# ---------------------------------------------------------------------------


def test_check_integration_ids_skips_when_no_token(tmp_path, monkeypatch):
    """check_integration_ids should return True and skip when GITHUB_TOKEN is not set."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert check_integration_ids(str(tmp_path / "settings.yml")) is True


def test_check_integration_ids_skips_on_http_403(tmp_path, monkeypatch):
    """check_integration_ids should gracefully skip on HTTP 403 (insufficient permissions)."""
    from unittest.mock import patch

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_testtoken1234567890abcdef1234567890")
    sf = tmp_path / "settings.yml"
    sf.write_text(
        yaml.dump(
            {
                "rulesets": [
                    {
                        "name": "Test",
                        "bypass_actors": [{"actor_type": "Integration", "actor_id": 12345}],
                        "rules": [{"type": "deletion"}],
                    }
                ]
            }
        )
    )
    import urllib.error

    with patch("lib.linters.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.github.com/orgs/test/installations",
            code=403,
            msg="Forbidden",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        # Should return True (graceful skip) on 403
        result = check_integration_ids(str(sf), org_name="test")
    assert result is True


def test_check_integration_ids_validates_installed_app(tmp_path, monkeypatch):
    """check_integration_ids should return True when all Integration app_ids are installed."""
    import json as json_mod
    from unittest.mock import MagicMock, patch

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_testtoken1234567890abcdef1234567890")
    sf = tmp_path / "settings.yml"
    sf.write_text(
        yaml.dump(
            {
                "rulesets": [
                    {
                        "name": "Test",
                        "bypass_actors": [{"actor_type": "Integration", "actor_id": 42}],
                        "rules": [{"type": "deletion"}],
                    }
                ]
            }
        )
    )
    api_response = json_mod.dumps({"installations": [{"app_id": 42}, {"app_id": 99}]}).encode()

    with patch("lib.linters.urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = api_response
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        result = check_integration_ids(str(sf), org_name="test")
    assert result is True


# ---------------------------------------------------------------------------
#  validate_changelog — warning-only path
# ---------------------------------------------------------------------------


def test_validate_changelog_missing_url_footer_is_warning_not_error(tmp_path, monkeypatch):
    """Changelog without [Unreleased] URL footer should pass (warning only, not error)."""
    monkeypatch.chdir(tmp_path)
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text(
        "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] — 2026-01-01\n- Initial\n"
        # Note: no [Unreleased]: URL footer
    )
    # Should return True because the missing footer is only a warning, not an error
    assert validate_changelog(str(cl)) is True


# ---------------------------------------------------------------------------
#  check_action_readmes — auto_fix path
# ---------------------------------------------------------------------------


def test_check_action_readmes_auto_fix_creates_missing_readme(tmp_path, monkeypatch):
    """auto_fix=True should create a placeholder README for actions missing one."""
    monkeypatch.chdir(tmp_path)
    action_dir = tmp_path / "actions" / "my-action"
    action_dir.mkdir(parents=True)
    (action_dir / "action.yml").write_text(yaml.dump({"name": "Test"}))
    # No README.md exists yet
    assert not (action_dir / "README.md").exists()

    result = check_action_readmes(auto_fix=True)
    assert result is True
    assert (action_dir / "README.md").exists()
    content = (action_dir / "README.md").read_text()
    assert "my-action" in content


# ---------------------------------------------------------------------------
#  check_readme_actions — auto_fix path
# ---------------------------------------------------------------------------


def test_check_readme_actions_auto_fix_calls_generate_all(tmp_path, monkeypatch):
    """auto_fix=True should call generate_all() when actions are missing from README."""
    from unittest.mock import patch

    monkeypatch.chdir(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("# Actions\n\n- build\n")
    os.makedirs("actions/build", exist_ok=True)
    os.makedirs("actions/deploy", exist_ok=True)  # undocumented

    with patch("lib.generators.generate_all", return_value=True) as mock_gen:
        result = check_readme_actions(str(docs / "README.md"), auto_fix=True)
    mock_gen.assert_called_once()
    assert result is True


def test_check_readme_actions_auto_fix_fails_when_generate_fails(tmp_path, monkeypatch):
    """auto_fix=True should fall through to error when generate_all() fails."""
    from unittest.mock import patch

    monkeypatch.chdir(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("# Actions\n\n- build\n")
    os.makedirs("actions/build", exist_ok=True)
    os.makedirs("actions/deploy", exist_ok=True)  # undocumented

    with patch("lib.generators.generate_all", return_value=False):
        result = check_readme_actions(str(docs / "README.md"), auto_fix=True)
    assert result is False


# ---------------------------------------------------------------------------
#  check_integration_ids — malformed JSON response
# ---------------------------------------------------------------------------


def test_check_integration_ids_handles_malformed_json(tmp_path, monkeypatch):
    """check_integration_ids should return False on malformed JSON from API."""
    from unittest.mock import MagicMock, patch

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_testtoken1234567890abcdef1234567890")
    sf = tmp_path / "settings.yml"
    sf.write_text(
        yaml.dump(
            {
                "rulesets": [
                    {
                        "name": "Test",
                        "bypass_actors": [{"actor_type": "Integration", "actor_id": 42}],
                        "rules": [{"type": "deletion"}],
                    }
                ]
            }
        )
    )

    with patch("lib.linters.urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json{{"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        result = check_integration_ids(str(sf), org_name="test")
    assert result is False
