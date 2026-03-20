"""Read and extract text from a PDF file given its URL."""

from langchain_core.tools import tool
import io
import PyPDF2
import requests


@tool
def read_pdf(url: str) -> str:
    """Read and extract text from a PDF file given its URL.

    Args:
        url: The URL of the PDF file to read

    Returns:
        The extracted text content from the PDF
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Verify it's actually a PDF
        if not response.content[:5].startswith(b'%PDF'):
            return f"Error: The URL does not point to a valid PDF file: {url}"

        pdf_file = io.BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        num_pages = len(pdf_reader.pages)
        text = ""
        for i, page in enumerate(pdf_reader.pages, 1):
            print(f"Extracting text from page {i}/{num_pages}")
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        text = text.strip()

        # Truncate if too long to avoid context overflow
        if len(text) > 50000:
            text = text[:50000] + "\n\n[... truncated due to length ...]"

        print(f"Successfully extracted {len(text)} characters of text from PDF")
        return text if text else "Could not extract text from this PDF (may be scanned/image-based)."
    except requests.exceptions.Timeout:
        return f"Error: Request timed out when trying to download PDF from: {url}"
    except requests.exceptions.HTTPError as e:
        return f"Error: HTTP error {e.response.status_code} when downloading PDF from: {url}"
    except Exception as e:
        print(f"Error reading PDF: {str(e)}")
        return f"Error reading PDF: {str(e)}"

