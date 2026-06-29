# stat_inspection_materialized_kb.py

from pathlib import Path
import json
import re

import streamlit as st
from rdflib import Graph, RDF, RDFS, OWL, Literal, URIRef

from src.state import get_step_state_filename_fullpath


TEMPLATE_PATH = Path("data/templates/materialized_kb_inspection_to_show.json")


def normalize_windows_path(file_path: str | Path) -> Path:
    """
    Normalize a file path that may incorrectly start with '/C:/' on Windows.
    """
    file_path_str = str(file_path)

    if re.match(r"^/[A-Za-z]:/", file_path_str):
        file_path_str = file_path_str[1:]

    return Path(file_path_str)


def load_json_template(template_path: Path) -> dict:
    """
    Load the inspection template JSON.
    """
    with open(template_path, "r", encoding="utf-8") as file:
        return json.load(file)


def short_uri(value) -> str:
    """
    Convert URIRef or Literal into a readable short string.
    """
    if isinstance(value, Literal):
        return str(value)

    value_str = str(value)

    if "#" in value_str:
        return value_str.split("#")[-1]

    return value_str.rstrip("/").split("/")[-1]


def get_graph_statistics(graph: Graph) -> dict:
    """
    Extract general KB statistics.
    """
    classes = set(graph.subjects(RDF.type, OWL.Class))
    individuals = set(graph.subjects(RDF.type, OWL.NamedIndividual))
    object_properties = set(graph.subjects(RDF.type, OWL.ObjectProperty))
    data_properties = set(graph.subjects(RDF.type, OWL.DatatypeProperty))
    annotation_properties = set(graph.subjects(RDF.type, OWL.AnnotationProperty))

    return {
        "classes_count": len(classes),
        "individuals_count": len(individuals),
        "object_properties_count": len(object_properties),
        "data_properties_count": len(data_properties),
        "annotation_properties_count": len(annotation_properties),
        "triples_count": len(graph),
    }


def get_materialization_delta(before_graph: Graph, after_graph: Graph) -> dict:
    """
    Compare Step 3.1 and Step 3.2 to identify new materialized triples.
    """
    before_triples = set(before_graph)
    after_triples = set(after_graph)

    new_triples = after_triples - before_triples

    new_type_assertions = []
    new_object_property_assertions = []
    new_data_property_assertions = []

    for subject, predicate, obj in new_triples:
        triple_item = {
            "subject": short_uri(subject),
            "predicate": short_uri(predicate),
            "object": short_uri(obj),
        }

        if predicate == RDF.type:
            new_type_assertions.append(triple_item)
        elif isinstance(obj, Literal):
            new_data_property_assertions.append(triple_item)
        else:
            new_object_property_assertions.append(triple_item)

    return {
        "new_triples_count": len(new_triples),
        "new_type_assertions": new_type_assertions,
        "new_object_property_assertions": new_object_property_assertions,
        "new_data_property_assertions": new_data_property_assertions,
    }


def find_alert_individuals(graph: Graph, template: dict) -> list[URIRef]:
    """
    Find alert-related individuals using template match terms.
    """
    selection = template["sections"]["alert_individuals"]["selection"]
    match_terms = selection.get("match_uri_contains", [])

    alert_individuals = set()

    for individual in graph.subjects(RDF.type, OWL.NamedIndividual):
        individual_str = str(individual).lower()

        if any(term.lower() in individual_str for term in match_terms):
            alert_individuals.add(individual)

    for subject in graph.subjects():
        subject_str = str(subject).lower()

        if any(term.lower() in subject_str for term in match_terms):
            alert_individuals.add(subject)

    return sorted(alert_individuals, key=lambda value: str(value))


def get_alert_individual_details(graph: Graph, template: dict) -> list[dict]:
    """
    Extract types, relations, and literals for alert-related individuals.
    """
    selection = template["sections"]["alert_individuals"]["selection"]

    include_types = selection["include_types"]["enabled"]
    include_outgoing = selection["include_outgoing_relations"]["enabled"]
    include_incoming = selection["include_incoming_relations"]["enabled"]
    include_data = selection["include_data_properties"]["enabled"]

    alert_individuals = find_alert_individuals(graph, template)

    results = []

    for individual in alert_individuals:
        item = {
            "individual": short_uri(individual),
            "uri": str(individual),
            "types": [],
            "outgoing_relations": [],
            "incoming_relations": [],
            "data_properties": [],
        }

        if include_types:
            for obj in graph.objects(individual, RDF.type):
                item["types"].append(short_uri(obj))

        if include_outgoing or include_data:
            for predicate, obj in graph.predicate_objects(individual):
                if predicate == RDF.type:
                    continue

                relation_item = {
                    "predicate": short_uri(predicate),
                    "object": short_uri(obj),
                }

                if isinstance(obj, Literal):
                    if include_data:
                        item["data_properties"].append(relation_item)
                else:
                    if include_outgoing:
                        item["outgoing_relations"].append(relation_item)

        if include_incoming:
            for subject, predicate in graph.subject_predicates(individual):
                item["incoming_relations"].append({
                    "subject": short_uri(subject),
                    "predicate": short_uri(predicate),
                })

        results.append(item)

    return results


