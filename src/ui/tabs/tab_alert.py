"""
Tab 1: Wazuh Alert.
"""
import streamlit as st
import json
from typing import Any
from pathlib import Path
from pipeline_config import PIPELINE
from src.ui.tabs.tab_helper import render_tab_checklist
from src.state import get_step_state_filename_fullpath, save_dict_to_json_file, delete_file_if_exists, load_json_from_file, is_step_completed
from src.rdflib.convert_alert_to_rdf import convert_parsed_alert_to_rdf
from src.view_graph.rdf_graph_viewer import render_rdf_graph_iframe_from_rdf


def render_tab_alert():
    """
    Render Tab: Alert (Stage 1)
    """
    #######################################################
    #Tab header and tab checklist
    stage = "1"

    #Tab header
    stage_header = PIPELINE[stage]["name"]
    st.header(f"Stage {stage}: {stage_header}")    
    
    #Tab checklist
    checklist_placeholder = st.empty()
    
    st.divider()
    ######################################################
    # Step 1.1 - Upload alerta
    step = "1.1"
    step_name = PIPELINE[stage]["steps"][step]["name"]
    st.subheader(f"Step {step}: {step_name}", help=PIPELINE[stage]["steps"][step]["help"])

    #Check if step is already completed based on file -> state
    if is_step_completed(step):
        st.session_state.json_loaded = True
    
    # Uploader button
    uploaded_file = st.file_uploader("Upload Wazuh alert (JSON)", type=["json"], accept_multiple_files=False, help="Select a Wazuh alert JSON file")
    
    # Clear button
    if st.button("Clear parsed alert",
        disabled=not st.session_state.get("json_loaded", False),
        width="stretch"
    ):
        clear_upload_alert_state(get_step_state_filename_fullpath(step))
        st.rerun()

    # Process uploaded file
    if uploaded_file is not None:
        try:
            uploaded_json = json.load(uploaded_file)

            template_path = Path("data/templates/alert_fields_to_parse.json")
            with template_path.open("r", encoding="utf-8") as file:
                parse_template = json.load(file)
            
            parsed_alert = parse_wazuh_single_alert(alert_data=uploaded_json,parse_template=parse_template)

            is_valid, missing_fields = validate_parsed_alert(parsed_alert, parse_template)

            if not is_valid:
                st.session_state.json_loaded = False
                st.session_state.uploaded_json = None
                st.session_state.parsed_alert = None

                st.error("Parsed alert is incomplete.")
                st.warning(f"Missing or empty fields: {', '.join(missing_fields)}")

            else:
                st.session_state.uploaded_json = uploaded_json
                st.session_state.parsed_alert = parsed_alert
                st.session_state.json_loaded = True

                save_dict_to_json_file(parsed_alert, get_step_state_filename_fullpath(step))

                st.success("JSON file loaded and parsed successfully!")

        except Exception as error:
            st.session_state.json_loaded = False
            st.session_state.uploaded_json = None
            st.session_state.parsed_alert = None

            st.error(f"Error loading JSON file: {error}")

    else:
        saved_parsed_alert = load_json_from_file(get_step_state_filename_fullpath(step))

        if saved_parsed_alert is not None:
            st.session_state.parsed_alert = saved_parsed_alert
            st.session_state.json_loaded = True

        elif "json_loaded" not in st.session_state:
            st.session_state.json_loaded = False
            st.session_state.uploaded_json = None
            st.session_state.parsed_alert = None

    # Show parsed alert info if loaded
    json_loaded = st.session_state.get("json_loaded", False)
    parsed_alert = st.session_state.get("parsed_alert")

    if json_loaded and parsed_alert is not None:
        st.info("A parsed alert is currently loaded.")
        template_path = Path("data/templates/alert_fields_to_parse.json")
        with template_path.open("r", encoding="utf-8") as file:
            parse_template = json.load(file)
        render_parsed_alert_fields(parsed_alert, parse_template)
    
    #Button to view JSON content, disabled if JSON is not loaded
    if st.button("View JSON content",disabled=not st.session_state.get("uploaded_json", None),width="stretch"):
        show_json_dialog() 
    
    st.divider()
    ######################################################
    # Step 1.2 - Convert alert to RDF
    step = "1.2"
    step_name = PIPELINE[stage]["steps"][step]["name"]
    st.subheader(f"Step {step}: {step_name}", help=PIPELINE[stage]["steps"][step]["help"])

    #Check if step is already completed based on file -> state
    if is_step_completed(step):
        st.session_state.rdf_converted = True

    # Convert parsed alert to RDF button
    if st.button("Convert parsed alert to RDF",
    disabled=not st.session_state.get("json_loaded", False),
    width="stretch"
    ):
        rdf_convert_success = convert_parsed_alert_to_rdf()

        if rdf_convert_success:
            st.success("Parsed alert converted to RDF/XML successfully.")
            st.session_state.rdf_converted = True
        else:
            st.error("Could not convert parsed alert to RDF/XML.")

    ## View RDF content button
    if st.button(
        "View RDF content",
        disabled=not st.session_state.get("rdf_converted", False),
        width="stretch"
    ):
        rdf_file_path = get_step_state_filename_fullpath("1.2")
        rdf_graph_html_path = "state/tag_1_2_rdf_graph.html"
        render_rdf_graph_iframe_from_rdf(
                rdf_file_path=rdf_file_path,
                html_file_path=rdf_graph_html_path,
                height=850
            )

    # Clear button
    if st.button("Clear converted RDF",
        disabled=not st.session_state.get("rdf_converted", False),
        width="stretch"
    ):
        clear_converted_rdf_state(get_step_state_filename_fullpath(step))
        st.rerun()

    # Render checklist container after running validation logic
    with checklist_placeholder.container():
        render_tab_checklist(stage)


