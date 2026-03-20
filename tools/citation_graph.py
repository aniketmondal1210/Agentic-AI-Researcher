"""
Citation Graph — fetches citation relationships and builds an interactive network graph.
Uses Semantic Scholar API (free, no key needed).
"""

import requests
import json
from pathlib import Path


def search_paper_id(title: str) -> dict | None:
    """Search Semantic Scholar for a paper by title, return its ID and metadata."""
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": title,
            "limit": 1,
            "fields": "title,citationCount,year,authors,paperId",
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        papers = data.get("data", [])
        if papers:
            return papers[0]
    except Exception as e:
        print(f"Error searching for paper '{title}': {e}")
    return None


def get_citations_and_references(paper_id: str, limit: int = 5) -> dict:
    """Get citations and references for a paper from Semantic Scholar."""
    result = {"citations": [], "references": []}
    try:
        # Get citations (papers that cite this paper)
        url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations"
        params = {"fields": "title,citationCount,year,authors,paperId", "limit": limit}
        resp = requests.get(url, params=params, timeout=10)
        if resp.ok:
            for item in resp.json().get("data", []):
                if item.get("citingPaper"):
                    result["citations"].append(item["citingPaper"])

        # Get references (papers this paper cites)
        url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/references"
        resp = requests.get(url, params=params, timeout=10)
        if resp.ok:
            for item in resp.json().get("data", []):
                if item.get("citedPaper"):
                    result["references"].append(item["citedPaper"])
    except Exception as e:
        print(f"Error fetching citations for {paper_id}: {e}")

    return result


def build_citation_graph_html(paper_titles: list[str], height: str = "600px") -> str:
    """Build an interactive citation network graph as HTML.

    Args:
        paper_titles: List of paper titles to build the graph around
        height: Height of the graph visualization

    Returns:
        HTML string containing the interactive pyvis graph
    """
    from pyvis.network import Network

    net = Network(
        height=height,
        width="100%",
        bgcolor="#1a1a2e",
        font_color="#e0e0ff",
        directed=True,
    )

    # Physics settings for better layout
    net.set_options(json.dumps({
        "physics": {
            "barnesHut": {
                "gravitationalConstant": -3000,
                "centralGravity": 0.3,
                "springLength": 150,
                "springConstant": 0.04,
            },
            "maxVelocity": 50,
            "minVelocity": 0.1,
        },
        "nodes": {
            "font": {"size": 12, "color": "#e0e0ff"},
            "borderWidth": 2,
        },
        "edges": {
            "color": {"color": "#6c5ce7", "highlight": "#a29bfe"},
            "arrows": {"to": {"enabled": True, "scaleFactor": 0.5}},
            "smooth": {"type": "curvedCW", "roundness": 0.2},
        },
        "interaction": {
            "hover": True,
            "tooltipDelay": 200,
        },
    }))

    added_nodes = set()

    for title in paper_titles:
        # Search for the paper
        paper = search_paper_id(title)
        if not paper:
            continue

        paper_id = paper["paperId"]
        paper_title = paper.get("title", title)[:60]
        citations = paper.get("citationCount", 0)
        year = paper.get("year", "N/A")

        # Add main paper node (larger, highlighted)
        if paper_id not in added_nodes:
            node_size = min(30 + citations * 0.5, 60)
            net.add_node(
                paper_id,
                label=paper_title,
                title=f"{paper.get('title', title)}\nYear: {year}\nCitations: {citations}",
                color="#e74c3c",
                size=node_size,
                shape="dot",
            )
            added_nodes.add(paper_id)

        # Get citations and references
        graph_data = get_citations_and_references(paper_id, limit=5)

        # Add citation nodes (papers that cite this one)
        for citing in graph_data["citations"]:
            cid = citing.get("paperId")
            if not cid or cid in added_nodes:
                continue
            ctitle = (citing.get("title") or "Unknown")[:50]
            ccitations = citing.get("citationCount", 0)
            cyear = citing.get("year", "N/A")
            csize = min(15 + ccitations * 0.3, 40)

            net.add_node(
                cid,
                label=ctitle,
                title=f"{citing.get('title', 'Unknown')}\nYear: {cyear}\nCitations: {ccitations}",
                color="#00b894",
                size=csize,
                shape="dot",
            )
            added_nodes.add(cid)
            net.add_edge(cid, paper_id)  # citing -> cited

        # Add reference nodes (papers this one cites)
        for ref in graph_data["references"]:
            rid = ref.get("paperId")
            if not rid or rid in added_nodes:
                continue
            rtitle = (ref.get("title") or "Unknown")[:50]
            rcitations = ref.get("citationCount", 0)
            ryear = ref.get("year", "N/A")
            rsize = min(15 + rcitations * 0.3, 40)

            net.add_node(
                rid,
                label=rtitle,
                title=f"{ref.get('title', 'Unknown')}\nYear: {ryear}\nCitations: {rcitations}",
                color="#6c5ce7",
                size=rsize,
                shape="dot",
            )
            added_nodes.add(rid)
            net.add_edge(paper_id, rid)  # paper -> reference

    # Generate HTML
    html = net.generate_html()
    return html
