# libreoffice-mcp — Phase 2 Roadmap
## Document Management and Reading

**Repository:** https://github.com/Cypryx/libreoffice-mcp
**Starts from:** `main` after the Phase 0–1 project log commit (Phase 1 code at `953f83e`)
**Master roadmap reference:** Phase 2, tool Groups 1 and 2

This is the plan for Phase 2. Once work begins it is not edited. What is actually built gets recorded in the Phase 2 project log.

---

## Goal

An agent can create, inspect, convert, list, read and search `.docx`, `.odt` and `.pptx` documents through 9 MCP tools, on both CachyOS and Windows. Each tool returns a predictable success or error response, and none can crash the server or leave LibreOffice processes behind.

Phase 2 adds no editing. Editing begins in Phase 3.

---

## Team and roles

| Who | Machine | Role in Phase 2 |
|---|---|---|
| Project owner (sm33f3r) | Both | Approves each stage, relays prompts, merges to `main` |
| Architect (Claude, chat) | — | Plans, writes prompts, reviews code on GitHub, writes the project log |
| Claude Code | CachyOS laptop | Builds every stage on the `phase-2` branch and runs the automated tests |
| Noöm (Hermes) | CachyOS laptop | Agent acceptance testing on the priority machine, then day-to-day use |
| Cypryx (Hermes) | Windows PC | Runs the test suite and agent acceptance testing on Windows |

**Working rules**
- Hermes agents get **one task per prompt**.
- Agents never mark a stage done on their own report. The architect confirms by reading the files on GitHub at the pushed commit hash, or through a `git pull`.
- Verification that would cost agent tokens goes to Claude Code where possible.
- All commits use the author `sm33f3r <235947033+sm33f3r@users.noreply.github.com>`.
- The roadmap is never edited. Deviations go in the project log.

---

## Decisions

These four were left open at the end of the overview. The defaults below are what the roadmap assumes, and the owner can override any of them before the stage that depends on it.

| # | Decision | Assumed default | Needed by |
|---|---|---|---|
| D1 | `open_document` and `save_document` overlap with other tools in a stateless server | Keep all 9 tools with distinct jobs: `open_document` is a one-call overview, and `save_document` is "save as" | Stage 2.2 |
| D2 | Path confinement | Absolute paths allowed. An opt-in setting restricts tools to the working directory | Stage 2.1 |
| D3 | Templates in `create_document` | Blank documents only. Templates come in a later phase | Stage 2.2 |
| D4 | Default conversion timeout | 30 s (unchanged) | Stage 2.0 |

**Not blocking:** whether AGPL-3.0 is the intended license (the master roadmap says MIT).

---

## Workflow

1. Claude Code works on branch `phase-2` in the laptop clone, with one commit per stage.
2. After each stage, Claude Code pushes `phase-2`. The architect reviews it on GitHub before the next stage starts.
3. Noöm is not pointed at `phase-2` until Stage 2.5. Hermes runs the server from the same folder Claude Code works in, so testing mid-stage would exercise half-built code.
4. At Stage 2.5, Cypryx checks out `phase-2` on Windows.
5. After both machines pass, the owner merges `phase-2` into `main` with a fast-forward or a pull request.

---

## Stage 2.0 — Hardening (Phase 1 carry-over)

**Goal:** the wrapper and project setup are solid before any tool depends on them.

**Tasks**
1. **Process-tree kill on timeout.** Replace `subprocess.run` in `run_headless` with `subprocess.Popen` plus `communicate(timeout=...)`.
   - POSIX: start with `start_new_session=True`; on timeout, `os.killpg` the group with SIGTERM, then SIGKILL after a short grace period.
   - Windows: on timeout, run `taskkill /T /F /PID <pid>`.
   - The temporary profile stays, and is still removed afterwards.
