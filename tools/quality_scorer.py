"""
Paper Quality Scorer — evaluates generated research papers on multiple criteria.
"""

from langchain_core.tools import tool


@tool
def score_paper_quality(paper_content: str) -> str:
    """Evaluate the quality of a research paper on multiple academic criteria.

    Args:
        paper_content: The full text of the research paper to evaluate

    Returns:
        A structured quality assessment with scores and feedback
    """
    print("QUALITY SCORER: Evaluating paper")

    # Truncate if too long
    if len(paper_content) > 20000:
        paper_content = paper_content[:20000] + "\n[... truncated ...]"

    scoring_prompt = f"""You are a senior academic peer reviewer. Evaluate the following research paper 
on each criterion below. For each criterion, provide:
- A score from 1-10
- A brief justification (1-2 sentences)

**Evaluation Criteria:**

1. **Coherence & Flow** (1-10): Is the paper logically structured? Do sections flow naturally?
2. **Citation Quality** (1-10): Are sources properly cited? Are citations relevant and sufficient?
3. **Novelty & Contribution** (1-10): Does the paper offer new insights or synthesis?
4. **Methodology Rigor** (1-10): Is the analytical approach sound and well-described?
5. **Writing Quality** (1-10): Is the language clear, formal, and grammatically correct?
6. **Completeness** (1-10): Are all standard sections present and adequately developed?
7. **Abstract Quality** (1-10): Does the abstract accurately summarize the paper?
8. **Conclusion Strength** (1-10): Are findings properly synthesized with clear implications?

**Paper to Evaluate:**
{paper_content}

**Format your response as:**
## 📊 Paper Quality Assessment

| Criterion | Score | Feedback |
|-----------|-------|----------|
| Coherence & Flow | X/10 | ... |
| Citation Quality | X/10 | ... |
| Novelty & Contribution | X/10 | ... |
| Methodology Rigor | X/10 | ... |
| Writing Quality | X/10 | ... |
| Completeness | X/10 | ... |
| Abstract Quality | X/10 | ... |
| Conclusion Strength | X/10 | ... |

**Overall Score: X/80 (X%)**

### 🔑 Key Strengths
- ...

### ⚠️ Areas for Improvement
- ...

### 📝 Recommended Revisions
1. ...
2. ...
3. ..."""

    return scoring_prompt
