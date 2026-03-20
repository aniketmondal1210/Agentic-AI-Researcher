"""
Literature Review Table Generator — creates structured comparison tables from papers.
"""

from langchain_core.tools import tool


@tool
def generate_literature_table(papers_info: str) -> str:
    """Generate an automated literature review comparison table from research papers.

    Args:
        papers_info: Text containing information about multiple papers 
                     (titles, methods, results, etc.)

    Returns:
        A structured prompt to generate a literature review table
    """
    print("LITERATURE TABLE: Generating comparison table")

    table_prompt = f"""Based on the following research papers information, create a comprehensive 
literature review comparison table.

**Papers Information:**
{papers_info}

**Generate a table with the following columns:**

| # | Paper Title | Authors | Year | Methodology | Dataset/Domain | Key Findings | Metrics/Results | Limitations | Future Work |
|---|-------------|---------|------|-------------|----------------|--------------|-----------------|-------------|-------------|
| 1 | ... | ... | ... | ... | ... | ... | ... | ... | ... |

**Additional Analysis:**

### 📊 Methodology Distribution
- List the different methodologies used and how many papers use each

### 📈 Trend Analysis
- What trends are visible across the papers?
- Are newer papers using different approaches than older ones?

### 🔬 Research Gaps
- What areas are not well-covered by the existing papers?
- What questions remain unanswered?

### 💡 Synthesis
- What can we conclude from comparing all these papers?
- Which approaches seem most promising?

Make the table as detailed and accurate as possible based on the available information.
If certain information is not available for a paper, mark it as "N/A"."""

    return table_prompt
