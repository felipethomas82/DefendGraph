from pathlib import Path
import hashlib
import json

import streamlit as st

from rdflib import Graph, Literal


def render_rdf_graph_iframe_from_rdf(
    rdf_file_path: str | Path,
    html_file_path: str | Path,
    height: int = 850
) -> bool:
    """
    Create a standalone Cytoscape.js HTML file from an RDF/XML file
    and render it using st.iframe.

    Input:
        rdf_file_path: full path to the RDF/XML file.
        html_file_path: full path where the HTML graph file will be saved.
        height: iframe height in pixels.

    Output:
        True if the graph was rendered successfully; otherwise False.
    """
    rdf_file_path = Path(rdf_file_path)
    html_file_path = Path(html_file_path)

    if not rdf_file_path.is_file():
        st.warning(f"RDF/XML file not found: {rdf_file_path}")
        return False

    try:
        elements = rdf_to_cytoscape_elements(rdf_file_path)

        if not elements:
            st.warning("No RDF triples found in the RDF file.")
            return False

        html_content = build_cytoscape_html(elements)

        html_file_path.parent.mkdir(parents=True, exist_ok=True)
        html_file_path.write_text(html_content, encoding="utf-8")

        st.iframe(
            html_file_path,
            width="stretch",
            height=height
        )

        return True

    except Exception as error:
        st.error(f"Error rendering RDF graph: {error}")
        return False


def rdf_to_cytoscape_elements(rdf_file_path: str | Path) -> list[dict]:
    """
    Convert a RDF/XML file into Cytoscape.js elements.
    """
    rdf_file_path = Path(rdf_file_path)

    graph = Graph()
    graph.parse(str(rdf_file_path), format="xml")

    elements = []
    created_nodes = set()
    created_edges = set()

    for subject, predicate, object_value in graph:
        subject_id = get_safe_node_id(subject)
        object_id = get_safe_node_id(object_value)
        predicate_id = get_safe_node_id(predicate)

        if subject_id not in created_nodes:
            elements.append({
                "data": {
                    "id": subject_id,
                    "label": get_short_rdf_label(subject),
                    "type": "uri"
                }
            })
            created_nodes.add(subject_id)

        if object_id not in created_nodes:
            node_type = "literal" if isinstance(object_value, Literal) else "uri"

            elements.append({
                "data": {
                    "id": object_id,
                    "label": get_short_rdf_label(object_value),
                    "type": node_type
                }
            })
            created_nodes.add(object_id)

        edge_id = f"edge_{subject_id}_{predicate_id}_{object_id}"

        if edge_id not in created_edges:
            elements.append({
                "data": {
                    "id": edge_id,
                    "source": subject_id,
                    "target": object_id,
                    "label": get_short_rdf_label(predicate)
                }
            })
            created_edges.add(edge_id)

    return elements


def get_short_rdf_label(value) -> str:
    """
    Return a short readable label for an RDF URI or literal.
    """
    value_str = str(value)

    if "#" in value_str:
        return value_str.split("#")[-1]

    if "/" in value_str:
        return value_str.rstrip("/").split("/")[-1]

    if len(value_str) > 80:
        return value_str[:77] + "..."

    return value_str


def get_safe_node_id(value) -> str:
    """
    Return a stable safe node ID for Cytoscape.js.
    """
    value_str = str(value)
    hash_value = hashlib.md5(value_str.encode("utf-8")).hexdigest()

    return f"node_{hash_value}"


def build_cytoscape_html(elements: list[dict]) -> str:
    """
    Build a standalone HTML page with Cytoscape.js graph visualization.
    """
    elements_json = json.dumps(elements, ensure_ascii=False)

    html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>RDF graph</title>

    <script src="https://unpkg.com/cytoscape@3.29.2/dist/cytoscape.min.js"></script>

    <style>
        html, body {
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            overflow: hidden;
            background: #fafafa;
        }

        #header {
            height: 52px;
            padding: 14px 20px;
            box-sizing: border-box;
            border-bottom: 1px solid #ddd;
            background: #ffffff;
            font-size: 16px;
            font-weight: 600;
        }

        #cy {
            width: 100%;
            height: calc(100vh - 52px);
            background: #fafafa;
        }
    </style>
</head>

<body>
    <div id="header">RDF/XML graph visualization</div>
    <div id="cy"></div>

    <script>
        const elements = __ELEMENTS__;

        const cy = cytoscape({
            container: document.getElementById("cy"),
            elements: elements,

            style: [
                {
                    selector: "node",
                    style: {
                        "label": "data(label)",
                        "text-wrap": "wrap",
                        "text-max-width": "120px",
                        "font-size": "10px",
                        "text-valign": "center",
                        "text-halign": "center",
                        "background-color": "#4f81bd",
                        "color": "#222",
                        "width": "58px",
                        "height": "58px"
                    }
                },
                {
                    selector: 'node[type = "literal"]',
                    style: {
                        "background-color": "#f4b183",
                        "shape": "round-rectangle",
                        "width": "120px",
                        "height": "44px"
                    }
                },
                {
                    selector: "edge",
                    style: {
                        "label": "data(label)",
                        "font-size": "8px",
                        "curve-style": "bezier",
                        "target-arrow-shape": "triangle",
                        "target-arrow-color": "#999",
                        "line-color": "#999",
                        "width": 1.5,
                        "text-rotation": "autorotate",
                        "text-margin-y": "-8px"
                    }
                }
            ],

            layout: {
                name: "cose",
                animate: false,
                padding: 80,
                nodeRepulsion: 12000,
                idealEdgeLength: 150,
                edgeElasticity: 100
            }
        });

        cy.fit();

        window.addEventListener("resize", function() {
            cy.resize();
            cy.fit();
        });
    </script>
</body>
</html>
"""

    return html_template.replace("__ELEMENTS__", elements_json)