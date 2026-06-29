"""
State (stage and steps)
based on files in the STATE_DIR
"""

from pathlib import Path
import json
import shutil
from typing import Dict, Any, Optional
from pipeline_config import PIPELINE

STATE_DIR = Path("state")

def is_step_completed(step_id: str) -> bool:
    """
    Input: step id.
    Output: True if the step's corresponding file exists.
    """
    step = get_step(step_id)

    if step is None:
        return False

    file_name = step.get("file")

    if not file_name:
        return False

    file_name_full_path = STATE_DIR / file_name

    return Path(file_name_full_path).exists()


def get_step(step_id: str) -> Optional[Dict[str, Any]]:
    """
    Input: step id, for example '1.1'.
    Output: step configuration or None.
    """
    for stage in PIPELINE.values():
        steps = stage["steps"]

        if step_id in steps:
            return steps[step_id]

    return None


def is_stage_completed(stage_id: str) -> bool:
    """
    Input: stage id.
    Output: True if all stage steps are completed; otherwise False.
    """
    stage = PIPELINE.get(stage_id)
    
    if stage is None:
        return False
    
    step_ids = list(stage["steps"].keys())
    results = [is_step_completed(step_id) for step_id in step_ids]
    
    return all(results)

def ensure_state_dir() -> None:
    """
    Input: none.
    Output: creates the state directory if it does not exist.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_stage(stage_id: str) -> Optional[Dict[str, Any]]:
    """
    Input: stage id, for example '1'.
    Output: stage configuration or None.
    """
    return PIPELINE.get(stage_id)


def get_step_file(step_id: str) -> Optional[Path]:
    """
    Input: step id.
    Output: full path of the step artifact file or None.
    """
    step = get_step(step_id)

    if step is None:
        return None

    return get_artifact_path(step["file"])


def get_stage_help(stage_id: str) -> str:
    """
    Input: stage id.
    Output: help text for the stage, or empty string.
    """
    stage = get_stage(stage_id)

    if stage is None:
        return ""

    return stage.get("help", "")


def get_step_help(step_id: str) -> str:
    """
    Input: step id.
    Output: help text for the step, or empty string.
    """
    step = get_step(step_id)

    if step is None:
        return ""

    return step.get("help", "")


def is_valid_file(path: Path, file_type: str) -> bool:
    """
    Input: file path and expected file type.
    Output: True if the file exists, is not empty, and is valid.
    """
    if not path.exists():
        return False

    if path.stat().st_size == 0:
        return False

    if file_type == "json":
        try:
            with path.open("r", encoding="utf-8") as file:
                json.load(file)
            return True
        except Exception:
            return False

    return True


def get_step_status(step_id: str) -> str:
    """
    Input: step id.
    Output: 'completed' or 'pending'.
    """
    if is_step_completed(step_id):
        return "completed"

    return "pending"


def get_stage_status(stage_id: str) -> str:
    """
    Input: stage id.
    Output: 'completed', 'in_progress', or 'pending'.
    """
    stage = PIPELINE.get(stage_id)

    if stage is None:
        return "pending"

    step_ids = list(stage["steps"].keys())
    results = [is_step_completed(step_id) for step_id in step_ids]

    if all(results):
        return "completed"

    if any(results):
        return "in_progress"

    return "pending"


def get_stage_checklist(stage_id: str) -> Dict[str, bool]:
    """
    Input: stage id.
    Output: dictionary with step names and completion status.
    """
    stage = PIPELINE.get(stage_id)

    if stage is None:
        return {}

    checklist = {}

    for step_id, step in stage["steps"].items():
        name = f"{step_id} {step['name']}"
        checklist[name] = is_step_completed(step_id)

    return checklist


def is_stage_unlocked(stage_id: str) -> bool:
    """
    Input: stage id.
    Output: True if the stage can be accessed.
    """
    if stage_id == "1":
        return True

    try:
        previous_stage_id = str(int(stage_id) - 1)
    except ValueError:
        return False

    return get_stage_status(previous_stage_id) == "completed"


def is_step_unlocked(step_id: str) -> bool:
    """
    Input: step id.
    Output: True if the step can be executed.
    """
    try:
        stage_id, step_number = step_id.split(".")
        step_number = int(step_number)
    except ValueError:
        return False

    if not is_stage_unlocked(stage_id):
        return False

    if step_number == 1:
        return True

    previous_step_id = f"{stage_id}.{step_number - 1}"

    return is_step_completed(previous_step_id)


def reset_state() -> None:
    """
    Input: none.
    Output: removes and recreates the whole state directory.
    """
    if STATE_DIR.exists():
        shutil.rmtree(STATE_DIR)

    STATE_DIR.mkdir(parents=True, exist_ok=True)


def reset_step(step_id: str) -> None:
    """
    Input: step id.
    Output: removes the artifact file associated with the step.
    """
    path = get_step_file(step_id)

    if path is not None and path.exists():
        path.unlink()


def reset_stage(stage_id: str) -> None:
    """
    Input: stage id.
    Output: removes all artifact files associated with the stage.
    """
    stage = PIPELINE.get(stage_id)

    if stage is None:
        return

    for step_id in stage["steps"].keys():
        reset_step(step_id)


def get_step_state_filename_fullpath(step_id: str) -> str:
    """
    Input: step id
    Output: filename_fullpath
    """
    step = get_step(step_id)

    if step is None:
        return False

    file_name = step.get("file")

    if not file_name:
        return False

    file_name_full_path = STATE_DIR / file_name

    return file_name_full_path


def get_step_state_filename(step_id: str) -> str:
    """
    Input: step id
    Output: filename_fullpath
    """
    step = get_step(step_id)

    if step is None:
        return False

    file_name = step.get("file")

    if not file_name:
        return False

    return file_name

def save_dict_to_json_file(data: dict, file_path: Path) -> None:
    """
    Save dictionary data as a JSON file.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def delete_file_if_exists(file_path: str | Path) -> None:
    """
    Delete a file if it exists.
    """
    file_path = Path(file_path)

    if file_path.is_file():
        file_path.unlink()


def delete_all_state_files() -> None:
    """
    Delete all files in the state dir.

    If the state dir exists, delete all files inside it.

    Returns:
        None
    """
    state_dir = STATE_DIR

    if state_dir.exists():
        for file_path in state_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()

def load_json_from_file(file_path: str | Path) -> dict | None:
    """
    Load JSON data from a file if it exists.
    """
    file_path = Path(file_path)

    if not file_path.is_file():
        return None

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)

def read_owl_file(file_path: str) -> str:
    """
    Read a OWL file and return its full content as a string.
    """
    file_path = Path(file_path)

    if not file_path.is_file():
        return None

    return file_path.read_text(encoding="utf-8")


def write_owl_file(output_owl_path: str, owl_content: str) -> None:
    """
    Write OWL content to a new OWL file.
    """
    output_path = Path(output_owl_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(owl_content, encoding="utf-8")