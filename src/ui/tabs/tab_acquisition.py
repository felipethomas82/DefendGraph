"""
Tab 5: Human Validation and Knowledge Acquisition (Stage 5)
"""
import streamlit as st
import json
from pipeline_config import PIPELINE
from src.ui.tabs.tab_helper import render_tab_checklist


def render_tab_acquisition():
    """
    Render Tab: Human Validation and Knowledge Acquisition (Stage 5)
    """
    #######################################################
    #Tab header and tab checklist
    stage = "5"

    #Tab header
    stage_header = PIPELINE[stage]["name"]
    st.header(f"Stage {stage}: {stage_header}")    
    
    #Tab checklist
    checklist_placeholder = st.empty()
    
    st.divider()
    ######################################################

    # Render checklist container after running validation logic
    with checklist_placeholder.container():
        render_tab_checklist(stage)