# used on Step 3.1 - Logical Consistency Checking

from pathlib import Path
import re
import shutil

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


def check_DL_consistency() -> bool:
    """
    Step 3.1 - Logical Consistency Checking.

    Input:
        Step 2.4 OWL file.

    Output:
        Step 3.1 OWL file.

    Behavior:
        - Loads the Step 2.4 OWL file directly.
        - Runs Pellet to check logical consistency.
        - If consistent, copies Step 2.4 to Step 3.1.
        - If inconsistent, does not create Step 3.1.

    Returns:
        True if the knowledge base is consistent.
        False otherwise.
    """

    input_step_id = "2.4"
    output_step_id = "3.1"

    input_kb_path = normalize_windows_path(
        get_step_state_filename_fullpath(input_step_id)
    ).resolve()

    output_kb_path = normalize_windows_path(
        get_step_state_filename_fullpath(output_step_id)
    ).resolve()

    ontology_iri = "http://kg-ciber.local/ontology/step-3-1-consistency-check.owl"

    try:
        if not input_kb_path.is_file():
            st.error(f"Step 2.4 input file not found: {input_kb_path}")
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

        #st.info("Running Pellet consistency check...")

        with ontology:
            sync_reasoner_pellet(
                infer_property_values=False,
                infer_data_property_values=False,
                debug=1,
            )

        shutil.copyfile(input_kb_path, output_kb_path)

        #if not output_kb_path.is_file():
        #    st.error(f"Step 3.1 output file was not created: {output_kb_path}")
        #    return False

        #st.success("Knowledge base is logically consistent.")
        #st.success(f"Step 3.1 output file created: {output_kb_path}")

        return True

    except OwlReadyInconsistentOntologyError:
        st.error("The knowledge base is logically inconsistent.")
        st.warning("Step 3.1 output file was not created.")
        return False

    #except OwlReadyJavaError as error:
    #    st.error("Pellet returned a Java error during consistency checking.")
    #    st.exception(error)
    #    return False

    except Exception as error:
        st.error(f"Error while running DL consistency checking: {error}")
        return False

    finally:
        if world is not None:
            try:
                world.close()
            except Exception:
                pass