2. **Timeout message.** Format seconds so sub-second values print correctly (for example `:g`), not as `0s`.
3. **Conversion limit.** Add a semaphore that caps simultaneous LibreOffice processes. A new setting, `LIBREOFFICE_MCP_MAX_CONCURRENT_CONVERSIONS`, defaults to 2.
4. **Dependencies.** Declare `typer` in `pyproject.toml`, and add a dev dependency group with `pytest`.
5. **Scripts.** Delete `scripts/hermes_launch_test.py`. Replace `scripts/stdio_smoke.py` with a test (Stage 2.4). Keep `scripts/spike_docx.py` as a record of the Phase 1 spike.
6. **Server cleanup.** Remove the unused `serve --timeout` option and the unreachable `no_args_is_help`.

**Acceptance**
- With LibreOffice **closed**, a conversion forced to time out (a 0.5 s timeout on a docx-to-pdf conversion) raises `LibreOfficeError`. Five seconds later, no `soffice`, `soffice.bin` or `oosplash` process remains, and no temporary profile folder remains. Checked on CachyOS by Claude Code and on Windows by Cypryx.
- The 4-file concurrent conversion test still passes 3 of 3 runs, with LibreOffice closed.
- `uv sync` and `uv run libreoffice-mcp --help` work.

---

## Stage 2.1 — Shared foundations

**New modules:** `utils/envelope.py`, `utils/paths.py`. The existing `utils/converters.py` is extended.

### Response envelope
Every tool returns the same shape.

```json
{ "success": true,  "tool": "get_document_info", "data": { ... }, "error": null }
{ "success": false, "tool": "get_document_info", "data": null,
  "error": { "code": "FILE_NOT_FOUND", "message": "No file at /home/.../report.docx" } }
```

**Error codes:** `FILE_NOT_FOUND`, `FILE_EXISTS`, `UNSUPPORTED_FORMAT`, `INVALID_ARGUMENT`, `PATH_NOT_ALLOWED`, `CONVERSION_FAILED`, `CONVERSION_TIMEOUT`, `LIBREOFFICE_NOT_FOUND`, `READ_FAILED`, `INTERNAL_ERROR`.

A decorator catches every exception, maps it to a code, and returns an error envelope. No tool can raise into the MCP layer. Unexpected exceptions map to `INTERNAL_ERROR`, with the message but no stack trace.

### Path rules
- `~` is expanded.
- A relative path resolves under `LIBREOFFICE_MCP_WORKING_DIR`. The working directory is created on first use.
- Absolute paths are allowed by default (D2).
- New setting: `LIBREOFFICE_MCP_RESTRICT_TO_WORKING_DIR` (default `false`). When `true`, any path that resolves outside the working directory, including through `..` or a symlink, is rejected with `PATH_NOT_ALLOWED`.
- Tools that write never overwrite an existing file unless they are called with `overwrite=true`. Otherwise they return `FILE_EXISTS`.
- Results always report **absolute** paths.

### Formats
| Family | Read and edit natively | Read through conversion | Conversion targets |
|---|---|---|---|
| Writer | `.docx` | `.odt`, `.doc`, `.rtf` | `docx`, `odt`, `pdf`, `rtf`, `txt`, `html` |
| Presentation | `.pptx` | `.odp`, `.ppt` | `pptx`, `odp`, `pdf` |

Converting across families (for example `.pptx` to `.docx`) returns `UNSUPPORTED_FORMAT`. `odp` is added to the wrapper's list of allowed targets.

### Conversion safety
- Conversions run in a worker thread (`asyncio.to_thread`), so a slow conversion doesn't block other tool calls.
- LibreOffice writes into a private temporary folder. The result is then moved to its destination, so no half-written file ever appears and two calls can't clash over the same output name.
- `.odt`, `.doc`, `.rtf`, `.odp` and `.ppt` files are read by converting them to a temporary `.docx` or `.pptx`, which is never written next to the user's file and is deleted afterwards.

