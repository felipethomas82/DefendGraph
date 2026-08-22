from pathlib import Path
from typing import Any

import json
import streamlit as st

from rdflib import Graph, Literal, Namespace, URIRef

from src.state import get_step_state_filename_fullpath
from src.rdflib.d3fend_annotation_lookup import load_ontology_graph


#ANNOTATION_TEMPLATE_PATH = Path("data/templates/unannotated_rdf_to_semantically_annotated_rdf.json")


def is_empty_value(value: Any) -> bool:
    """
    Check whether a value should be ignored.
    """
    if value is None:
        return True

    if isinstance(value, str) and value.strip() == "":
        return True

    return False


def load_json_template(template_path: Path) -> dict[str, Any]:
    """
    Load a JSON template from disk.
    """
    if not template_path.is_file():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    with template_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_namespaces(template: dict[str, Any]) -> dict[str, Namespace]:
    """
    Build rdflib namespaces from the template.
    """
    namespaces: dict[str, Namespace] = {}

    for prefix, uri in template.get("namespaces", {}).items():
        namespaces[prefix] = Namespace(uri)

    return namespaces


def bind_namespaces(graph: Graph, namespaces: dict[str, Namespace]) -> None:
    """
    Bind namespaces to the graph.
    """
    for prefix, namespace in namespaces.items():
        graph.bind(prefix, namespace)


def expand_prefixed_name(value: str, namespaces: dict[str, Namespace]) -> URIRef:
    """
    Expand a prefixed name such as 'sdr:hasDecoderName' into a URIRef.
    """
    if ":" not in value:
        raise ValueError(f"Expected a prefixed name, got: {value}")

    prefix, local_name = value.split(":", 1)

    if prefix not in namespaces:
        raise ValueError(f"Namespace prefix not found in template: {prefix}")

    return namespaces[prefix][local_name]


def normalize_literal_value(value: Any, case_sensitive: bool = True) -> str:
    """
    Normalize a literal value for comparison.
    """
    normalized_value = str(value).strip()

    if not case_sensitive:
        return normalized_value.lower()

    return normalized_value


def values_are_equal(
    left_value: Any,
    right_value: Any,
    case_sensitive: bool = True,
) -> bool:
    """
    Compare two RDF literal values according to the configured case sensitivity.
    """
    return normalize_literal_value(left_value, case_sensitive) == normalize_literal_value(
        right_value,
        case_sensitive,
    )


def condition_matches(
    graph: Graph,
    subject_uri: URIRef,
    condition: dict[str, Any],
    namespaces: dict[str, Namespace],
) -> bool:
    """
    Check whether an annotation condition matches the alert graph.
    """
    source_predicate = expand_prefixed_name(
        condition["source_predicate"],
        namespaces,
    )

    operator = condition.get("operator", "equals")
    expected_value = condition["value"]
    case_sensitive = condition.get("case_sensitive", True)

    source_values = list(graph.objects(subject_uri, source_predicate))

    if operator != "equals":
        raise ValueError(f"Unsupported annotation condition operator: {operator}")

    for source_value in source_values:
        if is_empty_value(source_value):
            continue

        if values_are_equal(
            left_value=source_value,
            right_value=expected_value,
            case_sensitive=case_sensitive,
        ):
            return True

    return False


def find_subjects_by_literal_label(
    graph: Graph,
    label_predicate: URIRef,
    label_value: str,
    case_sensitive: bool = True,
) -> list[URIRef]:
    """
    Find ontology resources whose configured label predicate matches label_value.
    """
    matching_subjects: list[URIRef] = []

    for subject, literal_value in graph.subject_objects(label_predicate):
        if not isinstance(subject, URIRef):
            continue

        if is_empty_value(literal_value):
            continue

        if values_are_equal(
            left_value=literal_value,
            right_value=label_value,
            case_sensitive=case_sensitive,
        ):
            matching_subjects.append(subject)

    return matching_subjects


