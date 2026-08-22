from pathlib import Path
from typing import Any

import json
import streamlit as st

from rdflib import Graph, URIRef

from src.state import get_step_state_filename_fullpath

METHOD_ID = "method_1_syntactic_graph_traversal"

def load_json_template(template_path: Path) -> dict[str, Any]:
    """
    Load a JSON template from disk.
    """
    if not template_path.is_file():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    with template_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_config_value(method_config: dict[str, Any], field_name: str) -> Any:
    """
    Get the value of a configuration field from the method config.
    """
    return method_config["config"][field_name]["value"]


def expand_prefixed_name(value: str, namespaces: dict[str, str]) -> URIRef:
    """
    Expand a prefixed name such as 'sdr:CurrentWazuhAlert' into a URIRef.
    """
    prefix, local_name = value.split(":", 1)

    if prefix not in namespaces:
        raise ValueError(f"Namespace prefix not found: {prefix}")

    return URIRef(f"{namespaces[prefix]}{local_name}")


def bind_namespaces(graph: Graph, namespaces: dict[str, str]) -> None:
    """
    Bind configured namespaces to a graph.
    """
    for prefix, namespace_uri in namespaces.items():
        graph.bind(prefix, namespace_uri)


def get_ignored_predicates(
    method_config: dict[str, Any],
    namespaces: dict[str, str],
) -> set[URIRef]:
    """
    Build ignored predicate URIRefs from the method config.
    """
    ignored_predicate_names = get_config_value(
        method_config=method_config,
        field_name="ignored_predicates",
    )

    return {
        expand_prefixed_name(predicate_name, namespaces)
        for predicate_name in ignored_predicate_names
    }


def should_ignore_predicate(
    predicate: URIRef,
    ignored_predicates: set[URIRef],
) -> bool:
    """
    Check whether a predicate must be ignored.
    """
    return predicate in ignored_predicates


def add_node_closure(
    source_graph: Graph,
    target_graph: Graph,
    node: URIRef,
    include_outgoing_triples: bool,
    include_incoming_triples: bool,
    ignored_predicates: set[URIRef],
) -> None:
    """
    Add all direct triples associated with a selected node.
    """
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


def get_neighbor_nodes(
    source_graph: Graph,
    node: URIRef,
    include_outgoing_triples: bool,
    include_incoming_triples: bool,
    ignored_predicates: set[URIRef],
) -> set[URIRef]:
    """
    Get URIRef neighbor nodes connected to a node.
    """
    neighbor_nodes: set[URIRef] = set()

    if include_outgoing_triples:
        for _, predicate, object_value in source_graph.triples((node, None, None)):
            if should_ignore_predicate(predicate, ignored_predicates):
                continue

            if isinstance(object_value, URIRef):
                neighbor_nodes.add(object_value)

    if include_incoming_triples:
        for subject, predicate, _ in source_graph.triples((None, None, node)):
            if should_ignore_predicate(predicate, ignored_predicates):
                continue

            if isinstance(subject, URIRef):
                neighbor_nodes.add(subject)

    return neighbor_nodes


def build_syntactic_graph_traversal_subgraph(
    full_graph: Graph,
    method_config: dict[str, Any],
    namespaces: dict[str, str],
) -> Graph:
    """
    Build Method 1 subgraph from the full knowledge graph.

    Method 1 starts from a configured RDF resource and traverses graph
    connections up to max_depth. For each selected resource, it includes
    the node closure.
    """
    start_node_name = get_config_value(method_config, "start_node")
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

    ignored_predicates = get_ignored_predicates(
        method_config=method_config,
        namespaces=namespaces,
    )

    start_node = expand_prefixed_name(start_node_name, namespaces)

    subgraph = Graph()
    bind_namespaces(subgraph, namespaces)

    visited_nodes: set[URIRef] = set()
    frontier_nodes: set[URIRef] = {start_node}

    current_depth = 0

    while frontier_nodes and current_depth <= max_depth:
        next_frontier_nodes: set[URIRef] = set()

        for node in frontier_nodes:
            if node in visited_nodes:
                continue

            visited_nodes.add(node)

            if include_node_closure:
                add_node_closure(
                    source_graph=full_graph,
                    target_graph=subgraph,
                    node=node,
                    include_outgoing_triples=include_outgoing_triples,
                    include_incoming_triples=include_incoming_triples,
                    ignored_predicates=ignored_predicates,
                )

            neighbor_nodes = get_neighbor_nodes(
                source_graph=full_graph,
                node=node,
                include_outgoing_triples=include_outgoing_triples,
                include_incoming_triples=include_incoming_triples,
                ignored_predicates=ignored_predicates,
            )

            next_frontier_nodes.update(neighbor_nodes - visited_nodes)

        frontier_nodes = next_frontier_nodes
        current_depth += 1

    return subgraph


def create_syntactic_graph_traversal_subgraph(template_path: Path) -> bool:
    """
    Create Step 2.4 modular knowledge graph using Method 1.

    Input:
        Step 2.3 full knowledge graph.

    Output:
        Step 2.4 modular knowledge graph generated through syntactic graph traversal.

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

        subgraph = build_syntactic_graph_traversal_subgraph(
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
        st.error(f"Error creating Method 1 subgraph: {error}")
        return False