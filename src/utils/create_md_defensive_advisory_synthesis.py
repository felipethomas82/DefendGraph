import json
from pathlib import Path
from typing import Any, Dict, List, Set

from src.state import get_step_state_filename_fullpath

def generate_md_file_defensive_advisory(template_path: Path) -> bool:
    """
    Generates the defensive advisory Markdown artifact.

    Input:
        state/tag_4_1_competency_question_results.json
        data/templates/defensive_advisory_template.json

    Output:
        state/tag_4_2_defensive_advisory.md

    Returns:
        True if the Markdown artifact was generated successfully.
        False otherwise.
    """

    input_step_id = "4.1"
    output_step_id = "4.2"
    cq_results_path = Path(get_step_state_filename_fullpath(input_step_id))
    output_path = Path(get_step_state_filename_fullpath(output_step_id))

    try:
        if not cq_results_path.exists():
            print(f"Competency question results file not found: {cq_results_path}")
            return False

        if not template_path.exists():
            print(f"Defensive advisory template file not found: {template_path}")
            return False

        cq_results = _load_json(cq_results_path)
        advisory_template = _load_json(template_path)

        markdown = _build_advisory_markdown(cq_results, advisory_template)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as file:
            file.write(markdown)

        return True

    except Exception as error:
        print(f"Error while generating defensive advisory: {error}")
        return False


