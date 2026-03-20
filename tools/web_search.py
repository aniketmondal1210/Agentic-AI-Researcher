"""
Web Search Tool — searches the web using DuckDuckGo (no API key needed).
"""

from langchain_core.tools import tool
from duckduckgo_search import DDGS


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for information on a given topic using DuckDuckGo.

    Args:
        query: The search query to look up on the web
        max_results: Maximum number of results to return (default 5)

    Returns:
        Formatted search results with titles, URLs, and snippets
    """
    print(f"WEB SEARCH Agent called: {query}")
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(r)

        if not results:
            return f"No web results found for: {query}"

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"**{i}. {r['title']}**\n"
                f"URL: {r['href']}\n"
                f"Snippet: {r['body']}\n"
            )

        header = f"Found {len(results)} web results for: '{query}'\n\n"
        return header + "\n---\n".join(formatted)

    except Exception as e:
        print(f"Web search error: {str(e)}")
        return f"Error performing web search: {str(e)}"
