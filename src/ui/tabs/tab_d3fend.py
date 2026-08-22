"""
Tab 2: Knowledge Base (Mitre D3fend)
"""
import streamlit as st
from typing import Any
import json
from pathlib import Path
from pipeline_config import PIPELINE
from src.ui.tabs.tab_helper import render_tab_checklist
from src.state import get_step_state_filename_fullpath, is_step_completed, read_owl_file, write_owl_file, delete_file_if_exists, is_stage_completed
from src.rdflib.create_alert_annotated_rdf import create_annotated_rdf
from src.rdflib.create_full_knowledge_graph import create_full_knowledge_graph
from src.rdflib.method_1_syntactic_graph_traversal import create_syntactic_graph_traversal_subgraph
from src.rdflib.method_2_ontology_slicing import create_ontology_slicing_subgraph
from src.rdflib.method_3_full_global_baseline import create_full_global_baseline_subgraph


def render_tab_d3fend():
    """
    Render Tab: Alert (Stage 2)
    """
    #######################################################
    #Tab header and tab checklist
    stage = "2"

    #Tab header
    stage_header = PIPELINE[stage]["name"]
    st.header(f"Stage {stage}: {stage_header}")    
    
    #Tab checklist
    checklist_placeholder = st.empty()
    
    st.divider()
    ######################################################
    # Step 2.1 - Knowledge Base (Mitre D3fend)
    step = "2.1"
    step_name = PIPELINE[stage]["steps"][step]["name"]
    st.subheader(f"Step {step}: {step_name}", help=PIPELINE[stage]["steps"][step]["help"])
    template_filename = PIPELINE[stage]["steps"][step]["template"]
    template_path = Path(template_filename) #not used in this step, but kept for consistency with other steps

    #Check if step is already completed based on file -> state
    if is_step_completed(step):
        st.session_state.kb_loaded = True
    
    # Uploader button
    uploaded_file = st.file_uploader("Upload Knowledge Base [Mitre D3fend] (owl)", type=["owl"], accept_multiple_files=False, help="Select the knowledge base (Mitre D3fend ontology) as .owl file (RDF/XML)")
    
    # Clear button
    if st.button("Clear Knowledge base",
        disabled=not st.session_state.get("kb_loaded", False),
        width="stretch"
    ):
        clear_knowledge_base_state(get_step_state_filename_fullpath(step))
        st.rerun()

    # Process uploaded file
    if uploaded_file is not None:
        try:
            uploaded_kb = uploaded_file.getvalue().decode("utf-8")
            st.session_state.kb_loaded = True
            write_owl_file(get_step_state_filename_fullpath(step), uploaded_kb)
            st.success("Knowledge base file loaded successfully!")

        except Exception as error:
            st.session_state.kb_loaded = False
            st.error(f"Error loading knowledge base file: {error}")

    saved_kb = read_owl_file(get_step_state_filename_fullpath(step))

    if saved_kb is not None:
        st.session_state.kb_loaded = True

    if st.session_state.get("kb_loaded", False) and saved_kb is not None:
        st.info("A knowledge base is currently loaded.")

    st.divider()    
    ######################################################
    # Step 2.2 - Alert Semantic Annotation
    step = "2.2"
    step_name = PIPELINE[stage]["steps"][step]["name"]
    st.subheader(f"Step {step}: {step_name}", help=PIPELINE[stage]["steps"][step]["help"])    
    template_filename = PIPELINE[stage]["steps"][step]["template"]
    template_path = Path(template_filename) 

    #Check if step is already completed based on file -> state
    if is_step_completed(step):
        st.session_state.annotation_loaded = True

    # Create Annotated rdf
    create_annotated_rdf_button_enabled = (
        st.session_state.get("parsed_alert", False) #Step 1.1
        and st.session_state.get("rdf_converted", False) #Step 1.2
        and st.session_state.get("kb_loaded", False) #Step 2.1
        and not st.session_state.get("annotation_loaded", False) #Step 2.2 - actual
    )

    if st.button("Create Annotated RDF",
        disabled=not create_annotated_rdf_button_enabled,
        width="stretch"
    ):
        with st.spinner("Creating Annotated RDF file using RDFlib..."):
            create_annotated_rdf(template_path)
        st.session_state.annotation_loaded = True
        st.success("Annotated RDF file created successfully!")

    if st.session_state.get("annotation_loaded", False):
        st.info("Annotated RDF file is currently loaded.")

    # Clear button
    if st.button("Clear annotated RDF",
        disabled=not st.session_state.get("annotation_loaded", False),
        width="stretch"
    ):
        clear_annotation_state(get_step_state_filename_fullpath(step))
        st.rerun()

    st.divider()
    ######################################################
    # Step 2.3 - ABox (alert) Instantiation to TBox (D3FEND)
    step = "2.3"
    step_name = PIPELINE[stage]["steps"][step]["name"]
    st.subheader(f"Step {step}: {step_name}", help=PIPELINE[stage]["steps"][step]["help"])    
    template_filename = PIPELINE[stage]["steps"][step]["template"]
    template_path = Path(template_filename) #not used in this step, but kept for consistency with other steps

    #Check if step is already completed based on file -> state
    if is_step_completed(step):
        st.session_state.full_graph_loaded = True

    # Instantiation to TBox
    create_full_knowledge_graph_button_enabled = (
        st.session_state.get("parsed_alert", False) #Step 1.1
        and st.session_state.get("rdf_converted", False) #Step 1.2
        and st.session_state.get("kb_loaded", False) #Step 2.1
        and st.session_state.get("annotation_loaded", False) #Step 2.2
        and not st.session_state.get("full_graph_loaded", False) #Step 2.3 - actual
    )

    if st.button("Create full knowledge graph (D3fend + Annotated Alert RDF)",
        disabled=not create_full_knowledge_graph_button_enabled,
        width="stretch"
    ):
        with st.spinner("Creating full knowledge graph..."):
            create_full_knowledge_graph()
        st.session_state.full_graph_loaded = True
        st.success("Full knowledge graph created successfully!")

    if st.session_state.get("full_graph_loaded", False):
        st.info("Full knowledge graph is currently loaded.")

    # Clear button
    if st.button("Clear full knowledge graph",
        disabled=not st.session_state.get("full_graph_loaded", False),
        width="stretch"
    ):
        clear_full_knowledge_graph_state(get_step_state_filename_fullpath(step))
        st.rerun()

    st.divider()
    ######################################################
    # Step 2.4 - Create modular Knowledge Base (Subgraph Extraction)
    step = "2.4"
    step_name = PIPELINE[stage]["steps"][step]["name"]
    st.subheader(f"Step {step}: {step_name}", help=PIPELINE[stage]["steps"][step]["help"])    
    template_filename = PIPELINE[stage]["steps"][step]["template"]
    template_path = Path(template_filename)

    #Render selected method and its fields
    with template_path.open("r", encoding="utf-8") as file:
        methods_template = json.load(file)

    render_selected_subgraph_method(methods_template)   

    #Check if step is already completed based on file -> state
    if is_step_completed(step):
        st.session_state.subgraph_loaded = True

    # Create subgraph
    create_subgraph_button_enabled = (
        st.session_state.get("parsed_alert", False) #Step 1.1
        and st.session_state.get("rdf_converted", False) #Step 1.2
        and st.session_state.get("kb_loaded", False) #Step 2.1
        and st.session_state.get("annotation_loaded", False) #Step 2.2
        and st.session_state.get("full_graph_loaded", False) #Step 2.3
        and not st.session_state.get("subgraph_loaded", False) #Step 2.4 - actual
    )

    if st.button("Create Knowledge Base subgraph",
        disabled=not create_subgraph_button_enabled,
        width="stretch"
    ):
        with st.spinner("Creating subgraph..."):
            selected_method = methods_template["selected_method"]

            if selected_method == "method_1_syntactic_graph_traversal":
                success = create_syntactic_graph_traversal_subgraph(template_path)

            elif selected_method == "method_2_ontology_slicing":
                success = create_ontology_slicing_subgraph(template_path)

            elif selected_method == "method_3_full_global_baseline":
                success = create_full_global_baseline_subgraph(template_path)

            else:
                st.error(f"Unknown selected method: {selected_method}")
                success = False
        
            if success:
                st.session_state.subgraph_loaded = True
                st.success("Subgraph created successfully!")

    if st.session_state.get("subgraph_loaded", False):
        st.info("Subgraph is currently loaded.")

    # Clear button
    if st.button("Clear Knowledge Base subgraph",
        disabled=not st.session_state.get("subgraph_loaded", False),
        width="stretch"
    ):
        clear_subgraph_state(get_step_state_filename_fullpath(step))
        st.rerun()

    st.divider()
    ######################################################
    
    
    ######################################################
    # Step 2.2 - Create world Owl2Ready
    #step = "2.2"
    #step_name = PIPELINE[stage]["steps"][step]["name"]
    #st.subheader(f"Step {step}: {step_name}")
    #
    ##Condition to start owl2ready: Stage 1 completed + Step 2.1 completed
    #if is_stage_completed("1") and is_step_completed("2.1"):
    #    button_condition = True
    #else:
    #    button_condition = False
    #
    #if st.button("Create world Owl2Ready", disabled=not button_condition, width="stretch"):
    #    #todo
    #    world_created = create_owlready_world()
    #    if world_created:
    #        st.success("Owlready2 World created successfully!")
    #    else:
    #        st.error("Error creating Owlready2 World")
    #
    #st.divider()    
    ######################################################

    # Render checklist container after running validation logic
    with checklist_placeholder.container():
        render_tab_checklist(stage)


