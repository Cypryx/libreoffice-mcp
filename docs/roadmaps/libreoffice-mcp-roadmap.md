# libreoffice-mcp — LibreOffice MCP Server
## Master Build Roadmap

---

## Project Overview

**libreoffice-mcp** is an open source Model Context Protocol (MCP) server that gives AI agents full programmatic access to LibreOffice documents. It covers Writer documents (.docx, .odt), Impress presentations (.pptx), and format conversion across all three, backed by a LibreOffice headless subprocess.

The server is designed for local stdio use with any MCP-compatible agent framework (Hermes, Claude Code, Claude Desktop, and others). It has no cloud dependencies. Everything runs on the user's machine.

### Design principles

- **Universal first.** No hardcoded personas, names, or configurations. Every user-specific value is an environment variable with a sensible default.
- **Composable.** Each tool does one thing well. Agents combine tools to accomplish complex workflows.
- **Honest about limitations.** The README documents what the Python libraries can and cannot do so developers don't discover gaps the hard way.
- **Reliable over clever.** Industrial-grade error handling. Every tool returns structured success/error responses. No silent failures.

---

## Repository Structure

```
libreoffice-mcp/
├── src/
│   └── libreoffice_mcp/
│       ├── __init__.py
│       ├── server.py          # MCP server entry point, tool registration
│       ├── config.py          # Environment variable loading, path resolution
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── document.py    # Document management tools
│       │   ├── reader.py      # Reading and analysis tools
│       │   ├── writer.py      # Writer/docx editing tools
│       │   ├── review.py      # Proofreading, comments, tracked changes
│       │   └── presentation.py # Presentation (pptx) tools
│       └── utils/
│           ├── __init__.py
│           ├── libreoffice.py # LibreOffice headless subprocess wrapper
│           └── converters.py  # Format detection and conversion helpers
├── tests/
│   ├── test_document.py
│   ├── test_writer.py
│   ├── test_review.py
│   └── test_presentation.py
├── docs/
│   ├── TOOL_REFERENCE.md      # Complete tool documentation with examples
│   ├── CONFIGURATION.md       # All environment variables documented
│   └── AGENT_PROMPTING.md     # Suggested system prompt additions for agents
├── pyproject.toml
├── uv.lock
├── .env.example
├── libreoffice-mcp-helper.sh       # Verification and test script
└── README.md
```

---

## Environment Variables

All configuration is via environment variables. No values are hardcoded.

| Variable | Default | Description |
|---|---|---|
| `LIBREOFFICE_PATH` | `libreoffice` | Path to LibreOffice binary |
| `LIBREOFFICE_MCP_WORKING_DIR` | `~/Documents/libreoffice-mcp` | Default working directory for documents |
| `LIBREOFFICE_MCP_AUTHOR_NAME` | `AI Assistant` | Default author name for comments and tracked changes |
| `LIBREOFFICE_MCP_AUTHOR_INITIALS` | `AI` | Default author initials for comments |
| `LIBREOFFICE_MCP_CONVERSION_TIMEOUT` | `30` | Seconds before LibreOffice conversion times out |

Author name and initials are optional. If not set, they default to generic values. Agents (Noöm, Cypryx, or any other persona) set their own values in their Hermes or system configuration.

---

## Tool Surface

### Group 1 — Document Management

| Tool | Description |
|---|---|
| `create_document` | Create a new .docx, .odt, or .pptx from blank or template |
| `open_document` | Load an existing document and return its metadata |
| `save_document` | Save with optional format change |
| `convert_document` | Convert between .docx, .odt, .pdf, .pptx via LibreOffice headless |
| `get_document_info` | Metadata, word count, slide count, author, last modified |
| `list_documents` | List documents in the working directory |

### Group 2 — Reading and Analysis

| Tool | Description |
|---|---|
| `read_document_text` | Extract full text with structure (headings, paragraphs) |
| `read_document_structure` | Return outline, heading hierarchy, or slide list |
| `search_document` | Find text, return matching locations and surrounding context |

