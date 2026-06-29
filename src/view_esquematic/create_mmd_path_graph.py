import json
from pathlib import Path
from typing import Any

from src.state import get_step_state_filename_fullpath

def generate_reasoning_path_mermaid_from_cq_results() -> bool:
    """
    Generate a semi-dynamic Mermaid reasoning path from Stage 4.1 CQ results.

    Input:
        state/tag_4_1_competency_question_results.json

    Output:
        state/tag_4_3_reasoning_path_visualization.mmd
    """

    #input_path = Path("state") / "tag_4_1_competency_question_results.json"
    #output_path = Path("state") / "tag_4_3_reasoning_path_graph.mmd"

    input_step_id = "4.1"
    output_step_id = "4.3"
    input_path = Path(get_step_state_filename_fullpath(input_step_id))
    output_path = Path(get_step_state_filename_fullpath(output_step_id))

    if not input_path.exists():
        return False

    try:
        cq_results = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    def clean_node_id(value: Any) -> str:
        text = str(value)
        cleaned = "".join(char if char.isalnum() else "_" for char in text)
        return cleaned.strip("_") or "Unknown"

    def clean_label(value: Any) -> str:
        return str(value).replace('"', "'").replace("\n", " ").strip()

    def collect_rows(data: Any) -> list[dict]:
        rows = []

        if isinstance(data, list):
            for item in data:
                rows.extend(collect_rows(item))

        elif isinstance(data, dict):
            if "results" in data and isinstance(data["results"], list):
                for item in data["results"]:
                    if isinstance(item, dict):
                        rows.append(item)

            elif "rows" in data and isinstance(data["rows"], list):
                for item in data["rows"]:
                    if isinstance(item, dict):
                        rows.append(item)

            elif "bindings" in data and isinstance(data["bindings"], list):
                for item in data["bindings"]:
                    if isinstance(item, dict):
                        rows.append(item)

            else:
                for value in data.values():
                    rows.extend(collect_rows(value))

        return rows

    def get_first_available(row: dict, possible_keys: list[str]) -> Any:
        for key in possible_keys:
            value = row.get(key)

            if isinstance(value, dict) and "value" in value:
                value = value["value"]

            if value not in [None, "", [], {}]:
                return value

        return None

    rows = collect_rows(cq_results)

    mermaid_lines = [
        "flowchart TD",
        '    Alert["Wazuh Alert"]',
    ]

    added_edges = set()

    def add_edge(source_id: str, source_label: str, target_id: str, target_label: str) -> None:
        edge = (source_id, target_id)

        if edge in added_edges:
            return

        added_edges.add(edge)
        mermaid_lines.append(
            f'    {source_id}["{source_label}"] --> {target_id}["{target_label}"]'
        )

    for row in rows:
        tactic = get_first_available(row, ["tactic", "attack_tactic", "mitre_tactic"])
        technique = get_first_available(row, ["technique", "attack_technique", "mitre_technique"])
        subtechnique = get_first_available(row, ["subtechnique", "attack_subtechnique", "mitre_subtechnique"])
        d3fend_artifact = get_first_available(row, ["d3fend_artifact", "defensive_artifact", "artifact"])
        defensive_action = get_first_available(row, ["defensive_action", "recommended_action", "action"])

        path_values = [
            tactic,
            technique,
            subtechnique,
            d3fend_artifact,
            defensive_action,
        ]

        path_values = [value for value in path_values if value not in [None, "", [], {}]]

        if not path_values:
            continue

        previous_id = "Alert"
        previous_label = "Wazuh Alert"

        for value in path_values:
            node_id = clean_node_id(value)
            node_label = clean_label(value)

            add_edge(previous_id, previous_label, node_id, node_label)

            previous_id = node_id
            previous_label = node_label

    if len(mermaid_lines) <= 2:
        return False

    try:
        output_path.write_text("\n".join(mermaid_lines) + "\n", encoding="utf-8")
        return True
    except Exception:
        return False