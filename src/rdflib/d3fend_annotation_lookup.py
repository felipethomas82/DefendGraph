from pathlib import Path

from rdflib import Graph, Literal, URIRef


def load_ontology_graph(ontology_file_path: Path) -> Graph:
    """
    Load an OWL/RDF ontology file into an rdflib graph.
    """
    graph = Graph()
    graph.parse(str(ontology_file_path))
    return graph


def normalize_literal(value: str) -> str:
    """
    Normalize literal values for comparison.
    """
    return str(value).strip().lower()


def find_subjects_by_literal_value(
    graph: Graph,
    literal_value: str,
) -> list[URIRef]:
    """
    Find ontology subjects that have any literal annotation exactly matching
    the provided value.

    Example:
        literal_value = "T1110.001"
    """
    matched_subjects: list[URIRef] = []
    expected_value = normalize_literal(literal_value)

    for subject, predicate, object_value in graph.triples((None, None, None)):
        if not isinstance(subject, URIRef):
            continue

        if not isinstance(object_value, Literal):
            continue

        if normalize_literal(str(object_value)) == expected_value:
            matched_subjects.append(subject)

    return list(dict.fromkeys(matched_subjects))


def find_first_subject_by_literal_value(
    graph: Graph,
    literal_value: str,
) -> URIRef | None:
    """
    Find the first ontology subject that has a literal annotation matching
    the provided value.
    """
    matched_subjects = find_subjects_by_literal_value(graph, literal_value)

    if not matched_subjects:
        return None

    return matched_subjects[0]