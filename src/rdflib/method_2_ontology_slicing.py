from pathlib import Path
from typing import Any

import json
import streamlit as st

from rdflib import Graph, URIRef

from src.state import get_step_state_filename_fullpath

METHOD_ID = "method_2_ontology_slicing"


def load_json_template(template_path: Path) -> dict[str, Any]:
    if not template_path.is_file():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    with template_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_config_value(method_config: dict[str, Any], field_name: str) -> Any:
    return method_config["config"][field_name]["value"]


def expand_prefixed_name(value: str, namespaces: dict[str, str]) -> URIRef:
    prefix, local_name = value.split(":", 1)

    if prefix not in namespaces:
        raise ValueError(f"Namespace prefix not found: {prefix}")

    return URIRef(f"{namespaces[prefix]}{local_name}")


def bind_namespaces(graph: Graph, namespaces: dict[str, str]) -> None:
    for prefix, namespace_uri in namespaces.items():
        graph.bind(prefix, namespace_uri)


def get_ignored_predicates(
    method_config: dict[str, Any],
    namespaces: dict[str, str],
) -> set[URIRef]:
    ignored_predicate_names = get_config_value(
        method_config,
        "ignored_predicates",
    )

    return {
        expand_prefixed_name(predicate_name, namespaces)
        for predicate_name in ignored_predicate_names
    }


def get_class_hierarchy_predicates(
    method_config: dict[str, Any],
    namespaces: dict[str, str],
) -> set[URIRef]:
    predicate_names = get_config_value(
        method_config,
        "class_hierarchy_predicates",
    )

    return {
        expand_prefixed_name(predicate_name, namespaces)
        for predicate_name in predicate_names
    }


def should_ignore_predicate(
    predicate: URIRef,
    ignored_predicates: set[URIRef],
) -> bool:
    return predicate in ignored_predicates


def add_direct_triples(
    source_graph: Graph,
    target_graph: Graph,
    node: URIRef,
    include_outgoing_triples: bool,
    include_incoming_triples: bool,
    ignored_predicates: set[URIRef],
) -> None:
    if include_outgoing_triples:
        for subject, predicate, object_value in source_graph.triples((node, None, None)):
            if should_ignore_predicate(predicate, ignored_predicates):
                continue

            target_graph.add((subject, predicate, object_value))

    if include_incoming_triples:
        for subject, predicate, object_value in source_graph.triples((None, None, node)):
            if should_ignore_predicate(predicate, ignored_predicates):
                continue

            target_graph.add((subject, predicate, object_value))


def get_uri_neighbors(
    source_graph: Graph,
    node: URIRef,
    include_outgoing_triples: bool,
    include_incoming_triples: bool,
    ignored_predicates: set[URIRef],
) -> set[URIRef]:
    neighbors: set[URIRef] = set()

    if include_outgoing_triples:
        for _, predicate, object_value in source_graph.triples((node, None, None)):
            if should_ignore_predicate(predicate, ignored_predicates):
                continue

            if isinstance(object_value, URIRef):
                neighbors.add(object_value)

    if include_incoming_triples:
        for subject, predicate, _ in source_graph.triples((None, None, node)):
            if should_ignore_predicate(predicate, ignored_predicates):
                continue

            if isinstance(subject, URIRef):
                neighbors.add(subject)

    return neighbors


def get_alert_signature_resources(
    source_graph: Graph,
    method_config: dict[str, Any],
    namespaces: dict[str, str],
) -> set[URIRef]:
    alert_node = expand_prefixed_name(
        get_config_value(method_config, "alert_node"),
        namespaces,
    )

    signature_predicate = expand_prefixed_name(
        get_config_value(method_config, "signature_predicate"),
        namespaces,
    )

    signature_resources: set[URIRef] = set()

    if bool(get_config_value(method_config, "include_alert_node")):
        signature_resources.add(alert_node)

    if bool(get_config_value(method_config, "include_signature_resources")):
        for object_value in source_graph.objects(alert_node, signature_predicate):
            if isinstance(object_value, URIRef):
                signature_resources.add(object_value)

    return signature_resources


def add_class_hierarchy_context(
    source_graph: Graph,
    target_graph: Graph,
    seed_nodes: set[URIRef],
    hierarchy_predicates: set[URIRef],
    ignored_predicates: set[URIRef],
) -> set[URIRef]:
    """
    Add hierarchy/class-definition triples connected to seed nodes.

    Returns:
        Additional URIRef nodes found through hierarchy predicates.
    """
    discovered_nodes: set[URIRef] = set()

    for node in seed_nodes:
        for subject, predicate, object_value in source_graph.triples((node, None, None)):
            if predicate not in hierarchy_predicates:
                continue

            if should_ignore_predicate(predicate, ignored_predicates):
                continue

            target_graph.add((subject, predicate, object_value))

            if isinstance(object_value, URIRef):
                discovered_nodes.add(object_value)

        for subject, predicate, object_value in source_graph.triples((None, None, node)):
            if predicate not in hierarchy_predicates:
                continue

            if should_ignore_predicate(predicate, ignored_predicates):
                continue

            target_graph.add((subject, predicate, object_value))

            if isinstance(subject, URIRef):
                discovered_nodes.add(subject)

    return discovered_nodes


