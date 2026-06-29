"""
Sistema Especialista
Interface Streamlit para análise de alertas Wazuh com enriquecimento semântico
"""

import streamlit as st
from src.ui.sidebar import render_sidebar
from src.ui.tabs.tab_alert import render_tab_alert
from src.ui.tabs.tab_d3fend import render_tab_d3fend
from src.ui.tabs.tab_inference import render_tab_inference
from src.ui.tabs.tab_explanation import render_tab_explanation
#from src.ui.tabs.tab_acquisition import render_tab_acquisition


def main():
    """
    Main function
    """
    ##################################################################
    #  Layout
    st.set_page_config(
        page_title="Sistema Especialista",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    hide_sidebar_button()
    ################################################################
    # Render the sidebar and tab
    
    # Intial state st.session_state (tabs)
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = 1

    # Render sidebar
    render_sidebar()

    # Render the (selected) tab
    selected_tab = st.session_state.active_tab
    
    if selected_tab == 1:
        render_tab_alert()
    elif selected_tab == 2:
        render_tab_d3fend()
    elif selected_tab == 3:
        render_tab_inference()
    elif selected_tab == 4:
        render_tab_explanation()
    #elif selected_tab == 5:
    #    render_tab_acquisition()

def hide_sidebar_button():
    # CSS para esconder botão de minimizar da sidebar
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            width: 350px !important;
            min-width: 350px !important;
            max-width: 350px !important;
        }

        section[data-testid="stSidebar"] > div {
            width: 350px !important;
            min-width: 350px !important;
            max-width: 350px !important;
        }

        button[kind="header"] {
            display: none !important;
        }

        [data-testid="collapsedControl"] {
            display: none !important;
        }

        [data-testid="stSidebarCollapseButton"] {
            display: none !important;
        }
    </style>
    """,unsafe_allow_html=True)

if __name__ == "__main__":
    main()
