import hashlib
import json
import re
from pathlib import Path
from typing import Any

from src.state import get_step_state_filename_fullpath


MAX_RELATED_ATTACK_TECHNIQUES = 8
MAX_DETECT_TECHNIQUES = 8
MAX_HARDEN_TECHNIQUES = 8


def generate_reasoning_path_mermaid_from_cq_results() -> bool:
    """
    Generate a Mermaid reasoning path from Stage 4.1 competency question results.

    Preferred input structure:
        - CQ6 as an edge list with:
            source, source_label, edge_label, target, target_label

    Fallback input structure:
        - CQ1: alert literals
        - CQ2: alert-related D3FEND artifacts
        - CQ3: related ATT&CK techniques
        - CQ4: D3FEND Detect recommendations
        - CQ5: D3FEND Harden recommendations

    Input:
        state/tag_4_1_competency_question_results.json

    Output:
        state/tag_4_3_reasoning_path_visualization.mmd
    """

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

    try:
        mermaid_text = build_reasoning_path_mermaid(cq_results)

        if not mermaid_text.strip():
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(mermaid_text, encoding="utf-8")

        return output_path.is_file()

    except Exception:
        return False


def build_reasoning_path_mermaid(cq_results: dict[str, Any]) -> str:
    """
    Build Mermaid text from CQ results.

    If CQ6 exists, it is treated as the authoritative explanatory path.
    Otherwise, the function builds an aggregated explanatory graph from CQ1-CQ5.
    """

    builder = MermaidGraphBuilder()

    cq6_rows = get_question_results(cq_results, "CQ6")

    if cq6_rows:
        build_from_cq6_edge_list(builder, cq6_rows)

        if builder.has_edges():
            return builder.render()

    build_from_existing_cqs(builder, cq_results)

    if not builder.has_edges():
        return ""

    return builder.render()


class MermaidGraphBuilder:
    """
    Small helper to avoid duplicated Mermaid nodes and edges.
    """

    def __init__(self) -> None:
        self.lines: list[str] = ["flowchart TD"]
        self.added_nodes: set[str] = set()
        self.added_edges: set[tuple[str, str, str]] = set()

    def add_node(self, value: Any, label: Any | None = None) -> str:
        node_id = clean_node_id(value)
        node_label = clean_mermaid_label(label if label is not None else value)

        if node_id not in self.added_nodes:
            self.added_nodes.add(node_id)
            self.lines.append(f'    {node_id}["{node_label}"]')

        return node_id

    def add_edge(
        self,
        source_value: Any,
        target_value: Any,
        source_label: Any | None = None,
        target_label: Any | None = None,
        edge_label: Any | None = None,
    ) -> None:
        source_id = self.add_node(source_value, source_label)
        target_id = self.add_node(target_value, target_label)

        normalized_edge_label = clean_mermaid_label(edge_label) if edge_label else ""
        edge_key = (source_id, target_id, normalized_edge_label)

        if edge_key in self.added_edges:
            return

        self.added_edges.add(edge_key)

        if normalized_edge_label:
            self.lines.append(
                f'    {source_id} -->|"{normalized_edge_label}"| {target_id}'
            )
        else:
            self.lines.append(f"    {source_id} --> {target_id}")

    def has_edges(self) -> bool:
        return len(self.added_edges) > 0

    def render(self) -> str:
        return "\n".join(self.lines) + "\n"


def build_from_cq6_edge_list(
    builder: MermaidGraphBuilder,
    cq6_rows: list[dict[str, Any]],
) -> None:
    """
    Build the graph from a CQ6 edge list.

    Expected CQ6 row fields:
        - source or source_node
        - source_label
        - edge_label or predicate_label or relation
        - target or target_node
        - target_label
    """

    for row in cq6_rows:
        source = get_first_available(row, ["source", "source_node", "from"])
        target = get_first_available(row, ["target", "target_node", "to"])

        if source is None or target is None:
            continue

        builder.add_edge(
            source_value=source,
            target_value=target,
            source_label=get_first_available(row, ["source_label", "from_label"]),
            target_label=get_first_available(row, ["target_label", "to_label"]),
            edge_label=get_first_available(
                row,
                ["edge_label", "predicate_label", "relation"],
            ),
        )