def get_logical_axioms(graph: Graph) -> dict:
    """
    Extract a practical summary of logical axioms available in the KB.
    """
    return {
        "subclass_axioms": [
            {
                "class": short_uri(subject),
                "subclass_of": short_uri(obj),
            }
            for subject, obj in graph.subject_objects(RDFS.subClassOf)
        ],
        "equivalent_class_axioms": [
            {
                "class": short_uri(subject),
                "equivalent_to": short_uri(obj),
            }
            for subject, obj in graph.subject_objects(OWL.equivalentClass)
        ],
        "disjoint_class_axioms": [
            {
                "class": short_uri(subject),
                "disjoint_with": short_uri(obj),
            }
            for subject, obj in graph.subject_objects(OWL.disjointWith)
        ],
        "inverse_properties": [
            {
                "property": short_uri(subject),
                "inverse_of": short_uri(obj),
            }
            for subject, obj in graph.subject_objects(OWL.inverseOf)
        ],
        "transitive_properties": [
            short_uri(subject)
            for subject in graph.subjects(RDF.type, OWL.TransitiveProperty)
        ],
        "symmetric_properties": [
            short_uri(subject)
            for subject in graph.subjects(RDF.type, OWL.SymmetricProperty)
        ],
        "functional_properties": [
            short_uri(subject)
            for subject in graph.subjects(RDF.type, OWL.FunctionalProperty)
        ],
        "domain_axioms": [
            {
                "property": short_uri(subject),
                "domain": short_uri(obj),
            }
            for subject, obj in graph.subject_objects(RDFS.domain)
        ],
        "range_axioms": [
            {
                "property": short_uri(subject),
                "range": short_uri(obj),
            }
            for subject, obj in graph.subject_objects(RDFS.range)
        ],
        "existential_restrictions": [
            {
                "restriction": short_uri(subject),
                "some_values_from": short_uri(obj),
            }
            for subject, obj in graph.subject_objects(OWL.someValuesFrom)
        ],
        "universal_restrictions": [
            {
                "restriction": short_uri(subject),
                "all_values_from": short_uri(obj),
            }
            for subject, obj in graph.subject_objects(OWL.allValuesFrom)
        ],
        "cardinality_restrictions": [
            {
                "restriction": short_uri(subject),
                "predicate": short_uri(predicate),
                "value": short_uri(obj),
            }
            for predicate in [
                OWL.cardinality,
                OWL.minCardinality,
                OWL.maxCardinality,
                OWL.qualifiedCardinality,
                OWL.minQualifiedCardinality,
                OWL.maxQualifiedCardinality,
            ]
            for subject, obj in graph.subject_objects(predicate)
        ],
    }


def inspect_materialized_kb() -> dict | None:
    """
    Inspect the Step 3.2 materialized KB and compare it with Step 3.1.

    Input:
        Step 3.1 OWL file.
        Step 3.2 OWL file.
        materialized_kb_inspection_to_show.json template.

    Output:
        Dictionary with KB statistics, materialization delta,
        alert individual details, and logical axioms.

    Returns:
        dict if inspection succeeds.
        None otherwise.
    """

    before_kb_path = normalize_windows_path(
        get_step_state_filename_fullpath("3.1")
    ).resolve()

    after_kb_path = normalize_windows_path(
        get_step_state_filename_fullpath("3.2")
    ).resolve()

    template_path = TEMPLATE_PATH.resolve()

    try:
        if not before_kb_path.is_file():
            st.error(f"Step 3.1 file not found: {before_kb_path}")
            return None

        if not after_kb_path.is_file():
            st.error(f"Step 3.2 materialized KB file not found: {after_kb_path}")
            return None

        if not template_path.is_file():
            st.error(f"Inspection template not found: {template_path}")
            return None

        template = load_json_template(template_path)

        before_graph = Graph()
        after_graph = Graph()

        before_graph.parse(str(before_kb_path))
        after_graph.parse(str(after_kb_path))

        inspection_result = {
            "template_name": template.get("template_name"),
            "template_version": template.get("template_version"),
            "source_files": {
                "before_materialization": str(before_kb_path),
                "after_materialization": str(after_kb_path),
            },
            "kb_statistics": get_graph_statistics(after_graph),
            "materialization_delta": get_materialization_delta(
                before_graph=before_graph,
                after_graph=after_graph,
            ),
            "alert_individuals": get_alert_individual_details(
                graph=after_graph,
                template=template,
            ),
            "logical_axioms": get_logical_axioms(after_graph),
        }

        #st.success("Materialized KB inspection completed successfully.")

        return inspection_result

    except Exception as error:
        st.error(f"Error inspecting materialized KB: {error}")
        return None

def inspect_materialized_kb_enabled_only() -> dict | None:
    """
    Runs inspect_materialized_kb() and returns only the sections and fields
    enabled in materialized_kb_inspection_to_show.json.

    Returns:
        Filtered dict if inspection succeeds.
        None otherwise.
    """

    inspection_result = inspect_materialized_kb()

    if inspection_result is None:
        return None

    template_path = TEMPLATE_PATH.resolve()
    template = load_json_template(template_path)

    filtered_result = {
        "template_name": inspection_result.get("template_name"),
        "template_version": inspection_result.get("template_version"),
        "source_files": inspection_result.get("source_files"),
    }

    sections = template.get("sections", {})

    for section_key, section_config in sections.items():
        if not section_config.get("enabled", False):
            continue

        if section_key not in inspection_result:
            continue

        section_data = inspection_result[section_key]

        if section_key == "alert_individuals":
            filtered_result[section_key] = section_data
            continue

        enabled_fields = section_config.get("fields", {})

        if not isinstance(section_data, dict):
            filtered_result[section_key] = section_data
            continue

        filtered_result[section_key] = {}

        for field_key, field_config in enabled_fields.items():
            if not field_config.get("enabled", False):
                continue

            if field_key in section_data:
                filtered_result[section_key][field_key] = section_data[field_key]

    return filtered_result