### Group 3 — Writer / .docx Editing

| Tool | Description |
|---|---|
| `insert_text` | Insert text at a location (after paragraph, replace selection) |
| `replace_text` | Search and replace, with optional regex support |
| `format_text` | Apply bold, italic, font size, heading level, or named style |
| `insert_table` | Insert a table with provided data |
| `insert_image` | Insert an image at a specified location |

### Group 4 — Proofreading and Review

| Tool | Description |
|---|---|
| `add_comment` | Add an inline comment to a run or paragraph, with author name and initials |
| `read_comments` | List all comments with author, text, date, and document location |
| `resolve_comment` | Delete or mark a comment as resolved |
| `add_tracked_change` | Insert or delete text with author attribution and track changes markup |
| `accept_all_changes` | Accept all tracked changes in the document |
| `reject_all_changes` | Reject all tracked changes and restore original text |

### Group 5 — Presentation / .pptx

| Tool | Description |
|---|---|
| `read_slides` | List all slides with titles, text content, and shape summary |
| `add_slide` | Add a new slide from a named layout with title and content |
| `edit_slide_text` | Replace text in a named shape on a specific slide |
| `add_slide_image` | Insert an image into a slide at a specified position |
| `add_slide_notes` | Set or append speaker notes on a slide |
| `reorder_slides` | Move, duplicate, or delete slides |
| `export_presentation_pdf` | Export presentation to PDF via LibreOffice headless |

---

## Phase 0 — Prerequisites

**Goal:** Confirm the environment is ready before writing any server code.

**Tasks:**
- Confirm LibreOffice 24.2+ is installed and accessible via CLI
- Run a headless conversion test: `.odt` → `.pdf`
- Confirm Python 3.12+ is available
- Confirm `uv` is installed
- Confirm `git` is available

**Verification commands:**
```bash
libreoffice --version
libreoffice --headless --convert-to pdf --outdir /tmp /tmp/test.odt
python3 --version
uv --version
git --version
```

**Pass criteria:** All commands return without error. LibreOffice version is 24.2 or higher. A `.pdf` file appears at `/tmp/test.pdf`.

**Deliverables:**
- Checklist confirmed
- LibreOffice binary path noted for `LIBREOFFICE_PATH`

---

## Phase 1 — Project Scaffold

**Goal:** Create a clean, installable Python project ready for development.

**Tasks:**
- Initialize repo with `uv init`
- Configure `pyproject.toml` with project metadata, dependencies, and entry point
- Install core dependencies: `mcp[cli]`, `python-docx`, `docx-revisions`, `python-pptx`
- Create `src/libreoffice_mcp/` package structure
- Create `config.py` with environment variable loading
- Create `utils/libreoffice.py` with headless subprocess wrapper
- Create a minimal `server.py` that starts and registers zero tools (smoke test)
- Create `.env.example` with all environment variables documented
- Create `libreoffice-mcp-helper.sh` with `check`, `test`, `demo` commands

**Key dependency versions:**
```toml
[project]
name = "libreoffice-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcp[cli]>=1.0.0",
    "python-docx>=1.2.0",
    "docx-revisions>=0.1.0",
    "python-pptx>=1.0.0",
    "httpx>=0.27.0",
]
```

**Entry point:**
```toml
[project.scripts]
libreoffice-mcp = "libreoffice_mcp.server:main"
```

**Smoke test:**
```bash
uv run libreoffice-mcp --help
```

**Deliverables:**
- Installable Python package
- `config.py` with all environment variables
- LibreOffice headless wrapper with timeout handling
- Working entry point confirmed via `--help`

---

## Phase 2 — Core Server: Document Management and Reading

**Goal:** Implement the foundation layer. Reliable document I/O before any editing.

**Library mapping:**
- `.docx` create/read/save — `python-docx`
- `.pptx` create/read/save — `python-pptx`
- `.odt` and all format conversion — LibreOffice headless subprocess
- Format detection — file extension + `python-magic` or manual header check