def build_from_existing_cqs(
    builder: MermaidGraphBuilder,
    cq_results: dict[str, Any],
) -> None:
    """
    Fallback graph builder for the current CQ1-CQ5 JSON structure.

    Important limitation:
        CQ4 and CQ5 currently return only final defensive techniques.
        They do not return the exact artifact/subproperty path.
        Therefore, this fallback builds an aggregated explanatory graph.
    """

    alert_node = "sdr:CurrentWazuhAlert"
    artifact_hub = "d3fend:DigitalArtifactObjects"

    facts = extract_alert_facts(cq_results)

    decoder = get_first_list_value(facts, "hasDecoderName")
    mitre_tactic = get_first_list_value(facts, "hasMitreTactic")
    mitre_technique = get_first_list_value(facts, "hasMitreTechnique")
    mitre_id = get_first_list_value(facts, "hasMitreId")

    builder.add_node(alert_node, "Wazuh Alert")

    if decoder:
        builder.add_edge(
            alert_node,
            f"decoder:{decoder}",
            "Wazuh Alert",
            f"Decoder: {decoder}",
            "has decoder",
        )

    if mitre_tactic:
        builder.add_edge(
            alert_node,
            f"mitre_tactic:{mitre_tactic}",
            "Wazuh Alert",
            f"ATT&CK tactic: {mitre_tactic}",
            "has MITRE tactic",
        )

    if mitre_tactic and mitre_technique:
        builder.add_edge(
            f"mitre_tactic:{mitre_tactic}",
            f"mitre_technique:{mitre_technique}",
            f"ATT&CK tactic: {mitre_tactic}",
            f"ATT&CK technique: {mitre_technique}",
            "contains",
        )

    if mitre_technique and mitre_id:
        builder.add_edge(
            f"mitre_technique:{mitre_technique}",
            f"mitre_id:{mitre_id}",
            f"ATT&CK technique: {mitre_technique}",
            f"MITRE ID: {mitre_id}",
            "identified as",
        )

    if decoder:
        builder.add_edge(
            f"decoder:{decoder}",
            artifact_hub,
            f"Decoder: {decoder}",
            "D3FEND digital artifacts",
            "semantic annotation",
        )
    else:
        builder.add_edge(
            alert_node,
            artifact_hub,
            "Wazuh Alert",
            "D3FEND digital artifacts",
            "semantic annotation",
        )

    add_d3fend_artifact_nodes(builder, cq_results, artifact_hub)
    add_related_attack_techniques(builder, cq_results, artifact_hub, mitre_id)
    add_detect_recommendations(builder, cq_results, artifact_hub)
    add_harden_recommendations(builder, cq_results, artifact_hub)


def add_d3fend_artifact_nodes(
    builder: MermaidGraphBuilder,
    cq_results: dict[str, Any],
    artifact_hub: str,
) -> None:
    for row in get_question_results(cq_results, "CQ2"):
        artifact = get_first_available(row, ["artifact"])

        if artifact is None:
            continue

        builder.add_edge(
            artifact_hub,
            artifact,
            "D3FEND digital artifacts",
            local_name(artifact),
            "has artifact",
        )


def add_related_attack_techniques(
    builder: MermaidGraphBuilder,
    cq_results: dict[str, Any],
    artifact_hub: str,
    mitre_id: Any | None,
) -> None:
    rows = get_question_results(cq_results, "CQ3")[:MAX_RELATED_ATTACK_TECHNIQUES]

    if not rows:
        return

    related_attack_hub = "d3fend:RelatedOffensiveTechniques"

    builder.add_edge(
        artifact_hub,
        related_attack_hub,
        "D3FEND digital artifacts",
        "Related ATT&CK techniques",
        "associated with",
    )

    parent_mitre_id = get_parent_mitre_id(mitre_id)

    for row in rows:
        technique_uri = get_first_available(row, ["main_technique"])
        technique_label = get_first_available(row, ["label"])

        if technique_uri is None:
            continue

        technique_id = local_name(technique_uri)
        node_label = build_mitre_node_label(technique_id, technique_label)

        if parent_mitre_id and technique_id == parent_mitre_id:
            builder.add_edge(
                f"mitre_id:{mitre_id}",
                technique_uri,
                f"MITRE ID: {mitre_id}",
                node_label,
                "main technique",
            )

        builder.add_edge(
            related_attack_hub,
            technique_uri,
            "Related ATT&CK techniques",
            node_label,
            "includes",
        )


