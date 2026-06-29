from pathlib import Path
from rdflib import Graph

filename_fullpath = Path("state") / "tag_3_1_dl_consistent_kb.owl"

if not filename_fullpath.is_file():
    raise FileNotFoundError(f"File not found: {filename_fullpath}")

graph = Graph()
graph.parse(str(filename_fullpath))

print(f"Triples in Step 3.1 file: {len(graph)}")