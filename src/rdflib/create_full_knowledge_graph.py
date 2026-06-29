from pathlib import Path

import streamlit as st

from rdflib import Graph

from src.state import get_step_state_filename_fullpath


def parse_rdf_file(file_path: Path) -> Graph:
    """
    Parse an RDF/OWL file into an rdflib graph.
    """
    graph = Graph()
    graph.parse(str(file_path))
    return graph


def merge_graphs(graphs: list[Graph]) -> Graph:
    """
    Merge multiple rdflib graphs into a single graph.
    """
    merged_graph = Graph()

    for graph in graphs:
        for triple in graph:
            merged_graph.add(triple)

    return merged_graph


def bind_project_namespaces(graph: Graph) -> None:
    """
    Bind project namespaces used by the Semantic Defense Reasoner.
    """
    graph.bind(
        "sdr",
        "http://example.org/semantic-defense-reasoner#",
    )

    graph.bind(
        "d3fend",
        "http://d3fend.mitre.org/ontologies/d3fend.owl#",
    )

    graph.bind(
        "rdf",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    )

    graph.bind(
        "rdfs",
        "http://www.w3.org/2000/01/rdf-schema#",
    )

    graph.bind(
        "owl",
        "http://www.w3.org/2002/07/owl#",
    )

    graph.bind(
        "xsd",
        "http://www.w3.org/2001/XMLSchema#",
    )


def create_full_knowledge_graph() -> bool:
    """
    Create the full knowledge graph by merging D3FEND TBox and the annotated alert ABox.

    Input:
        Step 2.1: D3FEND OWL file.
        Step 2.2: annotated alert RDF/OWL file.

    Output:
        Step 2.3: full knowledge graph OWL file in RDF/XML.

    Returns:
        True if the full knowledge graph file was created successfully; otherwise False.
    """

    d3fend_step_id = "2.1"
    annotated_alert_step_id = "2.2"
    output_step_id = "2.3"

    d3fend_file_path = Path(get_step_state_filename_fullpath(d3fend_step_id))
    annotated_alert_file_path = Path(
        get_step_state_filename_fullpath(annotated_alert_step_id)
    )
    output_file_path = Path(get_step_state_filename_fullpath(output_step_id))

    try:
        if not d3fend_file_path.is_file():
            st.error(f"D3FEND OWL file not found: {d3fend_file_path}")
            return False

        if not annotated_alert_file_path.is_file():
            st.error(f"Annotated alert RDF file not found: {annotated_alert_file_path}")
            return False

        d3fend_graph = parse_rdf_file(d3fend_file_path)
        annotated_alert_graph = parse_rdf_file(annotated_alert_file_path)

        full_graph = merge_graphs(
            graphs=[
                d3fend_graph,
                annotated_alert_graph,
            ]
        )

        bind_project_namespaces(full_graph)

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        full_graph.serialize(
            destination=str(output_file_path),
            format="xml",
        )

        return output_file_path.is_file()

    except Exception as error:
        st.error(f"Error creating full knowledge graph: {error}")
        return False