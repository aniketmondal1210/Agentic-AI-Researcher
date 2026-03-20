# Step1: Access arXiv using URL
import requests


def search_arxiv_papers(topic: str, max_results: int = 5) -> dict:
    """Search arXiv API for papers on the given topic."""
    query = "+".join(topic.lower().split())
    # Remove invalid characters from query (arXiv API doesn't accept these)
    for char in ['"', "'", '(', ')', '{', '}', '[', ']']:
        query = query.replace(char, "")

    url = (
        "http://export.arxiv.org/api/query"
        f"?search_query=all:{query}"
        f"&max_results={max_results}"
        "&sortBy=submittedDate"
        "&sortOrder=descending"
    )
    print(f"Making request to arXiv API: {url}")
    resp = requests.get(url)

    if not resp.ok:
        print(f"ArXiv API request failed: {resp.status_code} - {resp.text}")
        raise ValueError(f"Bad response from arXiv API: {resp}\n{resp.text}")

    data = parse_arxiv_xml(resp.text)
    return data


# Step2: Parse XML
import xml.etree.ElementTree as ET


def parse_arxiv_xml(xml_content: str) -> dict:
    """Parse the XML content from arXiv API response."""
    entries = []
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    root = ET.fromstring(xml_content)

    for entry in root.findall("atom:entry", ns):
        # Extract authors
        authors = [
            author.findtext("atom:name", namespaces=ns)
            for author in entry.findall("atom:author", ns)
        ]
        # Extract categories
        categories = [
            cat.attrib.get("term")
            for cat in entry.findall("atom:category", ns)
        ]
        # Extract PDF link
        pdf_link = None
        for link in entry.findall("atom:link", ns):
            if link.attrib.get("type") == "application/pdf":
                pdf_link = link.attrib.get("href")
                break

        summary_text = entry.findtext("atom:summary", namespaces=ns)
        entries.append(
            {
                "title": (entry.findtext("atom:title", namespaces=ns) or "Untitled").strip(),
                "summary": (summary_text or "No summary available").strip(),
                "authors": authors,
                "categories": categories,
                "pdf": pdf_link,
            }
        )

    return {"entries": entries}


# Step3: Convert into a LangChain tool
from langchain_core.tools import tool


@tool
def arxiv_search(topic: str) -> list[dict]:
    """Search for recently uploaded arXiv papers.

    Args:
        topic: The topic to search for papers about

    Returns:
        List of papers with their metadata including title, authors, summary, etc.
    """
    print("ARXIV Agent called")
    print(f"Searching arXiv for papers about: {topic}")
    try:
        papers = search_arxiv_papers(topic)
        entries = papers.get("entries", [])
        if len(entries) == 0:
            return {"entries": [], "message": f"No papers found for topic: {topic}"}
        print(f"Found {len(entries)} papers about {topic}")
        return papers
    except Exception as e:
        print(f"arXiv search error: {str(e)}")
        return {"entries": [], "message": f"Error searching arXiv: {str(e)}"}
