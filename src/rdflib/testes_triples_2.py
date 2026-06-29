from pathlib import Path
from rdflib import Graph
from owlrl import DeductiveClosure, OWLRL_Semantics

input_path = Path("state") / "tag_2_3_full_knowledge_graph.owl"

graph = Graph()
graph.parse(str(input_path))

before = len(graph)

DeductiveClosure(OWLRL_Semantics).expand(graph)

after = len(graph)

print(f"Before OWL-RL: {before}")
print(f"After OWL-RL: {after}")
print(f"New triples: {after - before}")