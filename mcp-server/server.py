import os
import tempfile
import base64
from io import BytesIO
from typing import Optional
from fastmcp import FastMCP
import mcp_pdf_utils as pdf_utils
import mcp_ai_utils as ai_utils
from history_manager import HistoryManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("NanoPDF")
history = HistoryManager()

@mcp.tool()
def open_pdf(pdf_path: str) -> str:
    """
    Open a PDF file and initialize a new editing session.
    
    IMPORTANT: Requires the absolute path to the PDF file. 
    To get the absolute path on macOS:
      1. Right-click the file in Finder
      2. Hold the Option key
      3. Select "Copy '...' as Pathname"
      4. Paste the path as the argument
    """
    # Check if path is absolute
    if not os.path.isabs(pdf_path):
        return f"""❌ Please provide the absolute path to the PDF file.

Example:
  /Users/kdanmobile/Downloads/{pdf_path}

To get the absolute path:
  1. Right-click the file in Finder
  2. Hold Option key
  3. Select "Copy ... as Pathname"
  4. Paste the path here"""
    
    if not os.path.exists(pdf_path):
        return f"❌ File not found at: {pdf_path}\n\nPlease check the path and try again."
    
    try:
        session_id = history.init_session(pdf_path)
        output_dir = os.path.join(history.base_dir, "sessions", session_id)
        return f"""✅ Session initialized successfully!

Session ID: {session_id}
Original PDF: {pdf_path}
Working Directory: {output_dir}

Use this session_id with other tools to edit, preview, or add pages."""
    except Exception as e:
        return f"❌ Error initializing session: {str(e)}"

@mcp.tool()
def get_pdf_info(session_id: str) -> str:
    """
    Returns the page count and a summary of the PDF content for the session.
    """
    try:
        state = history.load_state(session_id)
        page_count = pdf_utils.get_page_count(state.current_path)
        context = pdf_utils.extract_full_text(state.current_path)
        return f"PDF Info:\nPages: {page_count}\nContent Summary:\n{context[:500]}..."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def preview_pdf_page(session_id: str, page_number: int) -> str:
    """
    Convert a specific page of the PDF to an image and save it.
    
    Args:
        session_id: Session ID
        page_number: Page number (1-based)
    
    Returns:
        The path to the saved image
    """
    try:
        state = history.load_state(session_id)
        img = pdf_utils.render_page_as_image(state.current_path, page_number)
        
        # Save to output/previews directory
        preview_dir = os.path.join(history.base_dir, "previews", session_id)
        os.makedirs(preview_dir, exist_ok=True)
        
        preview_path = os.path.join(preview_dir, f"page_{page_number}.png")
        img.save(preview_path, format="PNG")
        
        return f"""✅ Page {page_number} preview saved to:
{preview_path}

You can open this file to view the page."""
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def edit_pdf_page(session_id: str, page_number: int, prompt: str) -> str:
    """
    Edits a specific page of the PDF using AI based on a natural language prompt.
    
    IMPORTANT: You MUST specify the page_number. If the user hasn't explicitly mentioned 
    which page to edit, you MUST ASK the user to confirm the page number first.
    """
    try:
        state = history.load_state(session_id)
        
        # 1. Get Context
        try:
            full_text = pdf_utils.extract_full_text(state.current_path)
        except Exception as e:
            return f"❌ Error extracting text: {str(e)}"
        
        # 2. Get Current Page Image
        try:
            current_img = pdf_utils.render_page_as_image(state.current_path, page_number)
        except Exception as e:
            return f"❌ Error rendering page: {str(e)}"
        
        # 3. Generate New Content
        try:
            new_img, response_text = ai_utils.generate_edited_slide(
                target_image=current_img,
                style_reference_images=[current_img],
                full_text_context=full_text,
                user_prompt=prompt
            )
        except Exception as e:
            return f"❌ Error generating AI content: {str(e)}"
        
        # 3.5. Save the generated image to previews (for debugging/inspection)
        try:
            preview_dir = os.path.join(history.base_dir, "previews", session_id)
            os.makedirs(preview_dir, exist_ok=True)
            generated_image_path = os.path.join(preview_dir, f"generated_page_{page_number}.png")
            new_img.save(generated_image_path, format="PNG")
        except Exception as e:
            return f"❌ Error saving generated image: {str(e)}"
        
        # 4. Convert Image to PDF Page (with OCR and fallback)
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_new_page:
                temp_new_page_path = temp_new_page.name
            
            # Try OCR first, will auto-fallback to simple if OCR fails
            logger.info(f"Converting image to PDF: {temp_new_page_path}")
            logger.info(f"Image: {new_img}")
            pdf_utils.rehydrate_image_to_pdf(new_img, temp_new_page_path)
        except Exception as e:
            return f"❌ Error converting image to PDF: {str(e)}\n\nGenerated image saved at: {generated_image_path}"
        
        # 5. Replace in PDF
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_output:
                temp_output_path = temp_output.name
            
            pdf_utils.replace_page_in_pdf(
                original_pdf_path=state.current_path,
                new_page_pdf_path=temp_new_page_path,
                page_number=page_number,
                output_pdf_path=temp_output_path
            )
        except Exception as e:
            # Cleanup temp files
            if os.path.exists(temp_new_page_path):
                os.remove(temp_new_page_path)
            return f"❌ Error replacing page in PDF: {str(e)}\n\nGenerated image saved at: {generated_image_path}"
        
        # 6. Save Version
        try:
            history.add_version(session_id, temp_output_path)
        except Exception as e:
            return f"❌ Error saving version: {str(e)}"
        
        # Cleanup
        if os.path.exists(temp_new_page_path):
            os.remove(temp_new_page_path)
            
        return f"""✅ Page {page_number} updated successfully!

Latest Version: {state.current_path}
Generated Image (for reference): {generated_image_path}
AI Response: {response_text or 'Done'}"""
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"