def expand_from_signature(
    source_graph: Graph,
    target_graph: Graph,
    signature_nodes: set[URIRef],
    method_config: dict[str, Any],
    ignored_predicates: set[URIRef],
) -> set[URIRef]:
    max_depth = int(get_config_value(method_config, "max_depth"))

    include_outgoing_triples = bool(
        get_config_value(method_config, "include_outgoing_triples")
    )
    include_incoming_triples = bool(
        get_config_value(method_config, "include_incoming_triples")
    )
    include_node_closure = bool(
        get_config_value(method_config, "include_node_closure")
    )

    visited_nodes: set[URIRef] = set()
    frontier_nodes: set[URIRef] = set(signature_nodes)

    current_depth = 0

    while frontier_nodes and current_depth <= max_depth:
        next_frontier_nodes: set[URIRef] = set()

        for node in frontier_nodes:
            if node in visited_nodes:
                continue

            visited_nodes.add(node)

            if include_node_closure:
                add_direct_triples(
                    source_graph=source_graph,
                    target_graph=target_graph,
                    node=node,
                    include_outgoing_triples=include_outgoing_triples,
                    include_incoming_triples=include_incoming_triples,
                    ignored_predicates=ignored_predicates,
                )

            neighbors = get_uri_neighbors(
                source_graph=source_graph,
                node=node,
                include_outgoing_triples=include_outgoing_triples,
                include_incoming_triples=include_incoming_triples,
                ignored_predicates=ignored_predicates,
            )

            next_frontier_nodes.update(neighbors - visited_nodes)

        frontier_nodes = next_frontier_nodes
        current_depth += 1

    return visited_nodes


def build_ontology_slicing_subgraph(
    full_graph: Graph,
    method_config: dict[str, Any],
    namespaces: dict[str, str],
) -> Graph:
    subgraph = Graph()
    bind_namespaces(subgraph, namespaces)

    ignored_predicates = get_ignored_predicates(
        method_config=method_config,
        namespaces=namespaces,
    )

    signature_nodes = get_alert_signature_resources(
        source_graph=full_graph,
        method_config=method_config,
        namespaces=namespaces,
    )

    visited_nodes = expand_from_signature(
        source_graph=full_graph,
        target_graph=subgraph,
        signature_nodes=signature_nodes,
        method_config=method_config,
        ignored_predicates=ignored_predicates,
    )

    if bool(get_config_value(method_config, "include_class_hierarchy")):
        hierarchy_predicates = get_class_hierarchy_predicates(
            method_config=method_config,
            namespaces=namespaces,
        )

        hierarchy_nodes = add_class_hierarchy_context(
            source_graph=full_graph,
            target_graph=subgraph,
            seed_nodes=visited_nodes,
            hierarchy_predicates=hierarchy_predicates,
            ignored_predicates=ignored_predicates,
        )

        for hierarchy_node in hierarchy_nodes:
            add_direct_triples(
                source_graph=full_graph,
                target_graph=subgraph,
                node=hierarchy_node,
                include_outgoing_triples=True,
                include_incoming_triples=False,
                ignored_predicates=ignored_predicates,
            )

    return subgraph


def create_ontology_slicing_subgraph(template_path: Path) -> bool:
    """
    Create Step 2.4 modular knowledge graph using Method 2.

    Input:
        Step 2.3 full knowledge graph.

    Output:
        Step 2.4 modular knowledge graph generated through ontology slicing.

    Returns:
        True if the output file was created successfully; otherwise False.
    """
    input_step_id = "2.3"
    output_step_id = "2.4"

    input_file_path = Path(get_step_state_filename_fullpath(input_step_id))
    output_file_path = Path(get_step_state_filename_fullpath(output_step_id))

    try:
        if not input_file_path.is_file():
            st.error(f"Full knowledge graph file not found: {input_file_path}")
            return False

        template = load_json_template(template_path)
        namespaces = template.get("namespaces", {})
        methods = template.get("methods", {})

        if METHOD_ID not in methods:
            st.error(f"Method not found in template: {METHOD_ID}")
            return False

        method_config = methods[METHOD_ID]

        full_graph = Graph()
        full_graph.parse(str(input_file_path))

        subgraph = build_ontology_slicing_subgraph(
            full_graph=full_graph,
            method_config=method_config,
            namespaces=namespaces,
        )

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        subgraph.serialize(
            destination=str(output_file_path),
            format="xml",
        )

        return output_file_path.is_file()

    except Exception as error:
        st.error(f"Error creating Method 2 ontology slicing subgraph: {error}")
        return False