@st.dialog("JSON content")
def show_json_dialog():
    """
    Show the uploaded JSON content in a modal dialog.
    """
    st.json(st.session_state.uploaded_json)


def parse_wazuh_single_alert(
    alert_data: dict[str, Any],
    parse_template: dict[str, Any],
) -> dict[str, Any]:
    """
    Parse a single Wazuh alert JSON using a field mapping template.

    The template must contain groups where:
        - left side is the canonical/display field name used by the system
        - right side is the field path in the original Wazuh alert JSON
    """

    parsed_alert: dict[str, Any] = {}

    groups = parse_template.get("groups", {})

    for group_name, fields in groups.items():
        if not isinstance(fields, dict):
            continue

        for field_name, source_path in fields.items():
            parsed_alert[field_name] = get_nested_value(
                data=alert_data,
                path=source_path,
                default=None,
            )

    return parsed_alert


def get_nested_value(data: dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Get a nested value from a dictionary using dot notation.

    Example:
        path = "rule.mitre.id"
        returns data["rule"]["mitre"]["id"]
    """
    current_value: Any = data

    for key in path.split("."):
        if not isinstance(current_value, dict):
            return default

        current_value = current_value.get(key)

        if current_value is None:
            return default

    return current_value
    

def format_parsed_value(value: Any) -> str:
    """
    Format parsed values for UI display.
    """
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(str(item) for item in value)

    if isinstance(value, dict):
        return str(value)

    return str(value)


def render_parsed_alert_fields(
    parsed_alert: dict[str, Any],
    parse_template: dict[str, Any],
) -> None:
    """
    Render parsed Wazuh alert fields using the groups defined in the parse template.
    """

    st.subheader("Parsed alert fields")

    groups = parse_template.get("groups", {})

    for group_name, fields in groups.items():
        if not isinstance(fields, dict):
            continue

        st.markdown(f"### {group_name}")

        field_names = list(fields.keys())

        for index in range(0, len(field_names), 3):
            columns = st.columns(3)

            for column, field_name in zip(columns, field_names[index:index + 3]):
                with column:
                    value = parsed_alert.get(field_name)

                    st.text_input(
                        field_name,
                        value=format_parsed_value(value),
                        disabled=True,
                        key=f"parsed_alert_{group_name}_{field_name}",
                    )


def is_valid_value(value: Any) -> bool:
    """
    Check whether a parsed value is not empty.
    """
    if value is None:
        return False

    if isinstance(value, str) and value.strip() == "":
        return False

    if isinstance(value, list) and len(value) == 0:
        return False

    return True


def get_required_fields_from_parse_template(
    parse_template: dict[str, Any],
) -> list[str]:
    """
    Extract required field names from the alert parsing template.

    All fields listed in the template are considered required.
    """
    required_fields: list[str] = []

    groups = parse_template.get("groups", {})

    for group_name, fields in groups.items():
        if not isinstance(fields, dict):
            continue

        required_fields.extend(fields.keys())

    return required_fields


def validate_parsed_alert(
    parsed_alert: dict[str, Any],
    parse_template: dict[str, Any],
) -> tuple[bool, list[str]]:
    """
    Validate whether all fields defined in the parsing template
    are present and not empty in the parsed alert.

    Returns:
        tuple:
            - True/False validation result.
            - List of missing or empty fields.
    """
    missing_fields: list[str] = []

    required_fields = get_required_fields_from_parse_template(parse_template)

    for field_name in required_fields:
        field_value = parsed_alert.get(field_name)

        if not is_valid_value(field_value):
            missing_fields.append(field_name)

    is_valid = len(missing_fields) == 0

    return is_valid, missing_fields


def clear_upload_alert_state(file_path: str | Path) -> None:
    """
    Clear alert state and delete the saved parsed alert file.
    """
    delete_file_if_exists(file_path)

    st.session_state.json_loaded = False
    st.session_state.uploaded_json = None
    st.session_state.parsed_alert = None


def clear_converted_rdf_state(file_path: str | Path) -> None:
    """
    Clear RDF conversion state and delete the saved RDF file.
    """
    delete_file_if_exists(file_path)
    delete_file_if_exists("state/tag_1_2_rdf_graph.html")
    st.session_state.rdf_converted = False


@st.dialog("RDF/Turtle content")
def show_rdf_dialog():
    """
    Show the generated RDF/Turtle content in a modal dialog.
    """
    ttl_file_path = get_step_state_filename_fullpath("1.2")

    render_rdf_graph_from_ttl(ttl_file_path)