**Tasks:**
- Implement Group 1 tools: `create_document`, `open_document`, `save_document`, `convert_document`, `get_document_info`, `list_documents`
- Implement Group 2 tools: `read_document_text`, `read_document_structure`, `search_document`
- Implement structured tool response format (success/error envelope)
- Write tests for all Group 1 and Group 2 tools
- Run full Phase 3 verification suite

**Tool response envelope:**
```json
{
  "success": true,
  "tool": "read_document_text",
  "data": { ... },
  "error": null
}
```

**Known limitation to document:** `.odt` files are read by converting to `.docx` via LibreOffice headless first, then parsing with `python-docx`. Direct `.odt` manipulation via `odfpy` is not implemented — the library is insufficiently maintained for production use.

**Deliverables:**
- 8 working tools covering document management and reading
- Structured error handling across all tools
- Tests passing for all Group 1 and Group 2 tools

---

## Phase 3 — Writer and .docx Editing Tools

**Goal:** Full programmatic editing of Writer documents.

**Library:** `python-docx` throughout. All operations work on `.docx` files natively. `.odt` workflows convert to `.docx`, edit, convert back.

**Tasks:**
- Implement Group 3 tools: `insert_text`, `replace_text`, `format_text`, `insert_table`, `insert_image`
- Handle paragraph targeting by index, heading text, or search match
- Implement regex support in `replace_text` (optional flag, defaults off)
- Handle style application via named Word styles (Heading 1, Normal, etc.)
- Write tests covering insert, replace, format, table, and image operations

**Known limitation to document:** `python-docx` cannot apply arbitrary complex formatting or deeply nested structures in a single call. For complex document generation, agents should make multiple sequential tool calls.

**Deliverables:**
- 5 working editing tools
- Tests passing
- `TOOL_REFERENCE.md` updated with Group 3 examples

---

## Phase 4 — Proofreading and Review Tools

**Goal:** Inline comment and tracked changes support for proofreading workflows. This is the capability that distinguishes libreoffice-mcp from every other LibreOffice MCP server.

**Library mapping:**
- Comments — `python-docx` v1.2.0 native `add_comment()` API
- Tracked changes (insert/delete markup) — `docx-revisions`
- Accept/reject all — `docx-revisions`

**Tasks:**
- Implement Group 4 tools: `add_comment`, `read_comments`, `resolve_comment`, `add_tracked_change`, `accept_all_changes`, `reject_all_changes`
- Author name and initials sourced from `LIBREOFFICE_MCP_AUTHOR_NAME` and `LIBREOFFICE_MCP_AUTHOR_INITIALS` environment variables
- Both fields are also accepted as optional per-call parameters, overriding the environment variable defaults
- Write tests covering comment add/read/resolve and tracked change add/accept/reject
- Test output: open resulting `.docx` in LibreOffice Writer and confirm comments and markup are visible and correctly attributed

**Author name behavior:**

| Scenario | Author shown |
|---|---|
| `LIBREOFFICE_MCP_AUTHOR_NAME` set, no per-call override | Environment variable value |
| Per-call `author` parameter provided | Per-call value |
| Neither set | `"AI Assistant"` |

**Known limitation to document:** `.pptx` inline comments are not supported by `python-pptx`. For presentation proofreading, agents use `add_slide_notes` as the annotation layer instead.

**Deliverables:**
- 6 working review tools
- Author attribution working via environment variable and per-call override
- Tests passing and visually verified in LibreOffice Writer
- `TOOL_REFERENCE.md` updated with Group 4 examples and proofreading workflow example

---

## Phase 5 — Presentation Tools

**Goal:** Full slide deck creation and editing via `python-pptx`.

**Library:** `python-pptx` throughout. All operations work on `.pptx` natively. Export to `.pdf` via LibreOffice headless.

