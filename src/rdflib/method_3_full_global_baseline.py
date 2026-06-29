from pathlib import Path
from typing import Any

import json
import shutil
import streamlit as st

from src.state import get_step_state_filename_fullpath


SUBGRAPH_TEMPLATE_PATH = Path(
    "data/templates/modular_knowledge_graph_methods.json"
)

METHOD_ID = "method_3_full_global_baseline"


def load_json_template(template_path: Path) -> dict[str, Any]:
    """
    Load a JSON template from disk.
    """
    if not template_path.is_file():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    with template_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_config_value(method_config: dict[str, Any], field_name: str) -> Any:
    """
    Get the value of a configuration field from the method config.
    """
    return method_config["config"][field_name]["value"]


def create_full_global_baseline_subgraph() -> bool:
    """
    Create Step 2.4 output using Method 3: Full Global Baseline.

    This method performs no modularization or filtering. It copies the full
    knowledge graph from Step 2.3 unchanged to the Step 2.4 output.

    Returns:
        True if the output file was created successfully; otherwise False.
    """

    input_step_id = "2.3"
    output_step_id = "2.4"

    input_file_path = Path(get_step_state_filename_fullpath(input_step_id))
    output_file_path = Path(get_step_state_filename_fullpath(output_step_id))

    try:
        if not input_file_path.is_file():
            st.error(f"Full knowledge graph file not found: {input_file_path}")
            return False

        template = load_json_template(SUBGRAPH_TEMPLATE_PATH)
        methods = template.get("methods", {})

        if METHOD_ID not in methods:
            st.error(f"Method not found in template: {METHOD_ID}")
            return False

        method_config = methods[METHOD_ID]

        copy_full_graph = bool(
            get_config_value(method_config, "copy_full_graph")
        )

        if not copy_full_graph:
            st.error("Method 3 is configured not to copy the full graph.")
            return False

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copyfile(
            src=input_file_path,
            dst=output_file_path,
        )

        return output_file_path.is_file()

    except Exception as error:
        st.error(f"Error creating Method 3 full global baseline: {error}")
        return False