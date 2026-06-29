# used on Step 3.2 - OWL-RL Semantic Assertion Materialization

from pathlib import Path
import re

import streamlit as st
from rdflib import Graph, OWL, RDFS
from owlrl import DeductiveClosure, OWLRL_Semantics

from src.state import get_step_state_filename_fullpath


def normalize_windows_path(file_path: str | Path) -> Path:
    """
    Normalize a file path that may incorrectly start with '/C:/' on Windows.
    """
    file_path_str = str(file_path)

    if re.match(r"^/[A-Za-z]:/", file_path_str):
        file_path_str = file_path_str[1:]

    return Path(file_path_str)


def load_rdf_graph(input_file_path: str | Path) -> Graph:
    """
    Load an RDF/OWL file into an rdflib Graph.
    """
    normalized_path = normalize_windows_path(input_file_path).resolve()

    graph = Graph()
    graph.parse(str(normalized_path))

    return graph


def save_rdf_graph(
    graph: Graph,
    output_file_path: str | Path,
    rdf_format: str = "xml",
) -> None:
    """
    Save an rdflib Graph to disk.
    """
    normalized_path = normalize_windows_path(output_file_path).resolve()
    normalized_path.parent.mkdir(parents=True, exist_ok=True)

    graph.serialize(
        destination=str(normalized_path),
        format=rdf_format,
    )


def remove_reflexive_inference_noise(graph: Graph) -> int:
    """
    Remove reflexive inference triples that are logically valid but usually
    not useful for competency question resolution.

    Examples:
        :X owl:sameAs :X .
        :X owl:equivalentClass :X .
        :X rdfs:subClassOf :X .

    Returns:
        Number of removed triples.
    """
    predicates_to_clean = [
        OWL.sameAs,
        OWL.equivalentClass,
        RDFS.subClassOf,
    ]

    triples_to_remove = []

    for predicate in predicates_to_clean:
        for subject, _, obj in graph.triples((None, predicate, None)):
            if subject == obj:
                triples_to_remove.append((subject, predicate, obj))

    for triple in triples_to_remove:
        graph.remove(triple)

    return len(triples_to_remove)


def materialize_owlrl_assertions() -> bool:
    """
    Step 3.2 - OWL-RL Semantic Assertion Materialization.

    Input:
        Step 3.1 OWL file.

    Output:
        Step 3.2 materialized OWL file.

    Behavior:
        - Loads the DL-consistent KB generated in Step 3.1.
        - Applies OWL-RL deductive closure using owlrl.
        - Removes reflexive inference noise triples.
        - Saves the expanded/materialized graph as Step 3.2.
        - Reports triple counts before and after materialization.

    Returns:
        True if the materialized ontology was created successfully.
        False otherwise.
    """

    input_step_id = "3.1"
    output_step_id = "3.2"

    input_kb_path = normalize_windows_path(
        get_step_state_filename_fullpath(input_step_id)
    ).resolve()

    output_kb_path = normalize_windows_path(
        get_step_state_filename_fullpath(output_step_id)
    ).resolve()

    try:
        if not input_kb_path.is_file():
            st.error(f"Step 3.1 input file not found: {input_kb_path}")
            return False

        output_kb_path.parent.mkdir(parents=True, exist_ok=True)

        if output_kb_path.exists():
            output_kb_path.unlink()

        graph = load_rdf_graph(input_kb_path)

        triples_before = len(graph)

        DeductiveClosure(OWLRL_Semantics).expand(graph)

        triples_after_materialization = len(graph)
        new_triples = triples_after_materialization - triples_before

        removed_noise_triples = remove_reflexive_inference_noise(graph)

        triples_after_cleanup = len(graph)

        st.write(f"Triples before OWL-RL materialization: {triples_before}")
        st.write(
            f"Triples after OWL-RL materialization: "
            f"{triples_after_materialization}"
        )
        st.write(f"New inferred triples before cleanup: {new_triples}")
        st.write(f"Removed reflexive inference noise triples: {removed_noise_triples}")
        st.write(f"Triples after cleanup: {triples_after_cleanup}")

        if new_triples <= 0:
            st.warning("OWL-RL completed, but no new triples were materialized.")

        save_rdf_graph(
            graph=graph,
            output_file_path=output_kb_path,
            rdf_format="xml",
        )

        if not output_kb_path.is_file():
            st.error(f"Step 3.2 output file was not created: {output_kb_path}")
            return False

        return True

    except Exception as error:
        st.error(f"Error while running OWL-RL materialization: {error}")
        return False