**Tasks:**
- Implement Group 5 tools: `read_slides`, `add_slide`, `edit_slide_text`, `add_slide_image`, `add_slide_notes`, `reorder_slides`, `export_presentation_pdf`
- Handle slide layout selection by name and index
- Handle shape targeting by name and index within a slide
- Speaker notes used as the annotation/proofreading layer for presentations
- Write tests covering read, add, edit, image, notes, reorder, and export operations
- Test export: confirm LibreOffice headless renders `.pptx` to `.pdf` correctly

**Known limitation to document:** `python-pptx` works only with `.pptx` (PowerPoint 2007+). Legacy `.ppt` files must be converted to `.pptx` via LibreOffice headless before any editing. This conversion is handled automatically by `convert_document`.

**Deliverables:**
- 7 working presentation tools
- PDF export confirmed via LibreOffice headless
- Tests passing
- `TOOL_REFERENCE.md` updated with Group 5 examples

---

## Phase 6 — Hermes Integration (CachyOS)

**Goal:** Register libreoffice-mcp as a local stdio MCP server in Hermes on CachyOS and verify full end-to-end operation.

**Tasks:**
- Set environment variables in shell profile or Hermes environment config:
  ```bash
  export LIBREOFFICE_PATH="/usr/bin/libreoffice"
  export LIBREOFFICE_MCP_WORKING_DIR="$HOME/Documents/libreoffice-mcp"
  export LIBREOFFICE_MCP_AUTHOR_NAME="Noöm"
  export LIBREOFFICE_MCP_AUTHOR_INITIALS="NM"
  ```
- Add MCP entry to `~/.hermes/config.yaml`:
  ```yaml
  mcp_servers:
    libreoffice-mcp:
      command: "uv"
      args:
        - "run"
        - "--directory"
        - "/home/<username>/libreoffice-mcp"
        - "libreoffice-mcp"
      timeout: 60
  ```
- Run `/reload-mcp` and confirm tool discovery
- Run end-to-end verification sequence (see below)

**End-to-end verification sequence:**
1. Ask the agent to create a new Writer document called `test-report.docx`
2. Ask the agent to insert two paragraphs of text
3. Ask the agent to add a comment on the first paragraph noting a grammar issue
4. Ask the agent to export the document to PDF
5. Open both files — confirm text is present, comment is visible and attributed correctly, PDF renders cleanly

**Deliverables:**
- Hermes config entry confirmed working
- Tool discovery passing (all tools visible to agent)
- End-to-end verification sequence completed and documented

---

## Phase 7 — Live Editing Layer (Optional)

**Goal:** Add `jwingnut/mcp-libre` as a second, separate MCP server for sessions where visual editing in an open LibreOffice window is desired.

This phase is independent of the primary libreoffice-mcp server. It adds a complementary capability — live visual feedback — without replacing or modifying anything in the core server.

**When to use this layer:**
- The agent is doing complex layout work where visual feedback matters
- The user wants to watch the agent work in real time
- Reviewing a document collaboratively with the agent

**Tasks:**
- Clone `jwingnut/mcp-libre` separately
- Install the LibreOffice extension (`plugin/build.sh`)
- Add a second MCP entry to Hermes config:
  ```yaml
  mcp_servers:
    libreoffice-mcp:
      # ... primary server entry
    mcp-libre-live:
      command: "fastmcp"
      args:
        - "run"
        - "/home/<username>/mcp-libre/libreoffice_mcp_server.py"
      timeout: 120
  ```
- Verify both servers load simultaneously without conflict
- Document which tools come from which server so agents can route correctly

**Deliverables:**
- Live editing server running alongside libreoffice-mcp
- Both servers confirmed in tool discovery
- Usage guidance added to `docs/AGENT_PROMPTING.md`

---

## Phase 8 — Windows Port (Cypryx)

**Goal:** Deploy libreoffice-mcp on Windows for Cypryx. Near-identical setup with documented differences.