### Location scheme
Phase 2 fixes how positions in a document are described. Phase 3 editing and Phase 4 comments will use the same scheme, so it must not change later.
- **Writer:** `paragraph_index` is the 0-based index into python-docx's `Document.paragraphs` (paragraphs in the main body, excluding table cells). Tables are addressed separately by `table_index`, with `row` and `col`.
- **Presentation:** `slide_index` (0-based) and `shape_index` within that slide, plus the shape's `shape_name`.

**Acceptance:** unit tests cover the envelope decorator, path resolution (relative, `~`, absolute, `..` and symlink escape with the restriction on), and format routing.

---

## Stage 2.2 — Document management tools (6)

Module: `tools/document.py`, registered through `register(mcp)` in `server.py`.

### `create_document`
- **Parameters:** `path` (required), `title` (optional), `content` (optional), `overwrite` (default `false`).
- **`.docx`:** `title` becomes a Title-style paragraph. `content` is split on blank lines into Normal paragraphs.
- **`.pptx`:** one title slide; `title` sets the title, and `content` sets the subtitle.
- **`.odt`:** built as a `.docx` in a temporary folder, then converted to `.odt`.
- **Other extensions:** `UNSUPPORTED_FORMAT`. Templates are not supported yet (D3).
- **Returns:** `path`, `format`, `size_bytes`.

### `open_document`
The first call an agent makes on an unfamiliar document.
- **Parameters:** `path`, `preview_chars` (default 1000).
- **Returns:** everything from `get_document_info`, plus the outline (headings or slide titles, capped at 50), plus a text preview of the first `preview_chars` characters.
- Opening stores nothing on the server.

### `save_document` (save as)
- **Parameters:** `source_path`, `target_path`, `overwrite` (default `false`).
- If the extension is unchanged, the file is copied. If it changed, the file is converted to the target extension's format.
- **Returns:** `source_path`, `target_path`, `format`, `converted` (`true` or `false`), `size_bytes`.

