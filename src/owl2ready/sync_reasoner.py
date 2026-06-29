#not used - to be deleted

from pathlib import Path
import re

import streamlit as st
from owlready2 import (
    World,
    PREDEFINED_ONTOLOGIES,
    sync_reasoner_pellet,
    OwlReadyInconsistentOntologyError,
    OwlReadyJavaError,
)

from src.state import get_step_state_filename_fullpath


def normalize_windows_path(file_path: str | Path) -> Path:
    """
    Normalize a file path that may incorrectly start with '/C:/' on Windows.

    Example:
        /C:/Users/Eduardo/file.owl

    Becomes:
        C:/Users/Eduardo/file.owl
    """
    file_path_str = str(file_path)

    if re.match(r"^/[A-Za-z]:/", file_path_str):
        file_path_str = file_path_str[1:]

    return Path(file_path_str)


def register_local_ontology_file(ontology_iri: str, ontology_file_path: str | Path) -> None:
    """
    Register a local ontology file in Owlready2 using PREDEFINED_ONTOLOGIES.

    This avoids loading local Windows files through file:///C:/... URIs,
    which may be internally converted to invalid /C:/... paths.
    """
    normalized_path = normalize_windows_path(ontology_file_path).resolve()

    PREDEFINED_ONTOLOGIES[ontology_iri] = str(normalized_path)


def load_local_ontology(
    world: World,
    ontology_iri: str,
    ontology_file_path: str | Path
):
    """
    Load a local ontology file into an Owlready2 World using a logical ontology IRI.
    """
    register_local_ontology_file(
        ontology_iri=ontology_iri,
        ontology_file_path=ontology_file_path
    )

    ontology = world.get_ontology(ontology_iri).load()

    return ontology


def get_world_triples(world: World) -> set:
    """
    Return all triples from an Owlready2 World as a Python set.
    """
    rdflib_graph = world.as_rdflib_graph()

    return set(rdflib_graph.triples((None, None, None)))


def get_reasoner_target_ontologies(world: World) -> list:
    """
    Return the list of ontologies that should be processed by the reasoner.
    """
    target_ontologies = []

    for ontology in world.ontologies.values():
        ontology_base_iri = str(ontology.base_iri)

        if ontology_base_iri.startswith("http://www.w3.org/"):
            continue

        target_ontologies.append(ontology)

    return target_ontologies


def run_owlready_reasoner() -> bool:
    """
    Load the Owlready2 World from PIPELINE step 2.2 and run the Pellet reasoner.

    Input:
        None. File paths are obtained from PIPELINE.

    Output:
        True if the reasoner finished without inconsistency; otherwise False.
    """

    input_world_step_id = "2.2"

    input_world_path = normalize_windows_path(
        get_step_state_filename_fullpath(input_world_step_id)
    )

    world_ontology_iri = "http://kg-ciber.local/ontology/owlready-world.owl"
    inferred_ontology_iri = "http://kg-ciber.local/ontology/inferred-facts.owl"

    try:
        if not input_world_path.is_file():
            st.error(f"Owlready2 World file not found: {input_world_path}")
            return False

        world = World()

        loaded_world_ontology = load_local_ontology(
            world=world,
            ontology_iri=world_ontology_iri,
            ontology_file_path=input_world_path
        )

        inferred_ontology = world.get_ontology(inferred_ontology_iri)

        before_triples = get_world_triples(world)
        before_triple_count = len(before_triples)

        target_ontologies = get_reasoner_target_ontologies(world)

        if not target_ontologies:
            st.error("No ontologies found in the Owlready2 World.")
            return False

        with inferred_ontology:
            sync_reasoner_pellet(
                target_ontologies,
                infer_property_values=True,
                infer_data_property_values=True,
                debug=2
            )

        after_triples = get_world_triples(world)
        after_triple_count = len(after_triples)

        new_inferred_triples = after_triples - before_triples
        new_inferred_fact_count = len(new_inferred_triples)

        st.session_state["owlready_reasoned_world"] = world
        st.session_state["owlready_loaded_world_ontology"] = loaded_world_ontology
        st.session_state["owlready_inferred_ontology"] = inferred_ontology
        st.session_state["owlready_inconsistent"] = False
        st.session_state["owlready_new_inferred_fact_count"] = new_inferred_fact_count

        st.success("Pellet reasoner finished successfully.")

        st.write("Inconsistency found:", False)
        st.write("Triples before reasoning:", before_triple_count)
        st.write("Triples after reasoning:", after_triple_count)
        st.write("New inferred facts:", new_inferred_fact_count)

        if new_inferred_fact_count > 0:
            st.write("Sample inferred facts:")

            sample_size = min(10, new_inferred_fact_count)

            for index, triple in enumerate(list(new_inferred_triples)[:sample_size], start=1):
                subject, predicate, object_value = triple
                st.write(
                    f"{index}.",
                    str(subject),
                    str(predicate),
                    str(object_value)
                )

        return True

    except OwlReadyInconsistentOntologyError:
        st.session_state["owlready_inconsistent"] = True
        st.session_state["owlready_new_inferred_fact_count"] = 0

        st.error("Pellet found an inconsistent ontology.")

        st.write("Inconsistency found:", True)
        st.write("New inferred facts:", 0)

        return False

    except OwlReadyJavaError as error:
        st.error(f"Java/Pellet error while running the reasoner: {error}")
        st.warning("Check if Java is installed and available in the system PATH.")

        return False

    except Exception as error:
        st.error(f"Error running Owlready2 reasoner: {error}")

        return False