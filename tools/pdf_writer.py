"""Render a LaTeX document to PDF using tectonic."""

from langchain_core.tools import tool
from datetime import datetime
from pathlib import Path
import subprocess
import shutil


@tool
def render_latex_pdf(latex_content: str) -> str:
    """Render a LaTeX document to PDF.

    Args:
        latex_content: The LaTeX document content as a string

    Returns:
        Path to the generated PDF document
    """
    if shutil.which("tectonic") is None:
        raise RuntimeError(
            "tectonic is not installed. Install it first on your system. "
            "Visit: https://tectonic-typesetting.github.io/en-US/install.html"
        )

    try:
        # Create output directory
        output_dir = Path("output").absolute()
        output_dir.mkdir(exist_ok=True)

        # Setup filenames with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tex_filename = f"paper_{timestamp}.tex"
        pdf_filename = f"paper_{timestamp}.pdf"

        # Write .tex file
        tex_file = output_dir / tex_filename
        tex_file.write_text(latex_content)

        # Compile to PDF using tectonic
        result = subprocess.run(
            ["tectonic", tex_filename, "--outdir", str(output_dir)],
            cwd=output_dir,
            capture_output=True,
            text=True,
        )

        final_pdf = output_dir / pdf_filename
        if not final_pdf.exists():
            raise FileNotFoundError(
                f"PDF file was not generated. Tectonic output:\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )

        print(f"Successfully generated PDF at {final_pdf}")
        return str(final_pdf)

    except Exception as e:
        print(f"Error rendering LaTeX: {str(e)}")
        raise
