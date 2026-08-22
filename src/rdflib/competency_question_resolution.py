import json
from pathlib import Path
from typing import Any, Dict, List

from rdflib import Graph

from src.state import get_step_state_filename_fullpath, get_step_state_filename

def resolve_competency_questions(template_path: Path) -> bool:
    """
    Executes enabled competency questions over the materialized knowledge base.

    Input:
        state/tag_3_2_materialized_kb.owl
        data/templates/competency_questions_template.json
        data/templates/sparql/*.sparql

    Output:
        state/tag_4_1_competency_question_results.json

    Returns:
        True if the result artifact was generated successfully.
        False otherwise.
    """

    input_step_id = "3.2"
    output_step_id = "4.1"
    source_kb_path = Path(get_step_state_filename_fullpath(input_step_id))
    source_kb_filename = get_step_state_filename(input_step_id)
    output_path = Path(get_step_state_filename_fullpath(output_step_id))

    try:
        if not source_kb_path.exists():
            print(f"Source knowledge base file not found: {source_kb_path}")
            return False

        if not template_path.exists():
            print(f"Competency questions template not found: {template_path}")
            return False

        with open(template_path, "r", encoding="utf-8") as file:
            template_data = json.load(file)

        graph = Graph()
        graph.parse(source_kb_path)

        result_artifact: Dict[str, Any] = {
            "source_kb_file": source_kb_filename,
            "questions": {}
        }

        questions = template_data.get("questions", {})

        for question_id, question_data in questions.items():
            if not question_data.get("enabled", False):
                continue

            sparql_file = question_data.get("sparql_file", "")
            sparql_path = Path(sparql_file)

            question_result: Dict[str, Any] = {
                "name": question_data.get("name", ""),
                "question": question_data.get("question", ""),
                "explanation_role": question_data.get("explanation_role", ""),
                "expected_result_role": question_data.get("expected_result_role", ""),
                "sparql": "",
                "status": "error",
                "result_count": 0,
                "results": []
            }

            if not sparql_path.exists():
                question_result["error_message"] = f"SPARQL file not found: {sparql_path}"
                result_artifact["questions"][question_id] = question_result
                continue

            try:
                with open(sparql_path, "r", encoding="utf-8") as file:
                    sparql_query = file.read()

                question_result["sparql"] = sparql_query

                query_results = graph.query(sparql_query)
                bindings = _convert_query_results_to_dicts(query_results)

                question_result["results"] = bindings
                question_result["result_count"] = len(bindings)
                question_result["status"] = "success" if bindings else "empty"

            except Exception as query_error:
                question_result["status"] = "error"
                question_result["error_message"] = str(query_error)

            result_artifact["questions"][question_id] = question_result

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(result_artifact, file, indent=4, ensure_ascii=False)

        return True

    except Exception as error:
        print(f"Error while resolving competency questions: {error}")
        return False


def _convert_query_results_to_dicts(query_results: Any) -> List[Dict[str, str]]:
    """
    Converts RDFLib SPARQL query results into a JSON-serializable list of dictionaries.
    """

    rows: List[Dict[str, str]] = []

    for row in query_results:
        row_dict: Dict[str, str] = {}

        for variable in query_results.vars:
            value = row.get(variable)

            if value is None:
                row_dict[str(variable)] = ""
            else:
                row_dict[str(variable)] = str(value)

        rows.append(row_dict)

    return rows