def add_detect_recommendations(
    builder: MermaidGraphBuilder,
    cq_results: dict[str, Any],
    artifact_hub: str,
) -> None:
    rows = get_question_results(cq_results, "CQ4")[:MAX_DETECT_TECHNIQUES]

    if not rows:
        return

    detect_hub = "d3fend:Detect"

    builder.add_edge(
        artifact_hub,
        detect_hub,
        "D3FEND digital artifacts",
        "D3FEND Detect",
        "supports",
    )

    for row in rows:
        d3fend_id = get_first_available(row, ["d3fend_id"])
        label = get_first_available(row, ["label"])

        if d3fend_id is None:
            continue

        builder.add_edge(
            detect_hub,
            f"d3fend:{d3fend_id}",
            "D3FEND Detect",
            build_d3fend_node_label(d3fend_id, label),
            "recommends",
        )


def add_harden_recommendations(
    builder: MermaidGraphBuilder,
    cq_results: dict[str, Any],
    artifact_hub: str,
) -> None:
    rows = get_question_results(cq_results, "CQ5")[:MAX_HARDEN_TECHNIQUES]

    if not rows:
        return

    harden_hub = "d3fend:Harden"

    builder.add_edge(
        artifact_hub,
        harden_hub,
        "D3FEND digital artifacts",
        "D3FEND Harden",
        "supports",
    )

    for row in rows:
        d3fend_id = get_first_available(row, ["d3fend_id"])
        label = get_first_available(row, ["label"])

        if d3fend_id is None:
            continue

        builder.add_edge(
            harden_hub,
            f"d3fend:{d3fend_id}",
            "D3FEND Harden",
            build_d3fend_node_label(d3fend_id, label),
            "recommends",
        )


def extract_alert_facts(cq_results: dict[str, Any]) -> dict[str, list[Any]]:
    facts: dict[str, list[Any]] = {}

    for row in get_question_results(cq_results, "CQ1"):
        property_value = get_first_available(row, ["property"])
        literal_value = get_first_available(row, ["value"])

        if property_value is None or literal_value is None:
            continue

        property_name = local_name(property_value)
        facts.setdefault(property_name, []).append(literal_value)

    return facts


def get_question_results(cq_results: dict[str, Any], cq_id: str) -> list[dict[str, Any]]:
    questions = cq_results.get("questions", {})

    if not isinstance(questions, dict):
        return []

    question_data = questions.get(cq_id, {})

    if not isinstance(question_data, dict):
        return []

    rows = question_data.get("results", [])

    if not isinstance(rows, list):
        return []

    return [row for row in rows if isinstance(row, dict)]


def get_first_available(row: dict[str, Any], possible_keys: list[str]) -> Any:
    for key in possible_keys:
        value = row.get(key)

        if isinstance(value, dict) and "value" in value:
            value = value["value"]

        if value not in [None, "", [], {}]:
            return value

    return None


def get_first_list_value(values: dict[str, list[Any]], key: str) -> Any:
    items = values.get(key, [])

    if not items:
        return None

    return items[0]


def get_parent_mitre_id(mitre_id: Any | None) -> str | None:
    if mitre_id is None:
        return None

    text = str(mitre_id)

    if "." not in text:
        return text

    return text.split(".", 1)[0]


def build_mitre_node_label(technique_id: Any, label: Any | None) -> str:
    if label is None:
        return str(technique_id)

    if str(technique_id) in str(label):
        return str(label)

    return f"{technique_id}: {label}"


def build_d3fend_node_label(d3fend_id: Any, label: Any | None) -> str:
    if label is None:
        return str(d3fend_id)

    if str(d3fend_id) in str(label):
        return str(label)

    return f"{d3fend_id}: {label}"


def local_name(value: Any) -> str:
    text = str(value).strip()

    if "#" in text:
        return text.rsplit("#", 1)[-1]

    if "/" in text:
        return text.rstrip("/").rsplit("/", 1)[-1]

    return text


def clean_node_id(value: Any) -> str:
    original = str(value)
    base = local_name(value)

    cleaned = "".join(char if char.isalnum() else "_" for char in base)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")

    if not cleaned:
        cleaned = "Unknown"

    if cleaned[0].isdigit():
        cleaned = f"N_{cleaned}"

    digest = hashlib.md5(original.encode("utf-8")).hexdigest()[:8]

    return f"{cleaned}_{digest}"


def clean_mermaid_label(value: Any) -> str:
    text = local_name(value)
    text = text.replace("\\", "/")
    text = text.replace('"', "'")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()

    return text or "Unknown"
