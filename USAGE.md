# NanoPDF MCP Server Usage Guide

This server operates in a **strictly isolated environment**. All files and versions are stored within the project's `output/` directory to ensure no unintended modifications occur to your original documents.

## 🚀 Recommended Workflow

### 1. Initialize a Session

Start by opening your PDF document. Provide the **absolute path** to the source file. The server will copy it to its own internal storage.

**User Prompt:**
"Open the PDF file at `/Users/username/Downloads/Presentation.pdf`"

**Claude Actions:**
Calls `open_pdf(pdf_path="/Users/username/Downloads/Presentation.pdf")`

---

### 2. Direct AI Editing

You can edit pages using natural language. The server will generate a new version in the session folder.

**User Prompt:**
"On page 1, change the title to 'Annual Report 2024'."

**Claude Actions:**
Calls `edit_pdf_page(session_id="...", page_number=1, prompt="...")`

**Result:**
The response will include the **Latest Version path**, for example: 
`.../nano-pdf-mcp/output/sessions/{id}/v1_abcdef.pdf`

---

### 3. Reviewing Versions

Because the server saves a new file for every change, you can always go back.

- **Check Path**: Claude will tell you the path to the current version. You can open this file directly from your computer.
- **Undo**: If you're not happy, just say "Undo that". 
  `undo_pdf_change(session_id="...")`

---

## 🛠️ Available Tools Reference

| Tool | Description | Key Parameters |
| :--- | :--- | :--- |
| `open_pdf` | Initializes a session (copies source to internal storage) | `pdf_path` |
| `get_pdf_info` | Reads metadata/page count | `session_id` |
| `preview_pdf_page` | Saves a page as a PNG for internal viewing | `session_id`, `page_number` |
| `edit_pdf_page` | Modifies a page and saves a NEW version | `session_id`, `page_number`, `prompt` |
| `add_pdf_page` | Inserts a new page and saves a NEW version | `session_id`, `after_page`, `prompt` |
| `undo_pdf_change` | Reverts to the previous file version | `session_id` |

## 💡 Best Practices

1. **State Page Numbers**: Always specify which page you want to modify to avoid ambiguity.
2. **Accessing Files**: To see your results, use the "Latest Version" path provided after each successful tool call.
3. **Clean Up**: All data is inside the `output/` folder. You can manually delete session folders if you want to free up space.

---

## 📂 Directory Organization

- `output/sessions/`: All PDF versions and states (v0, v1, v2...).
- `output/previews/`: Temporary PNG renders for reference.
