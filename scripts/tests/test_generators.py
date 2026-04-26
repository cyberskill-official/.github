"""Tests for scripts/lib/generators.py — Mermaid graph and action docs generation."""

import os
import sys
import textwrap

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.generators import generate_action_docs, generate_codebase_graph

# ---------------------------------------------------------------------------
#  generate_action_docs
# ---------------------------------------------------------------------------


def _make_action(tmp_path, content: dict) -> str:
    """Helper: create a temp action directory with an action.yml."""
    action_path = tmp_path / "test-action"
    action_path.mkdir(exist_ok=True)
    # Avoid Path.write_text(newline=) which requires Python 3.10+
    text = yaml.dump(content)
    (action_path / "action.yml").write_bytes(text.encode("utf-8"))
    return str(action_path)


def test_action_docs_generates_readme_with_inputs(tmp_path) -> None:
    """Verify README contains input table with correct required markers."""
    path = _make_action(
        tmp_path,
        {
            "name": "🧪 Test Action",
            "description": "A test action for unit testing.",
            "inputs": {
                "TOKEN": {"description": "Auth token", "required": True},
                "MODE": {"description": "Run mode", "required": False, "default": "fast"},
            },
        },
    )
    assert generate_action_docs(path) is True

    readme = os.path.join(path, "README.md")
    assert os.path.isfile(readme)
    with open(readme, encoding="utf-8") as f:
        content = f.read()

    assert "# 🧪 Test Action" in content
    assert "A test action for unit testing." in content
    assert "| `TOKEN` |" in content
    assert "| `true` |" in content
    assert "| `MODE` |" in content
    assert "`fast`" in content


def test_action_docs_generates_output_table(tmp_path) -> None:
    """Verify README contains output table."""
    path = _make_action(
        tmp_path,
        {
            "name": "Output Action",
            "description": "Has outputs.",
            "outputs": {"result": {"description": "The result value"}},
        },
    )
    assert generate_action_docs(path) is True

    with open(os.path.join(path, "README.md"), encoding="utf-8") as f:
        content = f.read()
    assert "## Outputs" in content
    assert "| `result` | The result value |" in content


def test_action_docs_usage_marks_required_inputs(tmp_path) -> None:
    """Verify usage YAML block marks required inputs."""
    path = _make_action(
        tmp_path,
        {
            "name": "Usage Test",
            "description": "Test usage.",
            "inputs": {
                "HOST": {"description": "Host", "required": True},
                "PORT": {"description": "Port", "required": False, "default": "22"},
            },
        },
    )
    assert generate_action_docs(path) is True

    with open(os.path.join(path, "README.md"), encoding="utf-8") as f:
        content = f.read()
    assert "## Usage" in content
    assert "HOST: # required" in content


def test_action_docs_returns_false_for_missing_yml(tmp_path) -> None:
    """Verify returns False for missing action.yml."""
    missing_dir = str(tmp_path / "nonexistent")
    os.makedirs(missing_dir, exist_ok=True)
    assert generate_action_docs(missing_dir) is False


def test_action_docs_no_inputs_no_outputs(tmp_path) -> None:
    """Verify README generated for action with only name/description."""
    path = _make_action(tmp_path, {"name": "Minimal", "description": "No inputs or outputs."})
    assert generate_action_docs(path) is True

    with open(os.path.join(path, "README.md"), encoding="utf-8") as f:
        content = f.read()
    assert "# Minimal" in content
    assert "## Inputs" not in content
    assert "## Outputs" not in content
    assert "## Usage" in content


# ---------------------------------------------------------------------------
#  generate_codebase_graph
# ---------------------------------------------------------------------------


def test_graph_returns_false_when_architecture_missing(tmp_path, monkeypatch) -> None:
    """Verify returns False when ARCHITECTURE.md doesn't exist."""
    monkeypatch.chdir(tmp_path)
    os.makedirs("actions/test-action", exist_ok=True)
    with open("actions/test-action/action.yml", "w") as f:
        yaml.dump({"name": "test"}, f)
    assert generate_codebase_graph() is False


def test_graph_returns_false_when_markers_missing(tmp_path, monkeypatch) -> None:
    """Verify returns False when ARCHITECTURE.md lacks Mermaid markers."""
    monkeypatch.chdir(tmp_path)
    os.makedirs("docs", exist_ok=True)
    with open("docs/ARCHITECTURE.md", "w") as f:
        f.write("# Architecture\n\nNo markers here.\n")
    os.makedirs("actions/test-action", exist_ok=True)
    with open("actions/test-action/action.yml", "w") as f:
        yaml.dump({"name": "test"}, f)
    assert generate_codebase_graph() is False