### `convert_document`
- **Parameters:** `path`, `target_format` (for example `pdf`), `output_dir` (optional, defaults to the source's folder), `overwrite` (default `false`).
- The output name is the source name with the new extension.
- **Returns:** `source_path`, `output_path`, `target_format`, `size_bytes`, `duration_seconds`.

### `get_document_info`
- **Parameters:** `path`.
- **Returns for every format:** `path`, `format`, `size_bytes`, `modified` (file time, ISO 8601), and core properties (`title`, `author`, `created`, `modified`, `last_modified_by`), with null for any that are missing.
- **Writer:** `paragraph_count`, `table_count`, `word_count`, `character_count`.
- **Presentation:** `slide_count`.
- **`.odt` / `.odp`:** properties and statistics come straight from the package's `meta.xml`, with no LibreOffice call.

### `list_documents`
- **Parameters:** `directory` (optional, defaults to the working directory), `recursive` (default `false`), `formats` (optional list, for example `["docx", "pptx"]`), `limit` (default 200).
- Lists only supported formats, and skips LibreOffice lock files (`.~lock.*#`) and Office temp files (`~$*`).
- **Returns:** a list of entries (`path`, `format`, `size_bytes`, `modified`), plus `total` and `truncated`.

**Acceptance:** each tool has success-path tests for every format it supports, plus tests for its error codes: missing file, existing target without `overwrite`, unsupported format, and a cross-family conversion.

---

## Stage 2.3 — Reading tools (3)

Module: `tools/reader.py`.

### `read_document_text`
- **Parameters:** `path`, `max_chars` (default 50000), `include_tables` (default `true`), `include_notes` (presentations only, default `false`).
- **Writer:** walks the document body in order, covering paragraphs and tables. Headings are prefixed with `#` marks by level. Each table is rendered as a pipe table.
- **Presentation:** emits `## Slide N: <title>` followed by the slide's text in shape order, then the speaker notes when `include_notes` is set.
- **Returns:** `text`, `char_count` (before truncation), `truncated`, `format`.

### `read_document_structure`
- **Parameters:** `path`.
- **Writer:** `headings` (each with `level`, `text` and `paragraph_index`), `paragraph_count`, `table_count`, `image_count`, `section_count`, `comment_count`.
- **Presentation:** `slides` (each with `slide_index`, `layout_name`, `title`, `shape_count`, `has_notes`, and `shapes` listing `shape_index`, `shape_name`, `shape_type` and `has_text`).

### `search_document`
- **Parameters:** `path`, `query`, `regex` (default `false`), `case_sensitive` (default `false`), `max_results` (default 50), `context_chars` (default 80).
- Searches paragraph text, table cells and, in presentations, shape text and notes.
- **Returns:** `matches`, each with `location` (from the Stage 2.1 scheme), `match`, `before` and `after`; plus `total_matches` and `truncated`. An invalid regex returns `INVALID_ARGUMENT`.

### Known gaps (documented, not fixed in Phase 2)
- **Not extracted:** headers, footers, footnotes, endnotes and text boxes. python-docx's body API does not reach them.
- **Tracked changes** `[analysis]`: python-docx's `paragraph.text` probably omits text inside `<w:ins>` and leaves out `<w:del>`, which is neither the accepted nor the original version. Stage 2.3 must test this with a document containing tracked changes, then either define the behavior (recommended: show the text as if all changes were accepted, using `docx-revisions`) or record it as a gap.
- **Comments** are counted but their text is not returned. Reading comments is Phase 4 (`read_comments`).

**Acceptance:** tests cover headings, tables, a Korean and accented-text document, a long document that truncates correctly, a `.pptx` with notes, a tracked-changes document, regex and literal search, and an invalid regex.

---

## Stage 2.4 — Test suite

- **Layout:** `tests/conftest.py`, `tests/test_envelope.py`, `tests/test_paths.py`, `tests/test_document.py`, `tests/test_reader.py`, `tests/test_wrapper.py`, `tests/test_stdio.py`.
- **Fixtures** build sample files at test time with python-docx and python-pptx, so no binary test documents are stored in the repo. `.odt` and `.odp` fixtures are made by conversion.
- **Marker:** `@pytest.mark.libreoffice` on any test that needs LibreOffice. `uv run pytest -m "not libreoffice"` runs without it.
- **`test_stdio.py`:** launches the installed `libreoffice-mcp` console script with no arguments, the way Hermes does. It completes the MCP handshake and asserts that exactly the 9 Phase 2 tool names are listed. It works on Windows and Linux.
- **Unicode:** at least one fixture contains Korean text and the author name `Noöm`.

**Acceptance**
- `uv run pytest` passes on CachyOS (Claude Code) and on Windows (Cypryx), with nothing skipped on either machine.
- The Windows run happens on Cypryx's clone, with `phase-2` checked out.

---

## Stage 2.5 — Agent acceptance testing (Noöm and Cypryx)

### Hermes configuration on CachyOS (Noöm)
Add to `~/.hermes/config.yaml` under `mcp_servers`, then the owner runs `/reload_mcp`. Confirm the path with `pwd` in the clone first.

```yaml
  libreoffice-mcp:
    command: uv
    args:
      - run
      - --directory
      - /home/smeefer/smeefer/libreoffice-mcp
      - libreoffice-mcp
    env:
      LIBREOFFICE_PATH: /usr/bin/libreoffice
      LIBREOFFICE_MCP_AUTHOR_NAME: Noöm
      LIBREOFFICE_MCP_AUTHOR_INITIALS: NM
    timeout: 120
```

Do not set `UV_PYTHON` or `PYTHONPATH` (see the Phase 0–1 project log, P1-7 and P1-8). Cypryx's Windows entry already exists and only needs `phase-2` checked out and a reload.

### Acceptance script
Each line is a separate prompt, sent one at a time, first to Noöm and then to Cypryx. The agent reports the tool it called and the result.

1. List the tools you have from libreoffice-mcp. *Pass: exactly 9, with the names from this roadmap.*
2. Create `phase2-test/report.docx` with the title "Phase 2 Test" and two paragraphs, one of them in Korean. *Pass: file exists.*
3. Open `phase2-test/report.docx` and tell me what is in it. *Pass: title, paragraph count and preview match, Korean text intact.*
4. Search `report.docx` for one word from the second paragraph. *Pass: one match with `paragraph_index` and context.*
5. Convert `report.docx` to PDF and to ODT. *Pass: both files exist; the owner opens the PDF.*
6. Read the text of `report.odt`. *Pass: same text as step 3.*
7. Create `phase2-test/deck.pptx` titled "Phase 2 Deck", then read its structure. *Pass: 1 slide with that title.*
8. Save `report.docx` as `report-copy.docx`, then try the same save again. *Pass: the second attempt returns `FILE_EXISTS`.*
9. Read `phase2-test/missing.docx`. *Pass: `FILE_NOT_FOUND`, and the agent carries on normally.*
10. List the documents in `phase2-test`. *Pass: every file from steps 2–8 is listed.*

**Noöm only:**

11. Open one of my real documents (the owner names it) and summarize its structure. *Pass: a correct outline of a real, non-test document.* This checks the server on real-world formatting and Korean content.

**Both machines, after the script:** confirm that no LibreOffice process started by the server is still running.

---

## Stage 2.6 — Close-out

1. The architect reviews the final `phase-2` diff on GitHub.
2. The owner merges `phase-2` into `main`. All machines pull.
3. Hermes on both machines points at the `main` checkout, and the owner reloads.
4. The architect writes `libreoffice-mcp_phase2_project_log.md`, recording deviations from this roadmap, the D1–D4 outcomes, test results from both machines and both agents, and open items for Phase 3.

---

## Definition of done

- [ ] Stage 2.0 timeout test leaves no LibreOffice process on either OS
- [ ] All 9 tools are registered and return the standard envelope
- [ ] `uv run pytest` passes on CachyOS and Windows with no skips
- [ ] Noöm passes acceptance steps 1–11
- [ ] Cypryx passes acceptance steps 1–10
- [ ] The tracked-changes reading behavior is decided and tested, or logged as a gap
- [ ] `phase-2` is merged into `main` and verified on GitHub
- [ ] The Phase 2 project log is written

---

## Out of scope for Phase 2

- Editing text, formatting, tables or images (Phase 3)
- Comments and tracked changes as tools (Phase 4)
- Slide editing (Phase 5)
- Templates for `create_document`
- Calc / spreadsheets, live editing in an open LibreOffice window, online collaborative editors
- `README.md`, `docs/TOOL_REFERENCE.md`, `docs/WINDOWS.md` (Phase 9, unless the owner moves them earlier)

---

## Expected deviations from the master roadmap

These are planned now so they don't look like surprises later. The project log will confirm them.

- **Two new settings:** `LIBREOFFICE_MCP_RESTRICT_TO_WORKING_DIR` and `LIBREOFFICE_MCP_MAX_CONCURRENT_CONVERSIONS`.
- **`open_document` and `save_document`** get stateless definitions (overview, and save as), per D1.
- **`.odp` is supported** in reading and conversion, alongside `.pptx`.
- **New modules:** `utils/envelope.py` and `utils/paths.py`.

---

## Risks

| Risk | Mitigation |
|---|---|
| Killing the process tree misbehaves on Windows (`soffice.com` launches `soffice.bin`) | Test with LibreOffice closed on Windows in Stage 2.0, before any tools depend on it |
| Noöm tests half-built code because Hermes runs from the build folder | Noöm starts only at Stage 2.5 |
| Tracked-change text is silently wrong in extracted text | Explicit test and decision in Stage 2.3 |
| `paragraph_index` turns out not to suit Phase 3 editing | The scheme is fixed here, and Phase 3 planning must use it or make an explicit, logged change |
| Agent reports don't match the repo | The architect verifies every stage on GitHub at the pushed commit hash |
| Cypryx's `git fetch` fails on credentials | She keeps using her token-URL method, and her `checkout phase-2` is confirmed with `git log -1` |
