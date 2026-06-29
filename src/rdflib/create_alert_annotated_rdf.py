from pathlib import Path
from typing import Any

import json
import streamlit as st

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from src.state import get_step_state_filename_fullpath
from src.rdflib.d3fend_annotation_lookup import load_ontology_graph, find_first_subject_by_literal_value


ANNOTATION_TEMPLATE_PATH = Path(
    "data/templates/unannotated_rdf_to_semantically_annotated_rdf.json"
)


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
    Expand a prefixed name such as 'sdr:hasMitreId' into a URIRef.
    """
    prefix, local_name = value.split(":", 1)

    if prefix not in namespaces:
        raise ValueError(f"Namespace prefix not found in template: {prefix}")

    return namespaces[prefix][local_name]


def create_annotated_rdf() -> bool:
    """
    Create an annotated RDF/OWL alert file.

    This step reads:
        - Step 1.2: unannotated alert RDF
        - Step 2.1: D3FEND OWL

    It searches the D3FEND ontology for resources annotated with the same
    MITRE ID found in the alert RDF, then links the alert to the real
    ontology resource.

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

        annotation_template = load_json_template(ANNOTATION_TEMPLATE_PATH)
        namespaces = build_namespaces(annotation_template)

        alert_graph = Graph()
        alert_graph.parse(str(input_alert_file_path), format="xml")

        bind_namespaces(alert_graph, namespaces)

        d3fend_graph = load_ontology_graph(input_d3fend_file_path)

        subject_uri = expand_prefixed_name(
            annotation_template["subject"]["uri"],
            namespaces,
        )

        for annotation in annotation_template.get("annotations", []):
            source_predicate = expand_prefixed_name(
                annotation["source_predicate"],
                namespaces,
            )

            target_predicate = expand_prefixed_name(
                annotation["target_predicate"],
                namespaces,
            )

            source_values = list(alert_graph.objects(subject_uri, source_predicate))

            for source_value in source_values:
                if is_empty_value(source_value):
                    continue

                mitre_id = str(source_value).strip()

                d3fend_resource_uri = find_first_subject_by_literal_value(
                    graph=d3fend_graph,
                    literal_value=mitre_id,
                )

                if d3fend_resource_uri is None:
                    st.warning(f"No D3FEND resource found for MITRE ID: {mitre_id}")
                    continue

                alert_graph.add(
                    (
                        subject_uri,
                        target_predicate,
                        d3fend_resource_uri,
                    )
                )

                alert_graph.add(
                    (
                        d3fend_resource_uri,
                        namespaces["sdr"]["hasOriginalMitreId"],
                        Literal(mitre_id),
                    )
                )

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        alert_graph.serialize(
            destination=str(output_file_path),
            format="xml",
        )

        return output_file_path.is_file()

    except Exception as error:
        st.error(f"Error creating annotated RDF: {error}")
        return False