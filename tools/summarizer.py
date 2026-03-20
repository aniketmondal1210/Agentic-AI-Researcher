"""
Paper Summarizer Tool — generates a structured summary of a research paper.
"""

from langchain_core.tools import tool


@tool
def summarize_paper(paper_text: str, title: str = "Research Paper") -> str:
    """Generate a structured summary of a research paper's content.

    Args:
        paper_text: The full text content of the paper to summarize
        title: The title of the paper

    Returns:
        A structured summary with key sections
    """
    print(f"SUMMARIZER Agent called for: {title}")

    # Truncate if too long to avoid context issues
    if len(paper_text) > 20000:
        paper_text = paper_text[:20000] + "\n\n[... truncated ...]"

    summary_prompt = f"""Analyze the following research paper and provide a structured summary:

**Paper Title:** {title}

**Paper Content:**
{paper_text}

Please provide a summary with these sections:
1. **Key Findings** (3-5 bullet points)
2. **Methodology** (brief description)
3. **Main Contributions** (what's new/novel)
4. **Limitations** (identified weaknesses)
5. **Future Work** (suggested directions)
6. **Relevance Score** (1-10, how impactful is this paper)

Format the output as a clean, readable summary."""

    return summary_prompt
