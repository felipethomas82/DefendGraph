"""
Tab 4: Explanation (Stage 4)
"""
import streamlit as st
from streamlit_mermaid import st_mermaid
from pathlib import Path
from pipeline_config import PIPELINE
from src.ui.tabs.tab_helper import render_tab_checklist
from src.state import is_step_completed, get_step_state_filename_fullpath, delete_file_if_exists
from src.rdflib.competency_question_resolution import resolve_competency_questions
from src.utils.create_md_defensive_advisory_synthesis import generate_md_file_defensive_advisory
from src.view_esquematic.create_mmd_path_graph import generate_reasoning_path_mermaid_from_cq_results


def render_tab_explanation():
    """
    Render Tab: Explanation (Stage 4)
    """
    #######################################################
    #Tab header and tab checklist
    stage = "4"

    #Tab header
    stage_header = PIPELINE[stage]["name"]
    st.header(f"Stage {stage}: {stage_header}")    
    
    #Tab checklist
    checklist_placeholder = st.empty()

    st.divider()
    ######################################################
    # Step 4.1 - Execute Competency Questions (SPARQL queries)
    step = "4.1"
    step_name = PIPELINE[stage]["steps"][step]["name"]
    st.subheader(f"Step {step}: {step_name}", help=PIPELINE[stage]["steps"][step]["help"])    
    
    #Check if step is already completed based on file -> state
    if is_step_completed(step):
        st.session_state.competency_question_resulted = True

    # Extract inferential path
    if st.session_state.get("competency_question_resulted", False) == False:
        competency_question_button = True
    else:
        competency_question_button = False
    
    if st.button("Get competency question answer",
        disabled=not competency_question_button,
        width="stretch"
    ):
        with st.spinner("Getting results competency question..."):
            success = resolve_competency_questions()
            if success:
                st.session_state.competency_question_resulted = True
                st.success("Results competency question obtained successfully!")
            else:
                st.error("Could not resolve competency questions.")

    if st.session_state.get("competency_question_resulted", False):
        st.info("Results competency question is currently loaded.")

    # Clear button
    if st.button("Clear competency question results",
        disabled=not st.session_state.get("competency_question_resulted", False),
        width="stretch"
    ):
        clear_competency_question_results(get_step_state_filename_fullpath(step))
        st.rerun()

    st.divider()
    ######################################################
    #generate_defensive_advisory()
    # Step 4.2 - Create Defensive Advisory (Markdown .md file)
    step = "4.2"
    step_name = PIPELINE[stage]["steps"][step]["name"]
    st.subheader(f"Step {step}: {step_name}", help=PIPELINE[stage]["steps"][step]["help"])    
    
    #Check if step is already completed based on file -> state
    if is_step_completed(step):
        st.session_state.markdown_file_generated = True

    # Extract inferential path
    if st.session_state.get("markdown_file_generated", False) == False:
        markdown_button = True
    else:
        markdown_button = False
    
    if st.button("Generate markdown .md file",
        disabled=not markdown_button,
        width="stretch"
    ):
        with st.spinner("Generating markdown .md file..."):
            success = generate_md_file_defensive_advisory()
            if success:
                st.session_state.markdown_file_generated = True
                st.success("Markdown .md file generated successfully!")
            else:
                st.error("Could not generate markdown .md file.")

    if st.session_state.get("markdown_file_generated", False):
        st.info("Markdown .md file is currently loaded.")
        
    #Render markdown file
    if st.session_state.get("markdown_file_generated", False):
        advisory_path = get_step_state_filename_fullpath(step)
        with open(advisory_path, "r") as f:
            st.markdown(f.read())

    # Clear button
    if st.button("Clear markdown .md file",
        disabled=not st.session_state.get("markdown_file_generated", False),
        width="stretch"
    ):
        clear_markdown_file(get_step_state_filename_fullpath(step))
        st.rerun()

    st.divider()
    ######################################################
    # Step 4.3 - Create Reasoning Path Visualization
    step = "4.3"
    step_name = PIPELINE[stage]["steps"][step]["name"]
    st.subheader(f"Step {step}: {step_name}", help=PIPELINE[stage]["steps"][step]["help"])    
    
    #Check if step is already completed based on file -> state
    if is_step_completed(step):
        st.session_state.path_graph_created = True

    # Extract inferential path
    if st.session_state.get("path_graph_created", False) == False:
        path_graph_button = True
    else:
        path_graph_button = False

    if st.button("Create path visualization",
        disabled=not path_graph_button,
        width="stretch"
    ):
        with st.spinner("Creating path visualization..."):
            success = generate_reasoning_path_mermaid_from_cq_results()
            if success:
                st.session_state.path_graph_created = True
                st.success("Path graph visualization created successfully!")
            else:
                st.error("Could not create path graph visualization.")

    if st.session_state.get("path_graph_created", False):
        st.info("Path graph visualization is currently loaded.")

    #Render mmd mermaid file
    if st.session_state.get("path_graph_created", False):
        mmd_path = get_step_state_filename_fullpath(step)
        with open(mmd_path, "r") as f:
            mermaid_code = f.read()
            st_mermaid(mermaid_code)

    # Clear button
    if st.button("Clear path graph visualization",
        disabled=not st.session_state.get("path_graph_created", False),
        width="stretch"
    ):
        clear_path_graph_created(get_step_state_filename_fullpath(step))
        st.rerun()

    st.divider()
    ######################################################
    # Render checklist container after running validation logic
    with checklist_placeholder.container():
        render_tab_checklist(stage)

def clear_competency_question_results(file_path: str | Path) -> None:
    """
    Clear competency question results state and delete the saved competency question results file.
    """
    delete_file_if_exists(file_path)

    st.session_state.competency_question_resulted = False

def clear_markdown_file(file_path: str | Path) -> None:
    """
    Clear markdown file state and delete the saved markdown file.
    """
    delete_file_if_exists(file_path)

    st.session_state.markdown_file_generated = False

def clear_path_graph_created(file_path: str | Path) -> None:
    """
    Clear path graph created state and delete the saved path graph file.
    """
    delete_file_if_exists(file_path)

    st.session_state.path_graph_created = False