def add_d3fend_resources_by_label(
    alert_graph: Graph,
    d3fend_graph: Graph,
    subject_uri: URIRef,
    target_predicate: URIRef,
    lookup_config: dict[str, Any],
    namespaces: dict[str, Namespace],
) -> int:
    """
    Add semantic links from the alert to D3FEND resources found by rdfs:label.
    """
    lookup_predicate = expand_prefixed_name(
        lookup_config.get("predicate", "rdfs:label"),
        namespaces,
    )

    label_values = lookup_config.get("values", [])
    case_sensitive = lookup_config.get("case_sensitive", True)
    allow_multiple_matches = lookup_config.get("allow_multiple_matches_per_value", True)

    added_triples_count = 0

    for label_value in label_values:
        if is_empty_value(label_value):
            continue

        d3fend_resource_uris = find_subjects_by_literal_label(
            graph=d3fend_graph,
            label_predicate=lookup_predicate,
            label_value=str(label_value).strip(),
            case_sensitive=case_sensitive,
        )

        if not d3fend_resource_uris:
            st.warning(f"No D3FEND resource found with rdfs:label: {label_value}")
            continue

        if not allow_multiple_matches:
            d3fend_resource_uris = d3fend_resource_uris[:1]

        for d3fend_resource_uri in d3fend_resource_uris:
            triple = (
                subject_uri,
                target_predicate,
                d3fend_resource_uri,
            )

            if triple not in alert_graph:
                alert_graph.add(triple)
                added_triples_count += 1

            alert_graph.add(
                (
                    d3fend_resource_uri,
                    namespaces["sdr"]["hasOriginalD3FENDLabel"],
                    Literal(str(label_value).strip()),
                )
            )

    return added_triples_count


def create_annotated_rdf(template_path: Path) -> bool:
    """
    Create an annotated RDF/OWL alert file.

    This step reads:
        - Step 1.2: unannotated alert RDF
        - Step 2.1: D3FEND OWL

    It checks configured alert predicates, such as sdr:hasDecoderName,
    and, when a condition matches, links the alert to D3FEND resources found
    by matching configured labels against rdfs:label in the D3FEND ontology.

    Output:
        - Step 2.2: semantically annotated RDF/OWL
    """

    input_alert_step_id = "1.2"
    input_d3fend_step_id = "2.1"
    output_step_id = "2.2"

    input_alert_file_path = Path(get_step_state_filename_fullpath(input_alert_step_id))
    input_d3fend_file_path = Path(get_step_state_filename_fullpath(input_d3fend_step_id))
    output_file_path = Path(get_step_state_filename_fullpath(output_step_id))

    try:
        if not input_alert_file_path.is_file():
            st.error(f"Input alert RDF file not found: {input_alert_file_path}")
            return False

        if not input_d3fend_file_path.is_file():
            st.error(f"D3FEND ontology file not found: {input_d3fend_file_path}")
            return False

        annotation_template = load_json_template(template_path)
        namespaces = build_namespaces(annotation_template)

        alert_graph = Graph()
        alert_graph.parse(str(input_alert_file_path), format="xml")

        bind_namespaces(alert_graph, namespaces)

        d3fend_graph = load_ontology_graph(input_d3fend_file_path)
        bind_namespaces(d3fend_graph, namespaces)

        subject_uri = expand_prefixed_name(
            annotation_template["subject"]["uri"],
            namespaces,
        )

        total_added_triples = 0

        for annotation in annotation_template.get("annotations", []):
            condition = annotation.get("condition")

            if condition is None:
                st.warning(
                    f"Skipping annotation without condition: {annotation.get('name')}"
                )
                continue

            if not condition_matches(
                graph=alert_graph,
                subject_uri=subject_uri,
                condition=condition,
                namespaces=namespaces,
            ):
                continue

            target_predicate = expand_prefixed_name(
                annotation["target_predicate"],
                namespaces,
            )

            total_added_triples += add_d3fend_resources_by_label(
                alert_graph=alert_graph,
                d3fend_graph=d3fend_graph,
                subject_uri=subject_uri,
                target_predicate=target_predicate,
                lookup_config=annotation.get("lookup", {}),
                namespaces=namespaces,
            )

        if total_added_triples == 0:
            st.warning("No semantic annotation triple was added to the alert RDF.")

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        alert_graph.serialize(
            destination=str(output_file_path),
            format="xml",
        )

        return output_file_path.is_file()

    except Exception as error:
        st.error(f"Error creating annotated RDF: {error}")
        return False
