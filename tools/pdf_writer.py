"""Render a LaTeX document to PDF using tectonic."""

from langchain_core.tools import tool
from datetime import datetime
from pathlib import Path
import subprocess
import shutil
import re


def _ensure_valid_latex(content: str) -> str:
    """Ensure the content is a complete, compilable LaTeX document.

    Handles two common LLM mistakes:
    1. Wrapping LaTeX in markdown code fences (```latex ... ```)
    2. Passing raw text / partial LaTeX without \\documentclass + \\begin{document}
    """
    # Strip markdown code fences if present
    content = re.sub(r"^```(?:latex|tex)?\s*", "", content.strip(), flags=re.IGNORECASE)
    content = re.sub(r"\s*```$", "", content.strip())
    content = content.strip()

    # If it already looks like a full LaTeX document, return as-is
    if r"\documentclass" in content and r"\begin{document}" in content:
        return content

    # Otherwise wrap it in a standard academic paper template
    return r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{geometry}
\geometry{margin=1in}
\usepackage{setspace}
\onehalfspacing

\begin{document}

""" + content + r"""

\end{document}
"""


@tool
def render_latex_pdf(latex_content: str) -> str:
    """Render a LaTeX document to PDF.

    Args:
        latex_content: The LaTeX document content as a string

    Returns:
        Path to the generated PDF document
    """
    if shutil.which("tectonic"):
        compiler = "tectonic"
    elif shutil.which("pdflatex"):
        compiler = "pdflatex"
    else:
        return (
            "Error: Neither tectonic nor pdflatex is installed on this server. "
            "The LaTeX content has been prepared but cannot be compiled to PDF in this environment. "
        )

    try:
        # Ensure content is a valid compilable LaTeX document
        latex_content = _ensure_valid_latex(latex_content)

        # Generate output directory and files
        output_dir = Path("output").absolute()
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tex_filename = f"paper_{timestamp}.tex"
        pdf_filename = f"paper_{timestamp}.pdf"

        # Write .tex file
        tex_file = output_dir / tex_filename
        tex_file.write_text(latex_content, encoding="utf-8")

        if compiler == "tectonic":
            args = ["tectonic", tex_filename, "--outdir", str(output_dir)]
        else:
            args = ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(output_dir), tex_filename]

        # Compile to PDF
        result = subprocess.run(
            args,
            cwd=output_dir,
            capture_output=True,
            text=True,
        )

        final_pdf = output_dir / pdf_filename
        if not final_pdf.exists():
            raise FileNotFoundError(
                f"PDF file was not generated. {compiler} output:\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )

        print(f"Successfully generated PDF at {final_pdf}")
        return str(final_pdf)

    except Exception as e:
        print(f"Error rendering LaTeX: {str(e)}")
        raise