def _load_json(file_path: Path) -> Dict[str, Any]:
    """
    Loads a JSON file as a dictionary.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _build_advisory_markdown(
    cq_results: Dict[str, Any],
    advisory_template: Dict[str, Any]
) -> str:
    """
    Builds the full Markdown advisory from the advisory template and CQ results.
    """

    lines: List[str] = []

    source_kb_file = cq_results.get("source_kb_file", "")

    lines.append("# Defensive Advisory")
    lines.append("")
    lines.append("This advisory was generated deterministically from competency question results over the materialized knowledge base.")
    lines.append("")

    if source_kb_file:
        lines.append(f"**Source Knowledge Base:** `{source_kb_file}`")
        lines.append("")

    sections = advisory_template.get("sections", {})

    for section_id, section_config in sections.items():
        if not section_config.get("enabled", False):
            continue

        section_lines = _build_section_markdown(section_id, section_config, cq_results)

        if section_lines:
            lines.extend(section_lines)
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def _build_section_markdown(
    section_id: str,
    section_config: Dict[str, Any],
    cq_results: Dict[str, Any]
) -> List[str]:
    """
    Builds one Markdown section according to the configured render_as strategy.
    """

    title = section_config.get("title", section_id)
    description = section_config.get("description", "")
    source_cq = section_config.get("source_cq", "")
    render_as = section_config.get("render_as", "")
    fields = section_config.get("fields", [])

    question_data = cq_results.get("questions", {}).get(source_cq, {})
    results = question_data.get("results", [])
    status = question_data.get("status", "missing")

    lines: List[str] = []

    lines.append(f"## {title}")
    lines.append("")

    if description:
        lines.append(description)
        lines.append("")

    if not question_data:
        lines.append(f"_No competency question result found for `{source_cq}`._")
        return lines

    if status == "error":
        error_message = question_data.get("error_message", "Unknown error.")
        lines.append(f"_Unable to generate this section because `{source_cq}` returned an error: {error_message}_")
        return lines

    if not results:
        lines.append(f"_No results were returned by `{source_cq}`._")
        return lines

    if render_as == "summary":
        lines.extend(_build_summary_markdown(results, fields))

    elif render_as == "table":
        lines.extend(_build_table_markdown(results, fields))

    elif render_as == "grouped_list":
        group_by = section_config.get("group_by", "")
        lines.extend(_build_grouped_list_markdown(results, fields, group_by))

    elif render_as == "path_list":
        lines.extend(_build_path_list_markdown(results, fields))

    elif render_as == "focus_list":
        lines.extend(_build_focus_list_markdown(results, fields))

    else:
        lines.append(f"_Unsupported render mode: `{render_as}`._")

    return lines


def _build_summary_markdown(
    results: List[Dict[str, Any]],
    fields: List[Dict[str, str]]
) -> List[str]:
    """
    Builds a key-value Markdown summary from CQ1-like results.
    """

    lines: List[str] = []
    property_value_map = _build_property_value_map(results)

    for field in fields:
        source = field.get("source", "")
        label = field.get("label", source)

        values = property_value_map.get(source, [])

        if not values:
            continue

        unique_values = _unique_preserve_order(values)

        if len(unique_values) == 1:
            lines.append(f"- **{label}:** {unique_values[0]}")
        else:
            lines.append(f"- **{label}:** {', '.join(unique_values)}")

    if not lines:
        lines.append("_No configured fields were found in the competency question results._")

    return lines


def _build_table_markdown(
    results: List[Dict[str, Any]],
    fields: List[Dict[str, str]]
) -> List[str]:
    """
    Builds a Markdown table.
    """

    headers = [field.get("label", field.get("source", "")) for field in fields]

    if not headers:
        return ["_No fields configured for this table._"]

    lines: List[str] = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    seen_rows: Set[str] = set()

    for row in results:
        rendered_values: List[str] = []

        for field in fields:
            value = _get_field_value(row, field)
            rendered_values.append(_format_cell_value(value))

        row_key = json.dumps(rendered_values, ensure_ascii=False)

        if row_key in seen_rows:
            continue

        seen_rows.add(row_key)
        lines.append("| " + " | ".join(rendered_values) + " |")

    return lines


def _build_grouped_list_markdown(
    results: List[Dict[str, Any]],
    fields: List[Dict[str, str]],
    group_by: str
) -> List[str]:
    """
    Builds a grouped Markdown list.
    """

    if not group_by:
        return ["_No group_by field configured for grouped list._"]

    grouped_items: Dict[str, List[str]] = {}

    for row in results:
        group_name = str(row.get(group_by, "")).strip() or "Unlabeled Group"

        for field in fields:
            value = _get_field_value(row, field)

            if value:
                grouped_items.setdefault(group_name, []).append(value)

    if not grouped_items:
        return ["_No grouped items could be generated._"]

    lines: List[str] = []

    for group_name in sorted(grouped_items.keys()):
        lines.append(f"### {group_name}")
        lines.append("")

        for item in _unique_preserve_order(grouped_items[group_name]):
            lines.append(f"- {item}")

        lines.append("")

    return lines


def _build_path_list_markdown(
    results: List[Dict[str, Any]],
    fields: List[Dict[str, str]]
) -> List[str]:
    """
    Builds a numbered list of semantic paths.
    """

    lines: List[str] = []
    seen_paths: Set[str] = set()
    path_index = 1

    for row in results:
        path_parts: List[str] = []

        for field in fields:
            value = _get_field_value(row, field)

            if field.get("source") == "relation":
                value = _local_name(value)

            if value:
                path_parts.append(value)

        if not path_parts:
            continue

        path_text = " → ".join(path_parts)

        if path_text in seen_paths:
            continue

        seen_paths.add(path_text)
        lines.append(f"{path_index}. {path_text}")
        path_index += 1

    if not lines:
        lines.append("_No explanatory paths could be generated._")

    return lines


def _build_focus_list_markdown(
    results: List[Dict[str, Any]],
    fields: List[Dict[str, str]]
) -> List[str]:
    """
    Builds a deduplicated defensive focus list.
    """

    focus_items: List[str] = []

    for row in results:
        for field in fields:
            value = _get_field_value(row, field)

            if value:
                focus_items.append(value)

    unique_focus_items = _unique_preserve_order(focus_items)

    if not unique_focus_items:
        return ["_No defensive focus items could be derived._"]

    lines: List[str] = []

    lines.append("Based on the semantic paths identified in the materialized knowledge base, defensive investigation should prioritize:")
    lines.append("")

    for item in unique_focus_items:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("These focus items are derived from D3FEND artifacts directly connected to the ATT&CK techniques associated with the alert.")

    return lines


def _build_property_value_map(results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Builds a map from local property name to all observed values.
    """

    property_value_map: Dict[str, List[str]] = {}

    for row in results:
        property_uri = str(row.get("property", ""))
        value = str(row.get("value", ""))

        if not property_uri or not value:
            continue

        property_name = _local_name(property_uri)
        property_value_map.setdefault(property_name, []).append(value)

    return property_value_map


def _get_field_value(row: Dict[str, Any], field: Dict[str, str]) -> str:
    """
    Retrieves a field value from a result row using optional fallback.
    """

    source = field.get("source", "")
    fallback = field.get("fallback", "")

    value = str(row.get(source, "")).strip()

    if not value and fallback:
        value = str(row.get(fallback, "")).strip()

    if value.startswith("http://") or value.startswith("https://"):
        return _local_name(value)

    return value


def _local_name(value: str) -> str:
    """
    Extracts local name from a URI-like value.
    """

    if not value:
        return ""

    if "#" in value:
        return value.rsplit("#", 1)[-1]

    if "/" in value:
        return value.rstrip("/").rsplit("/", 1)[-1]

    return value


def _format_cell_value(value: str) -> str:
    """
    Formats a value for safe use inside a Markdown table cell.
    """

    value = value.replace("\n", " ").replace("\r", " ").strip()
    value = value.replace("|", "\\|")

    return value


def _unique_preserve_order(values: List[str]) -> List[str]:
    """
    Removes duplicates while preserving order.
    """

    seen: Set[str] = set()
    unique_values: List[str] = []

    for value in values:
        value = str(value).strip()

        if not value:
            continue

        if value in seen:
            continue

        seen.add(value)
        unique_values.append(value)

    return unique_values