def test_graph_updates_mermaid_block(tmp_path, monkeypatch) -> None:
    """Verify Mermaid block is updated between markers."""
    monkeypatch.chdir(tmp_path)
    os.makedirs("docs", exist_ok=True)
    arch_content = textwrap.dedent("""\
        # Architecture

        <!-- START MERMAID -->
        old content
        <!-- END MERMAID -->

        ## Footer
    """)
    with open("docs/ARCHITECTURE.md", "w") as f:
        f.write(arch_content)

    os.makedirs("actions/my-action", exist_ok=True)
    with open("actions/my-action/action.yml", "w") as f:
        yaml.dump({"name": "My Action", "inputs": {"FOO": {"required": True}}}, f)

    assert generate_codebase_graph() is True

    with open("docs/ARCHITECTURE.md") as f:
        result = f.read()

    assert "```mermaid" in result
    assert "graph TD" in result
    assert 'myaction["my-action"]' in result
    assert "old content" not in result
    assert "## Footer" in result


# ---------------------------------------------------------------------------
#  generate_all
# ---------------------------------------------------------------------------


def test_generate_all_orchestrates_graph_and_docs(tmp_path, monkeypatch) -> None:
    """Verify generate_all() runs both graph generation and per-action docs."""
    monkeypatch.chdir(tmp_path)

    # Setup ARCHITECTURE.md with mermaid markers
    os.makedirs("docs", exist_ok=True)
    with open("docs/ARCHITECTURE.md", "w") as f:
        f.write("# Arch\n\n<!-- START MERMAID -->\nold\n<!-- END MERMAID -->\n")

    # Setup a single action
    os.makedirs("actions/demo-action", exist_ok=True)
    with open("actions/demo-action/action.yml", "w") as f:
        yaml.dump(
            {
                "name": "Demo",
                "description": "A demo action.",
                "inputs": {"TOKEN": {"description": "Auth", "required": True}},
            },
            f,
        )

    from lib.generators import generate_all

    assert generate_all() is True

    # Verify graph was updated
    with open("docs/ARCHITECTURE.md") as f:
        arch = f.read()
    assert "```mermaid" in arch
    assert "old" not in arch

    # Verify per-action README was generated
    readme = os.path.join("actions", "demo-action", "README.md")
    assert os.path.isfile(readme)
    with open(readme) as f:
        content = f.read()
    assert "# Demo" in content
    assert "TOKEN" in content


def test_action_docs_escapes_pipe_in_description(tmp_path) -> None:
    """Verify pipe characters in descriptions are escaped to prevent markdown table corruption."""
    path = _make_action(
        tmp_path,
        {
            "name": "Pipe Test",
            "description": "Test pipe escaping.",
            "inputs": {
                "MODE": {
                    "description": "Choose A | B | C",
                    "required": False,
                    "default": "A|B",
                },
            },
        },
    )
    assert generate_action_docs(path) is True

    with open(os.path.join(path, "README.md"), encoding="utf-8") as f:
        content = f.read()

    # Pipes in description must be escaped
    assert "Choose A \\| B \\| C" in content
    # Pipes in default value must be escaped
    assert "A\\|B" in content
    # The table row must not be broken by raw pipes
    mode_row = [line for line in content.splitlines() if "`MODE`" in line]
    assert len(mode_row) == 1
    # A valid table row for 4 columns has exactly 5 pipe delimiters at column boundaries
    assert mode_row[0].count("|") - mode_row[0].count("\\|") == 5


def test_action_docs_escapes_pipe_in_output_description(tmp_path) -> None:
    """Verify pipe characters in output descriptions are escaped to prevent markdown table corruption."""
    path = _make_action(
        tmp_path,
        {
            "name": "Output Pipe Test",
            "description": "Test output pipe escaping.",
            "outputs": {
                "result": {"description": "Choose X | Y | Z"},
            },
        },
    )
    assert generate_action_docs(path) is True

    with open(os.path.join(path, "README.md"), encoding="utf-8") as f:
        content = f.read()

    # Pipes in output description must be escaped
    assert "Choose X \\| Y \\| Z" in content
    # The output table row must not be broken by raw pipes
    result_row = [line for line in content.splitlines() if "`result`" in line]
    assert len(result_row) == 1
    # A valid output table row has exactly 3 pipe delimiters at column boundaries
    assert result_row[0].count("|") - result_row[0].count("\\|") == 3
