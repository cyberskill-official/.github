"""Auto-generate Mermaid dependency graph and action documentation."""

from __future__ import annotations

import glob
import logging
import os

import yaml
from lib.linters import gh_annotation

log = logging.getLogger("cyberskill")


def generate_codebase_graph() -> bool:
    """Generate Mermaid dependency graph and update ARCHITECTURE.md."""
    mermaid = ["```mermaid", "graph TD"]
    mermaid.append("    subgraph Actions")
    actions = []
    for action_path in sorted(glob.glob("actions/*/action.yml")):
        dir_name = os.path.basename(os.path.dirname(action_path))
        actions.append(dir_name)
        mermaid.append(f'        {dir_name.replace("-", "")}["{dir_name}"]')
    mermaid.append("    end")

    mermaid.append("    subgraph Scripts")
    scripts = []
    for script_path in sorted(glob.glob("scripts/*.*")):
        if os.path.isfile(script_path):
            basename = os.path.basename(script_path)
            scripts.append(basename)
            mermaid.append(f'        {basename.replace("-", "").replace(".", "")}["{basename}"]')
    mermaid.append("    end")

    mermaid.append("    subgraph Config")
    configs = [
        "settings.yml",
        "renovate.json",
        ".yamllint",
        ".editorconfig",
        "CODEOWNERS",
    ]
    for config in configs:
        mermaid.append(f'        {config.replace("-", "").replace(".", "")}["{config}"]')
    mermaid.append("    end")

    mermaid.append("    subgraph CI")
    mermaid.append('        ci["ci.yml"]')
    mermaid.append("    end")

    mermaid.append("    %% Auto-detected dependencies")
    try:
        with open(".github/workflows/ci.yml", encoding="utf-8") as f:
            ci_content = f.read()
            for action in actions:
                uses_patterns = [
                    f"uses: cyberskill-official/.github/actions/{action}",
                    f"uses: ./.github/actions/{action}",
                    f"uses: ./actions/{action}",
                ]
                if any(p in ci_content for p in uses_patterns):
                    mermaid.append(f"    ci --> {action.replace('-', '')}")
            for script in scripts:
                if f"scripts/{script}" in ci_content:
                    mermaid.append(f"    ci --> {script.replace('-', '').replace('.', '')}")
            for config in configs:
                if config in ci_content:
                    mermaid.append(f"    ci --> {config.replace('-', '').replace('.', '')}")
    except FileNotFoundError:
        pass

    for action in actions:
        action_yml = f"actions/{action}/action.yml"
        if not os.path.exists(action_yml):
            continue
        with open(action_yml, encoding="utf-8") as f:
            content = f.read()
            for other_action in actions:
                if other_action == action:
                    continue
                uses_in_action = (
                    f"uses: cyberskill-official/.github/actions/{other_action}" in content
                    or f"uses: ./actions/{other_action}" in content
                )
                if uses_in_action:
                    mermaid.append(f"    {action.replace('-', '')} --> {other_action.replace('-', '')}")
            for script in scripts:
                if f"scripts/{script}" in content:
                    mermaid.append(f"    {action.replace('-', '')} --> {script.replace('-', '').replace('.', '')}")

    mermaid.append("```")

    codebase_md = "docs/ARCHITECTURE.md"
    if not os.path.exists(codebase_md):
        gh_annotation("error", f"File not found: {codebase_md}")
        return False

    with open(codebase_md, encoding="utf-8") as f:
        content = f.read()

    start_marker = "<!-- START MERMAID -->"
    end_marker = "<!-- END MERMAID -->"

    if start_marker in content and end_marker in content:
        before = content.split(start_marker)[0]
        after = content.split(end_marker)[1]
        new_content = before + start_marker + "\n" + "\n".join(mermaid) + "\n" + end_marker + after
        with open(codebase_md, "w", encoding="utf-8") as f:
            f.write(new_content)
        log.info("✅ Updated ARCHITECTURE.md with auto-generated Mermaid graph.")
        return True
    else:
        gh_annotation("warning", "Markers not found in ARCHITECTURE.md.")
        return False


def generate_action_docs(action_dir: str) -> bool:
    """Generate README.md for a single action from its action.yml."""
    action_yml_path = os.path.join(action_dir, "action.yml")
    readme_path = os.path.join(action_dir, "README.md")

    if not os.path.isfile(action_yml_path):
        gh_annotation("error", f"File not found: {action_yml_path}")
        return False

    with open(action_yml_path, encoding="utf-8") as f:
        action_data = yaml.safe_load(f)

    name = action_data.get("name", os.path.basename(os.path.abspath(action_dir)))
    description = action_data.get("description", "No description provided.")
    inputs = action_data.get("inputs", {})
    outputs = action_data.get("outputs", {})

    lines = []
    lines.append(f"# {name}")
    lines.append("")
    lines.append(description)
    lines.append("")

    # Escape pipe characters in table cell values to prevent Markdown table corruption
    def _esc_pipe(s: object) -> str:
        return str(s).replace("|", "\\|")

    if inputs:
        lines.append("## Inputs")
        lines.append("")
        lines.append("| Name | Description | Required | Default |")
        lines.append("| ---- | ----------- | -------- | ------- |")

        for in_name, in_meta in inputs.items():
            desc = _esc_pipe(str(in_meta.get("description", "")).replace("\\n", " "))
            req = str(in_meta.get("required", False)).lower()
            default = f"`{_esc_pipe(str(in_meta.get('default')))}`" if "default" in in_meta else "—"
            lines.append(f"| `{in_name}` | {desc} | `{req}` | {default} |")
        lines.append("")

    if outputs:
        lines.append("## Outputs")
        lines.append("")
        lines.append("| Name | Description |")
        lines.append("| ---- | ----------- |")
        for out_name, out_meta in outputs.items():
            desc = _esc_pipe(str(out_meta.get("description", "")).replace("\\n", " "))
            lines.append(f"| `{out_name}` | {desc} |")
        lines.append("")

    lines.append("## Usage")
    lines.append("")
    lines.append("```yaml")
    lines.append(f"uses: cyberskill-official/.github/actions/{os.path.basename(os.path.abspath(action_dir))}@main")
    if inputs:
        lines.append("with:")
        for in_name, in_meta in inputs.items():
            if str(in_meta.get("required", False)).lower() == "true":
                lines.append(f"  {in_name}: # required")
    lines.append("```")
    lines.append("")

    with open(readme_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    log.info("✅ Generated %s", readme_path)
    return True


def generate_all() -> bool:
    """Generate all docs: Mermaid graph + per-action READMEs."""
    res1 = generate_codebase_graph()
    success = res1
    for action_path in sorted(glob.glob("actions/*/action.yml")):
        dir_name = os.path.dirname(action_path)
        if not generate_action_docs(dir_name):
            success = False
    return success