**Differences from CachyOS:**
- LibreOffice binary path: `C:\Program Files\LibreOffice\program\soffice.exe`
- Hermes config location: `C:\Users\<username>\AppData\Local\hermes\config.yaml`
- `UV_PYTHON` must be set explicitly if multiple Python versions are installed
- Environment variables set via Windows system environment or Hermes env block

**Hermes config entry (Windows):**
```yaml
mcp_servers:
  libreoffice-mcp:
    command: "uv"
    args:
      - "run"
      - "--directory"
      - "C:\\Users\\smeefer\\libreoffice-mcp"
      - "libreoffice-mcp"
    env:
      UV_PYTHON: "C:\\Users\\smeefer\\miniconda3\\python.exe"
      LIBREOFFICE_PATH: "C:\\Program Files\\LibreOffice\\program\\soffice.exe"
      LIBREOFFICE_MCP_AUTHOR_NAME: "Cypryx"
      LIBREOFFICE_MCP_AUTHOR_INITIALS: "CX"
    timeout: 60
```

**Tasks:**
- Confirm LibreOffice installed and CLI accessible on Windows
- Clone repo, run `uv sync --python <path>`
- Run `uv run libreoffice-mcp --help` standalone
- Add Hermes config entry
- Run `/reload-mcp` and confirm tool discovery
- Run same end-to-end verification sequence as Phase 6

**Deliverables:**
- Hermes config entry confirmed working on Windows
- End-to-end verification sequence completed
- Any Windows-specific issues documented in `docs/` for future reference

---

## Phase 9 — Public Release

**Goal:** Publish libreoffice-mcp as a well-documented, genuinely useful open source project.

**Tasks:**
- Write `README.md` covering: what it is, requirements, installation, Hermes config, Claude Desktop config, all environment variables, quick start example
- Write `docs/TOOL_REFERENCE.md` — complete documentation of all 26 tools with input parameters, output format, and usage examples
- Write `docs/CONFIGURATION.md` — every environment variable with type, default, and examples
- Write `docs/AGENT_PROMPTING.md` — suggested system prompt additions to help agents use the server well, including persona-specific author name setup
- Write `CONTRIBUTING.md`
- Tag `v0.1.0`
- Publish to GitHub (public repo)
- Optionally: submit to [mcpservers.org](https://mcpservers.org) directory

**README sections:**
- What libreoffice-mcp does (3 sentences)
- Requirements
- Installation
- Configuration (environment variables table)
- Hermes setup
- Claude Desktop / Claude Code setup
- Quick start (5-step example)
- Tool reference (link to docs/)
- Known limitations (honest, upfront)
- Contributing
- License (MIT)

**Deliverables:**
- Public GitHub repository
- Complete documentation
- `v0.1.0` tag
- Submitted to MCP server directories

---

## Status Tracking

| Phase | Status | Notes |
|---|---|---|
| 0 — Prerequisites | ☐ | |
| 1 — Project scaffold | ☐ | |
| 2 — Document management + reading | ☐ | |
| 3 — Writer / .docx editing | ☐ | |
| 4 — Proofreading and review | ☐ | |
| 5 — Presentation tools | ☐ | |
| 6 — Hermes integration (CachyOS) | ☐ | |
| 7 — Live editing layer | ☐ | Optional |
| 8 — Windows port (Cypryx) | ☐ | |
| 9 — Public release | ☐ | |

---

## Known Limitations (Consolidated)

These are documented upfront so developers and agents are never surprised.

| Limitation | Workaround |
|---|---|
| `.odt` native editing not supported | Convert to `.docx` via LibreOffice headless, edit, convert back |
| `.ppt` (legacy) not supported by python-pptx | Convert to `.pptx` via `convert_document` first |
| `.pptx` inline comments not supported | Use `add_slide_notes` as annotation layer |
| Complex formatting requires multiple tool calls | Chain `insert_text` + `format_text` calls |
| LibreOffice headless conversion requires display server or Xvfb on some Linux setups | Install `xvfb` and run `Xvfb :99 &` before starting server |

---

*libreoffice-mcp — MIT License*
