from pathlib import Path
from typing import Any

import json
import streamlit as st

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

from src.state import get_step_state_filename_fullpath, load_json_from_file


RDF_TEMPLATE_PATH = Path("data/templates/parsed_fields_to_unannotated_rdf.json")


def is_empty_value(value: Any) -> bool:
    """
    Check whether a value should be ignored when creating RDF triples.
    """
    if value is None:
        return True

    if isinstance(value, str) and value.strip() == "":
        return True

    if isinstance(value, list) and len(value) == 0:
        return True

    return False


def expand_prefixed_name(value: str, namespaces: dict[str, Namespace]) -> URIRef:
    """
    Expand a prefixed name such as 'sdr:hasAlertId' into a URIRef.
    """
    prefix, local_name = value.split(":", 1)

    if prefix not in namespaces:
        raise ValueError(f"Namespace prefix not found in template: {prefix}")

    return namespaces[prefix][local_name]


def get_xsd_datatype(datatype_name: str | None) -> URIRef | None:
    """
    Convert a datatype string from the template into an XSD URIRef.
    """
    if datatype_name is None:
        return None

    datatype_map = {
        "xsd:string": XSD.string,
        "xsd:integer": XSD.integer,
        "xsd:boolean": XSD.boolean,
        "xsd:dateTime": XSD.dateTime,
    }

    return datatype_map.get(datatype_name)


def add_literal(
    graph: Graph,
    subject: URIRef,
    predicate: URIRef,
    value: Any,
    datatype: URIRef | None = None,
) -> None:
    """
    Add a literal triple only when the value is not empty.
    """
    if is_empty_value(value):
        return

    graph.add((subject, predicate, Literal(value, datatype=datatype)))


def load_rdf_template(template_path: Path = RDF_TEMPLATE_PATH) -> dict[str, Any]:
    """
    Load the RDF mapping template from disk.
    """
    if not template_path.is_file():
        raise FileNotFoundError(f"RDF template not found: {template_path}")

    with template_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_namespaces(template: dict[str, Any]) -> dict[str, Namespace]:
    """
    Build rdflib Namespace objects from the template namespace section.
    """
    namespace_config = template.get("namespaces", {})
    namespaces: dict[str, Namespace] = {}

    for prefix, uri in namespace_config.items():
        namespaces[prefix] = Namespace(uri)

    return namespaces


def add_template_namespaces_to_graph(
    graph: Graph,
    namespaces: dict[str, Namespace],
) -> None:
    """
    Bind template namespaces to the RDF graph.
    """
    for prefix, namespace in namespaces.items():
        graph.bind(prefix, namespace)


def add_subject_type_from_template(
    graph: Graph,
    template: dict[str, Any],
    namespaces: dict[str, Namespace],
) -> URIRef:
    """
    Create the subject URI and add its rdf:type triple.
    """
    subject_config = template.get("subject", {})

    subject_uri = expand_prefixed_name(subject_config["uri"], namespaces)
    rdf_type_uri = expand_prefixed_name(subject_config["rdf_type"], namespaces)

    graph.add((subject_uri, RDF.type, rdf_type_uri))

    return subject_uri


def add_parsed_fields_to_graph(
    graph: Graph,
    subject_uri: URIRef,
    parsed_alert: dict[str, Any],
    template: dict[str, Any],
    namespaces: dict[str, Namespace],
) -> None:
    """
    Add RDF triples according to the RDF mapping template.
    """
    fields = template.get("fields", {})

    for field_name, field_config in fields.items():
        value = parsed_alert.get(field_name)

        if is_empty_value(value):
            continue

        predicate = expand_prefixed_name(field_config["predicate"], namespaces)
        datatype = get_xsd_datatype(field_config.get("datatype"))
        is_list = field_config.get("is_list", False)

        if is_list:
            if not isinstance(value, list):
                value = [value]

            for item in value:
                add_literal(
                    graph=graph,
                    subject=subject_uri,
                    predicate=predicate,
                    value=item,
                    datatype=datatype,
                )
        else:
            add_literal(
                graph=graph,
                subject=subject_uri,
                predicate=predicate,
                value=value,
                datatype=datatype,
            )


def convert_parsed_alert_to_rdf() -> bool:
    """
    Convert the saved parsed alert JSON to an RDF/XML file using an RDF mapping template.

    Input:
        Parsed alert JSON from step 1.1.
        RDF mapping template from data/templates/parsed_fields_to_unannotated_rdf.json.

    Output:
        RDF/XML file for step 1.2.

    Returns:
        True if the RDF/XML file was created successfully; otherwise False.
    """

    input_step_id = "1.1"
    output_step_id = "1.2"

    input_file_path = Path(get_step_state_filename_fullpath(input_step_id))
    output_file_path = Path(get_step_state_filename_fullpath(output_step_id))

    try:
        if not input_file_path.is_file():
            st.error(f"Input JSON file not found: {input_file_path}")
            return False

        parsed_alert = load_json_from_file(input_file_path)

        if not parsed_alert:
            st.error("Parsed alert JSON is empty or could not be loaded.")
            return False

        rdf_template = load_rdf_template()
        namespaces = build_namespaces(rdf_template)

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        graph = Graph()

        add_template_namespaces_to_graph(graph, namespaces)

        subject_uri = add_subject_type_from_template(
            graph=graph,
            template=rdf_template,
            namespaces=namespaces,
        )

        add_parsed_fields_to_graph(
            graph=graph,
            subject_uri=subject_uri,
            parsed_alert=parsed_alert,
            template=rdf_template,
            namespaces=namespaces,
        )

        graph.serialize(
            destination=str(output_file_path),
            format="xml",
        )

        return output_file_path.is_file()

    except Exception as error:
        st.error(f"Error converting parsed alert to RDF/XML: {error}")
        return False