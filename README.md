# NanoPDF MCP Server

NanoPDF MCP Server is a Model Context Protocol (MCP) implementation that brings AI-powered PDF editing and generation capabilities directly to Claude Desktop. It enables users to modify existing PDF pages or generate new ones using Google's Gemini 3 Pro model, all within a privacy-focused local environment.

## 🚀 Key Features

- **AI-Driven Editing**: Modify PDF slides using natural language prompts.
- **Smart Generation**: Create new, visually consistent slides after any page.
- **Visual Previews**: View specific PDF pages as high-quality images.
- **Privacy First**: All versioning and temporary files are stored locally on your machine.
- **State Preservation**: Uses Tesseract OCR to maintain searchable text layers in AI-generated pages.
- **Version Control**: Built-in undo functionality for safe experimentation.

## 📋 Prerequisites

### System Dependencies

The server requires `poppler` (for PDF rendering) and `tesseract` (for OCR) installed on your system.

- **macOS (Homebrew):**
  ```bash
  brew install poppler tesseract
  ```
- **Ubuntu/Debian:**
  ```bash
  sudo apt-get install poppler-utils tesseract-ocr
  ```

### Environment Variables

A Google Gemini API key is required to power the AI features.

- `GEMINI_API_KEY`: Your Google AI Studio API key.

## 🛠️ Installation & Setup

### 1. Development Environment

This project uses `uv` for lightning-fast Python package management.

```bash
cd mcp-server
uv sync
```

### 2. Configure Claude Desktop

Add the NanoPDF server to your Claude Desktop configuration:

**Path:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "nanopdf": {
      "command": "/Users/username/.local/bin/uv", # replace with your uv path
      "args": [
        "run",
        "--directory",
        "/Users/username/nano-pdf-mcp/nano-pdf-mcp", # replace with your mcp-server path
        "server.py"
      ]
    }
  }
}
```

> [!IMPORTANT]
> Ensure the `--directory` path is the absolute path to your `mcp-server` folder.

## 📖 Usage Guide

For detailed tool descriptions and workflow examples, please refer to the [Usage Guide](USAGE.md).

### Core Workflow

1. **Open PDF**: `open_pdf(pdf_path="/path/to/document.pdf")`
2. **Edit/Add**: `edit_pdf_page(session_id="...", page_number=1, prompt="...")`

## 📂 Project Structure

- `server.py`: Main MCP server entry point and tool definitions.
- `mcp_pdf_utils.py`: PDF processing, OCR, and rendering logic.
- `mcp_ai_utils.py`: Gemini 3 Pro Vision API integration.
- `history_manager.py`: Local session and version history tracker.
- `output/`: Local storage for sessions, previews exports.

## 🤝 Acknowledgements

Based on the original [NanoPDF](https://github.com/gavrielc/Nano-PDF) project. Adapted for the Model Context Protocol.

## 📄 License

MIT License