@mcp.tool()
def add_pdf_page(session_id: str, after_page: int, prompt: str) -> str:
    """
    Generates and inserts a new page into the PDF after the specified page number.
    
    IMPORTANT: You MUST specify after_page (use 0 for a new first page). 
    If the user hasn't explicitly mentioned where to insert the new page, 
    you MUST ASK the user to confirm the insertion point first.
    """
    try:
        state = history.load_state(session_id)
        
        # 1. Get Context
        full_text = pdf_utils.extract_full_text(state.current_path)
        
        # 2. Get Style Reference
        ref_page = 1 if after_page == 0 else after_page
        style_ref_img = pdf_utils.render_page_as_image(state.current_path, ref_page)
        
        # 3. Generate New Slide
        new_img, response_text = ai_utils.generate_new_slide(
            style_reference_images=[style_ref_img],
            user_prompt=prompt,
            full_text_context=full_text
        )
        
        # 4. Convert to PDF Page
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_new_page:
            temp_new_page_path = temp_new_page.name
        pdf_utils.rehydrate_image_to_pdf(new_img, temp_new_page_path)
        
        # 5. Insert into PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_output:
            temp_output_path = temp_output.name
        
        pdf_utils.insert_page(
            original_pdf_path=state.current_path,
            new_page_pdf_path=temp_new_page_path,
            after_page=after_page,
            output_pdf_path=temp_output_path
        )
        
        # 6. Save Version
        history.add_version(session_id, temp_output_path)
        
        # Cleanup
        if os.path.exists(temp_new_page_path):
            os.remove(temp_new_page_path)
            
        return f"""✅ New page added after page {after_page}.

Latest Version: {state.current_path}
AI Response: {response_text or 'Done'}"""
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def undo_pdf_change(session_id: str) -> str:
    """
    Reverts the last change made to the PDF in the current session.
    """
    try:
        state = history.undo(session_id)
        return f"✅ Undone successfully. Reverted to version index {state.current_index}.\nCurrent Path: {state.current_path}"
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    mcp.run()

if __name__ == "__main__":
    main()
