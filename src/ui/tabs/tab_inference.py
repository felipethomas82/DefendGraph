"""
Tab 3: Inference (Stage 3)
"""
import streamlit as st
from pathlib import Path
from pipeline_config import PIPELINE
from src.ui.tabs.tab_helper import render_tab_checklist
from src.state import is_step_completed, get_step_state_filename_fullpath, delete_file_if_exists
from src.owl2ready.check_DL_consistency import check_DL_consistency
from src.owl2ready.create_materialized_kb import materialize_owlrl_assertions

def render_tab_inference():
    """
    Render Tab: Inference (Stage 3)
    """
    #######################################################
    #Tab header and tab checklist
    stage = "3"

    #Tab header
    stage_header = PIPELINE[stage]["name"]
    st.header(f"Stage {stage}: {stage_header}")    
    
    #Tab checklist
    checklist_placeholder = st.empty()
    
    st.divider()
    ######################################################
    # Step 3.1 - Logical Consistency Checking
    step = "3.1"
    step_name = PIPELINE[stage]["steps"][step]["name"]
    st.subheader(f"Step {step}: {step_name}", help=PIPELINE[stage]["steps"][step]["help"])    
    template_filename = PIPELINE[stage]["steps"][step]["template"]
    template_path = Path(template_filename) #not used in this step, but kept for consistency with other steps 

    #Check if step is already completed based on file -> state
    if is_step_completed(step):
        st.session_state.consistent_kb = True

    # Check logical consistency
    check_dl_consistency_button_enabled = (
        st.session_state.get("parsed_alert", False) #Step 1.1
        and st.session_state.get("rdf_converted", False) #Step 1.2
        and st.session_state.get("kb_loaded", False) #Step 2.1
        and st.session_state.get("annotation_loaded", False) #Step 2.2
        and st.session_state.get("full_graph_loaded", False) #Step 2.3
        and st.session_state.get("subgraph_loaded", False) #Step 2.4
        and not st.session_state.get("consistent_kb", False) #Step 3.1 - actual
    )

    if st.button("Check Logical Consistency",
        disabled=not check_dl_consistency_button_enabled,
        width="stretch"
    ):
        with st.spinner("Checking logical consistency..."):
            is_consistent = check_DL_consistency()
            if is_consistent:
                st.session_state.consistent_kb = True
                st.success("Logical consistency checked successfully!")

    if st.session_state.get("consistent_kb", False):
        st.info("DL consistent KB is currently loaded.")

    # Clear button
    if st.button("Clear DL consistent KB",
        disabled=not st.session_state.get("consistent_kb", False),
        width="stretch"
    ):
        clear_DL_consistent_KB(get_step_state_filename_fullpath(step))
        st.rerun()

    st.divider()
    ######################################################
    # Step 3.2 - Semantic Assertion Materialization
    step = "3.2"
    step_name = PIPELINE[stage]["steps"][step]["name"]
    st.subheader(f"Step {step}: {step_name}", help=PIPELINE[stage]["steps"][step]["help"])    
    template_filename = PIPELINE[stage]["steps"][step]["template"]
    template_path = Path(template_filename) #not used in this step, but kept for consistency with other steps

    #Check if step is already completed based on file -> state
    if is_step_completed(step):
        st.session_state.materialized_kb = True

    # Semantic Assertion Materialization
    check_materialization_button_enabled = (
        st.session_state.get("parsed_alert", False) #Step 1.1
        and st.session_state.get("rdf_converted", False) #Step 1.2
        and st.session_state.get("kb_loaded", False) #Step 2.1
        and st.session_state.get("annotation_loaded", False) #Step 2.2
        and st.session_state.get("full_graph_loaded", False) #Step 2.3
        and st.session_state.get("subgraph_loaded", False) #Step 2.4
        and st.session_state.get("consistent_kb", False) #Step 3.1 
        and not st.session_state.get("materialized_kb", False) #Step 3.2 - actual
    )

    if st.button("Create Materialized KB",
        disabled=not check_materialization_button_enabled,
        width="stretch"
    ):
        with st.spinner("Creating materialized KB..."):
            materialize_owlrl_assertions()
            st.session_state.materialized_kb = True
            st.success("Materialized KB created successfully!")

    if st.session_state.get("materialized_kb", False):
        st.info("Materialized KB is currently loaded.")
                
    # Clear button
    if st.button("Clear Materialized KB",
        disabled=not st.session_state.get("materialized_kb", False),
        width="stretch"
    ):
        clear_materialized_KB(get_step_state_filename_fullpath(step))
        st.rerun()

    st.divider()
    ######################################################

    # Render checklist container after running validation logic
    with checklist_placeholder.container():
        render_tab_checklist(stage)

def clear_DL_consistent_KB(file_path: str | Path) -> None:
    """
    Clear DL consistent KB state and delete the saved DL consistent KB file.
    """
    delete_file_if_exists(file_path)

    st.session_state.consistent_kb = False

def clear_materialized_KB(file_path: str | Path) -> None:
    """
    Clear materialized KB state and delete the saved materialized KB file.
    """
    delete_file_if_exists(file_path)

    st.session_state.materialized_kb = False


def render_materialized_kb_inspection(inspection_result: dict | None) -> None:
    """
    Render materialized KB inspection result in Streamlit.
    """

    if inspection_result is None:
        st.error("No materialized KB inspection result to show.")
        return

    kb_statistics = inspection_result.get("kb_statistics", {})
    if kb_statistics:
        st.markdown("### Knowledge Base Statistics")
        st.write(kb_statistics)

    materialization_delta = inspection_result.get("materialization_delta", {})
    if materialization_delta:
        st.markdown("### Materialization Delta")

        st.metric(
            "New triples",
            materialization_delta.get("new_triples_count", 0),
        )

        st.write("New type assertions")
        st.dataframe(materialization_delta.get("new_type_assertions", []))

        st.write("New object property assertions")
        st.dataframe(materialization_delta.get("new_object_property_assertions", []))

        st.write("New data property assertions")
        st.dataframe(materialization_delta.get("new_data_property_assertions", []))

    alert_individuals = inspection_result.get("alert_individuals", [])
    if alert_individuals:
        st.markdown("### Alert Individuals")

        for item in alert_individuals:
            st.markdown(f"#### {item.get('individual')}")

            st.write("Types")
            st.dataframe(item.get("types", []))

            st.write("Outgoing relations")
            st.dataframe(item.get("outgoing_relations", []))

            st.write("Incoming relations")
            st.dataframe(item.get("incoming_relations", []))

            st.write("Data properties")
            st.dataframe(item.get("data_properties", []))

    logical_axioms = inspection_result.get("logical_axioms", {})
    if logical_axioms:
        st.markdown("### Logical Axioms")

        for axiom_name, axiom_data in logical_axioms.items():
            st.write(axiom_name.replace("_", " ").title())
            st.dataframe(axiom_data)