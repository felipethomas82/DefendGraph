"""
Tab 4: Explanation (Stage 4)
"""
import streamlit as st
from streamlit_mermaid import st_mermaid
import json
import html
import hashlib
import streamlit.components.v1 as components
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

    # Render mmd mermaid file
    if st.session_state.get("path_graph_created", False):
        mmd_path = get_step_state_filename_fullpath(step)

        with open(mmd_path, "r", encoding="utf-8") as f:
            mermaid_code = f.read()

        render_mermaid_pan_zoom(
            mermaid_code=mermaid_code,
            container_height=650,
            component_height=680,
            initial_zoom=3,
        )

    # Clear button
    if st.button(
        "Clear path graph visualization",
        disabled=not st.session_state.get("path_graph_created", False),
        width="stretch",
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

def render_mermaid_pan_zoom(
    mermaid_code: str,
    container_height: int = 650,
    component_height: int = 680,
    initial_zoom: float = 1.25,
) -> None:
    """
    Render a Mermaid graph with pan and zoom support.
    """

    mermaid_code_json = json.dumps(mermaid_code)
    component_id = hashlib.md5(mermaid_code.encode("utf-8")).hexdigest()[:10]

    graph_container_id = f"graph-container-{component_id}"
    graph_target_id = f"graph-target-{component_id}"
    graph_render_id = f"reasoning-path-graph-{component_id}"

    zoom_in_button_id = f"zoom-in-{component_id}"
    zoom_out_button_id = f"zoom-out-{component_id}"
    reset_button_id = f"reset-zoom-{component_id}"
    fit_button_id = f"fit-graph-{component_id}"

    graph_area_height = container_height - 50

    components.html(
        f"""
        <div style="
            width: 100%;
            height: {container_height}px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background-color: white;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        ">
            <div style="
                height: 42px;
                padding: 6px 10px;
                display: flex;
                gap: 8px;
                align-items: center;
                border-bottom: 1px solid #eee;
                background-color: #fafafa;
                flex-shrink: 0;
            ">
                <button id="{zoom_in_button_id}">+</button>
                <button id="{zoom_out_button_id}">-</button>
                <button id="{reset_button_id}">Reset</button>
                <button id="{fit_button_id}">Fit</button>

                <span style="font-size: 13px; color: #555;">
                    Use o scroll para zoom e arraste o grafo para navegar.
                </span>
            </div>

            <div id="{graph_container_id}" style="
                width: 100%;
                height: {graph_area_height}px;
                overflow: hidden;
                position: relative;
            ">
                <div id="{graph_target_id}" style="
                    width: 100%;
                    height: 100%;
                "></div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.2/dist/svg-pan-zoom.min.js"></script>

        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';

            const mermaidCode = {mermaid_code_json};

            mermaid.initialize({{
                startOnLoad: false,
                theme: 'default',
                securityLevel: 'loose',
                flowchart: {{
                    useMaxWidth: false,
                    htmlLabels: true,
                    nodeSpacing: 70,
                    rankSpacing: 100
                }}
            }});

            let panZoomInstance = null;

            async function renderGraph() {{
                const target = document.getElementById("{graph_target_id}");

                const rendered = await mermaid.render(
                    "{graph_render_id}",
                    mermaidCode
                );

                target.innerHTML = rendered.svg;

                const svg = target.querySelector("svg");

                if (!svg) {{
                    return;
                }}

                svg.removeAttribute("width");
                svg.removeAttribute("height");

                svg.style.width = "100%";
                svg.style.height = "100%";
                svg.style.maxWidth = "none";
                svg.style.display = "block";

                panZoomInstance = svgPanZoom(svg, {{
                    zoomEnabled: true,
                    panEnabled: true,
                    controlIconsEnabled: false,
                    fit: true,
                    center: true,
                    contain: false,
                    minZoom: 0.05,
                    maxZoom: 20,
                    zoomScaleSensitivity: 0.35
                }});

                setTimeout(() => {{
                    panZoomInstance.resize();
                    panZoomInstance.fit();
                    panZoomInstance.center();
                    panZoomInstance.zoomBy({initial_zoom});
                }}, 100);
            }}

            document.getElementById("{zoom_in_button_id}").onclick = function() {{
                if (panZoomInstance) {{
                    panZoomInstance.zoomIn();
                }}
            }};

            document.getElementById("{zoom_out_button_id}").onclick = function() {{
                if (panZoomInstance) {{
                    panZoomInstance.zoomOut();
                }}
            }};

            document.getElementById("{reset_button_id}").onclick = function() {{
                if (panZoomInstance) {{
                    panZoomInstance.resetZoom();
                    panZoomInstance.center();
                }}
            }};

            document.getElementById("{fit_button_id}").onclick = function() {{
                if (panZoomInstance) {{
                    panZoomInstance.resize();
                    panZoomInstance.fit();
                    panZoomInstance.center();
                }}
            }};

            renderGraph();
        </script>
        """,
        height=component_height,
        scrolling=False,
    )

