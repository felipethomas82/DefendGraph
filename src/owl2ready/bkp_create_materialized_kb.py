# used on Step 3.2 - Semantic Assertion Materialization

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
    """
    file_path_str = str(file_path)

    if re.match(r"^/[A-Za-z]:/", file_path_str):
        file_path_str = file_path_str[1:]

    return Path(file_path_str)


def register_local_ontology_file(
    ontology_iri: str,
    ontology_file_path: str | Path,
) -> None:
    """
    Register a local ontology file in Owlready2 using PREDEFINED_ONTOLOGIES.
    """
    normalized_path = normalize_windows_path(ontology_file_path).resolve()
    PREDEFINED_ONTOLOGIES[ontology_iri] = str(normalized_path)


def load_local_ontology(
    world: World,
    ontology_iri: str,
    ontology_file_path: str | Path,
):
    """
    Load a local ontology file into an Owlready2 World using a logical ontology IRI.
    """
    register_local_ontology_file(
        ontology_iri=ontology_iri,
        ontology_file_path=ontology_file_path,
    )

    ontology = world.get_ontology(ontology_iri).load()

    return ontology


def materialize_DL_assertions() -> bool:
    """
    Step 3.2 - Semantic Assertion Materialization.

    Input:
        Step 3.1 OWL file.

    Output:
        Step 3.2 materialized OWL file.

    Behavior:
        - Loads the consistent KB generated in Step 3.1.
        - Runs Pellet with materialization enabled.
        - Saves the reasoned/materialized ontology as Step 3.2.

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

    ontology_iri = "http://kg-ciber.local/ontology/step-3-2-materialization.owl"

    world = None

    try:
        if not input_kb_path.is_file():
            st.error(f"Step 3.1 input file not found: {input_kb_path}")
            return False

        output_kb_path.parent.mkdir(parents=True, exist_ok=True)

        if output_kb_path.exists():
            output_kb_path.unlink()

        world = World()

        ontology = load_local_ontology(
            world=world,
            ontology_iri=ontology_iri,
            ontology_file_path=input_kb_path,
        )

        #st.info("Running Pellet semantic materialization...")

        with ontology:
            sync_reasoner_pellet(
                infer_property_values=True,
                infer_data_property_values=True,
                debug=1,
            )

        world.save(
            file=str(output_kb_path),
            format="rdfxml",
        )

        #if not output_kb_path.is_file():
        #    st.error(f"Step 3.2 output file was not created: {output_kb_path}")
        #    return False

        #st.success("Semantic assertions materialized successfully.")
        #st.success(f"Step 3.2 output file created: {output_kb_path}")

        return True

    except OwlReadyInconsistentOntologyError:
        st.error("The knowledge base is logically inconsistent.")
        st.warning("Step 3.2 output file was not created.")
        return False

    #except OwlReadyJavaError as error:
    #    st.error("Pellet returned a Java error during semantic materialization.")
    #    st.exception(error)
    #    return False

    except Exception as error:
        st.error(f"Error while running semantic materialization: {error}")
        return False

    finally:
        if world is not None:
            try:
                world.close()
            except Exception:
                pass