def clear_knowledge_base_state(file_path: str | Path) -> None:
    """
    Clear knowledge base state and delete the saved knowledge base file.
    """
    delete_file_if_exists(file_path)

    st.session_state.kb_loaded = False


def clear_annotation_state(file_path: str | Path) -> None:
    """
    Clear annotated rdf state and delete the saved annotation file.
    """
    delete_file_if_exists(file_path)

    st.session_state.annotation_loaded = False


def clear_full_knowledge_graph_state(file_path: str | Path) -> None:
    """
    Clear full knowledge graph state and delete the saved full knowledge graph file.
    """
    delete_file_if_exists(file_path)

    st.session_state.full_graph_loaded = False


def clear_subgraph_state(file_path: str | Path) -> None:
    """
    Clear subgraph state and delete the saved subgraph file.
    """
    delete_file_if_exists(file_path)

    st.session_state.subgraph_loaded = False


def render_selected_subgraph_method(methods_template: dict) -> None:
    """
    Render the selected Step 2.4 extraction method and its configuration.
    """

    selected_method_id = methods_template.get("selected_method")
    methods = methods_template.get("methods", {})

    selected_method = methods.get(selected_method_id)

    if selected_method is None:
        st.error(f"Selected method not found in template: {selected_method_id}")
        return

    #Selected Method
    st.text_input(
        "Selected Method",
        value=selected_method.get("name", selected_method_id),
        disabled=True,
        help="Extraction method selected in modular_knowledge_graph_methods.json.",
    )
    st.caption(selected_method.get("description", ""))

    # Method configuration - fields from json template

    config = selected_method.get("config", {})

    for field_name, field_config in config.items():
        value = field_config.get("value")
        help_text = field_config.get("description", "")

        if isinstance(value, bool):
            st.checkbox(
                field_name,
                value=value,
                disabled=True,
                help=help_text,
            )

        elif isinstance(value, list):
            st.text_area(
                field_name,
                value=", ".join(str(item) for item in value),
                disabled=True,
                height=80,
                help=help_text,
            )

        else:
            st.text_input(
                field_name,
                value=str(value),
                disabled=True,
                help=help_text,
            )