"""
Sidebar
"""
import streamlit as st
from streamlit_mermaid import st_mermaid
from pipeline_config import SIDEBAR, PIPELINE
from src.state import is_stage_completed, delete_all_state_files

def render_sidebar():
    """
    Renderiza a sidebar com informações macro do pipeline.
    """
    with st.sidebar:
        #######################################################
        #Sidebar header and Sidebar caption
        sidebar_header = SIDEBAR["name"]
        sidebar_caption = SIDEBAR["caption"]
        st.header(sidebar_header)
        st.caption(sidebar_caption)
        
        st.divider()
        #######################################################
        #Show static pipeline 
        if st.button("Show stages pipeline (schematic)",width="stretch"):
            render_static_pipeline_mermaid()

        if st.button("Hide stages pipeline (schematic)",width="stretch"):
            st.rerun()
        
        st.divider()        
        #######################################################        
        # Pipeline - Stages        
        # Create one button and one icon (ok and pending) - both for each stage 
        # Each button selects the corresponding tab/stage

        #Stage 1
        stage_id = "1"
        create_stage_button(stage_id)
        
        #Stage 2
        stage_id = "2"
        create_stage_button(stage_id)

        #Stage 3
        stage_id = "3"
        create_stage_button(stage_id)

        #Stage 4
        stage_id = "4"
        create_stage_button(stage_id)

        #Stage 5
        #stage_id = "5"
        #create_stage_button(stage_id)
        
        st.divider()
        #######################################################
        # Reset all stages button
        if st.button("Reset all stages",width = "stretch"):
            delete_all_state_files()
            clear_all_session_state()
            st.session_state.active_tab = 1
            st.rerun()


def create_stage_button(stage_id: str) -> str:
    stage_name = PIPELINE[stage_id]["name"]
    status_icon = get_stage_status_icon(stage_id)
    button_label = f"Stage {stage_id}:\t\t{stage_name}\n\nStatus:\t\t{status_icon}"
    st.button(button_label,width = "stretch", on_click=set_active_tab, args=[int(stage_id)], help=PIPELINE[stage_id]["help"]) 


def set_active_tab(tab_id: int):
    """
    Update the active tab in Streamlit session state.
    """
    st.session_state.active_tab = tab_id


def get_stage_status_icon(stage_id: str) -> str:
    """
    Return the status icon for a stage.
    """
    return "✅" if is_stage_completed(stage_id) else "⏳"


def clear_all_session_state() -> None:
    """
    Remove all keys from Streamlit session state.
    """
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def render_static_pipeline_mermaid() -> None:
    """
    Render the static pipeline Mermaid diagram directly in Streamlit.
    This does not generate any .mmd file.
    """
    st.subheader("Reasoning Path Visualization")

    mermaid_code = """
flowchart TD
    A["Wazuh Alert"] --> B["Parsed Alert Fields"]
    B --> C["Alert RDF Representation"]
    C --> D["Alert RDF edited with Semantic Annotation"]
    D --> E["Materialized Knowledge Base"]
    E --> F["Competency Question Results"]
    F --> G["Defensive Advisory Synthesis"]
    F --> H["Reasoning Path Visualization"]

    A -. evidence .-> F
    E -. inferred context .-> F
    G -. explanation .-> H
"""
    st_mermaid(mermaid_code)