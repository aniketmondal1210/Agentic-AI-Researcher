"""
Semantic Scholar Tool — searches Semantic Scholar for papers with citation metrics.
Free API, no key required.
"""

import requests
from langchain_core.tools import tool


@tool
def semantic_scholar_search(query: str, max_results: int = 5) -> str:
    """Search Semantic Scholar for academic papers with citation counts and impact metrics.

    Args:
        query: The search query for finding relevant papers
        max_results: Maximum number of results to return (default 5)

    Returns:
        Formatted results with titles, authors, citation counts, and abstracts
    """
    print(f"SEMANTIC SCHOLAR Agent called: {query}")
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,authors,abstract,citationCount,influentialCitationCount,year,url,openAccessPdf",
        }

        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        papers = data.get("data", [])
        if not papers:
            return f"No papers found on Semantic Scholar for: {query}"

        formatted = []
        for i, paper in enumerate(papers, 1):
            authors = ", ".join(
                a.get("name", "Unknown") for a in (paper.get("authors") or [])[:5]
            )
            if len(paper.get("authors") or []) > 5:
                authors += " et al."

            abstract = paper.get("abstract") or "No abstract available"
            if len(abstract) > 400:
                abstract = abstract[:400] + "..."

            pdf_url = ""
            if paper.get("openAccessPdf"):
                pdf_url = f"\nPDF: {paper['openAccessPdf'].get('url', 'N/A')}"

            formatted.append(
                f"**{i}. {paper.get('title', 'Untitled')}**\n"
                f"Authors: {authors}\n"
                f"Year: {paper.get('year', 'N/A')}\n"
                f"Citations: {paper.get('citationCount', 0)} "
                f"(Influential: {paper.get('influentialCitationCount', 0)})\n"
                f"Abstract: {abstract}\n"
                f"URL: {paper.get('url', 'N/A')}{pdf_url}\n"
            )

        header = f"Found {len(papers)} papers on Semantic Scholar for: '{query}'\n\n"
        return header + "\n---\n".join(formatted)

    except Exception as e:
        print(f"Semantic Scholar error: {str(e)}")
        return f"Error searching Semantic Scholar: {str(e)}"
