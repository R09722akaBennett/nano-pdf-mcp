import os
import subprocess
import shutil
from pdf2image import convert_from_path
from pypdf import PdfReader, PdfWriter
import pytesseract
from PIL import Image
import logging
import tempfile
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_system_dependencies():
    """Checks if required system dependencies are installed."""
    missing = []

    # Check for pdftotext (part of poppler-utils)
    if not shutil.which('pdftotext'):
        missing.append('pdftotext (poppler/poppler-utils)')

    # Check for tesseract
    if not shutil.which('tesseract'):
        missing.append('tesseract')

    if missing:
        deps_str = ", ".join(missing)
        if os.name == 'darwin':  # macOS
            install_cmd = "brew install poppler tesseract"
        elif os.name == 'posix':  # Linux
            install_cmd = "sudo apt-get install poppler-utils tesseract-ocr"
        else:  # Windows
            install_cmd = "choco install poppler tesseract"

        raise RuntimeError(
            f"Missing system dependencies: {deps_str}\n\n"
            f"Installation:\n{install_cmd}\n"
        )

def get_page_count(pdf_path: str) -> int:
    """Returns the total number of pages in the PDF."""
    reader = PdfReader(pdf_path)
    return len(reader.pages)

def extract_full_text(pdf_path: str) -> str:
    """Extracts the full text from a PDF using pdftotext."""
    try:
        result = subprocess.run(
            ['pdftotext', '-layout', pdf_path, '-'],
            capture_output=True,
            text=False,
            check=True
        )
        raw_text = result.stdout.decode('utf-8', errors='replace')
        
        pages = raw_text.split('\f')
        formatted_pages = []
        for i, page_text in enumerate(pages):
            if not page_text.strip():
                continue
            clean_text = page_text.strip()
            if len(clean_text) > 2000:
                clean_text = clean_text[:2000] + "...[truncated]"
            formatted_pages.append(f"<page-{i+1}>\n{clean_text}\n</page-{i+1}>")
            
        return "<document_context>\n" + "\n".join(formatted_pages) + "\n</document_context>"
    except subprocess.CalledProcessError as e:
        logger.error(f"Error extracting text: {e}")
        return ""

def render_page_as_image(pdf_path: str, page_number: int) -> Image.Image:
    """Renders a specific page (1-indexed) as a PIL Image."""
    images = convert_from_path(
        pdf_path, 
        first_page=page_number, 
        last_page=page_number
    )
    if not images:
        raise ValueError(f"Could not render page {page_number}")
    return images[0]



def rehydrate_image_to_pdf(image: Image.Image, output_pdf_path: str):
    """
    Converts Image to PDF using Tesseract.
    USES LOCAL DIRECTORY instead of system /tmp to avoid macOS Sandbox issues.
    """
    temp_input_path = None
    temp_output_base = None
    local_temp_dir = None
    
    try:
        # 1. Set Tesseract path
        tesseract_cmd = 'tesseract'
        possible_paths = [
            "/opt/homebrew/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/usr/bin/tesseract"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                tesseract_cmd = path
                break
        
        # 2. Use a local temporary directory within the project to avoid macOS sandbox restrictions.
        current_dir = os.getcwd()
        local_temp_dir = os.path.join(current_dir, "mcp_temp_work")
        os.makedirs(local_temp_dir, exist_ok=True)
        
        # 3. Generate a unique filename (avoiding tempfile module to have more control)
        unique_id = str(uuid.uuid4())
        temp_input_path = os.path.join(local_temp_dir, f"{unique_id}.png")
        temp_output_base = os.path.join(local_temp_dir, unique_id) 
        
        logger.info(f"Saving temp image to safe local path: {temp_input_path}")
        
        # 4. Save the image as PNG
        image.save(temp_input_path, format="PNG")
        
        # 5. Run Tesseract CLI
        cmd = [tesseract_cmd, temp_input_path, temp_output_base, "pdf"]
        
        process = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            cwd=local_temp_dir, 
            env=os.environ.copy()
        )

        if process.returncode != 0:
            error_msg = process.stderr.decode('utf-8', errors='replace')
            raise RuntimeError(f"Tesseract CLI Error: {error_msg}")

        generated_pdf = temp_output_base + ".pdf"

        if not os.path.exists(generated_pdf):
            raise RuntimeError(f"Tesseract output missing at: {generated_pdf}")
            
        if os.path.exists(output_pdf_path):
            os.remove(output_pdf_path)
        shutil.move(generated_pdf, output_pdf_path)
        
        logger.info(f"PDF generated successfully: {output_pdf_path}")

    except Exception as e:
        logger.warning(f"OCR failed ({str(e)}). Fallback to simple PDF conversion.")
        try:
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.save(output_pdf_path, "PDF", resolution=100.0)
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            raise

    finally:
        # Cleanup temporary files
        try:
            if temp_input_path and os.path.exists(temp_input_path):
                os.remove(temp_input_path)
            # Cleanup generated PDF
            if temp_output_base and os.path.exists(temp_output_base + ".pdf"):
                os.remove(temp_output_base + ".pdf")
            # The local_temp_dir is kept as a persistent work directory
        except Exception as cleanup_err:
            logger.warning(f"Cleanup warning: {cleanup_err}")

def replace_page_in_pdf(original_pdf_path: str, new_page_pdf_path: str, page_number: int, output_pdf_path: str):
    """Replaces a specific page in the original PDF."""
    try:
        reader = PdfReader(original_pdf_path)
        writer = PdfWriter()

        for i in range(len(reader.pages)):
            if i == page_number - 1:
                original_page = reader.pages[i]
                original_width = original_page.mediabox.width
                original_height = original_page.mediabox.height
                
                new_reader = PdfReader(new_page_pdf_path)
                new_page = new_reader.pages[0]
                new_page.scale_to(width=float(original_width), height=float(original_height))
                writer.add_page(new_page)
            else:
                writer.add_page(reader.pages[i])

        with open(output_pdf_path, 'wb') as f:
            writer.write(f)
            
    except Exception as e:
        logger.error(f"Error in replace_page_in_pdf: {e}")
        raise

def insert_page(original_pdf_path: str, new_page_pdf_path: str, after_page: int, output_pdf_path: str):
    """Inserts a new page into the PDF after the specified page number."""
    reader = PdfReader(original_pdf_path)
    writer = PdfWriter()

    reference_page = reader.pages[0]
    ref_width = reference_page.mediabox.width
    ref_height = reference_page.mediabox.height

    new_reader = PdfReader(new_page_pdf_path)
    new_page = new_reader.pages[0]
    new_page.scale_to(width=float(ref_width), height=float(ref_height))

    if after_page == 0:
        writer.add_page(new_page)

    for i in range(len(reader.pages)):
        writer.add_page(reader.pages[i])
        if i + 1 == after_page:
            writer.add_page(new_page)

    with open(output_pdf_path, 'wb') as f:
        writer.write(f)
