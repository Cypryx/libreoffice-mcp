# libreoffice-mcp — Project Log: Phase 0 and Phase 1

**Repository:** https://github.com/Cypryx/libreoffice-mcp
**Period:** 2026-10-12 to 2026-10-13 (KST)
**State at close:** `main` at `953f83e`, 5 commits. Phase 1 closed.
**Written by:** the architect / observer.

The roadmap (`docs/roadmaps/`) is the record of the **original plan** and is not edited. This log is the record of **what was actually built**. Where the build differed from the roadmap, the difference is recorded here.

### Evidence tags

| Tag | Meaning |
|---|---|
| `[repo]` | Read directly from the GitHub repository and confirmed. |
| `[reported]` | Reported from a terminal by Cypryx (Windows) or Claude Code (CachyOS). Not independently verifiable from the repo. |
| `[analysis]` | Architect's inference. Not tested. |

### Machines

| Name | Machine | Role |
|---|---|---|
| Cypryx | Windows PC, Hermes agent | Owns the repo; builds, commits and pushes |
| Noöm machine | CachyOS laptop | Priority machine for document work; pulls and verifies |

---

## Timeline

| Commit | Description |
|---|---|
| `343589…` | Initial commit (hash as reported, truncated) |
| `198624f` | Add AGPL-3.0 license |
| `1486fa9` | Add the master roadmap to the repo |
| `3ccee8f` | Phase 1 scaffold and docx comment + tracked-changes spike |
| `953f83e` | Isolate each headless LibreOffice call in its own temporary profile |

---

## Phase 0 — Prerequisites

**Result: PASS on both machines.** `[reported]`

| Check | CachyOS | Windows |
|---|---|---|
| LibreOffice ≥ 24.2 | 26.8.0.3 | 26.2.6.3 |
| Binary | `/usr/bin/libreoffice` | `C:\Program Files\LibreOffice\program\soffice.com` |
| Python ≥ 3.12 | 3.13.14 | 3.12.9 |
| uv | 0.10.4 | 0.11.1 |
| git | 2.56.0 | 2.51.0 |
| Headless `.odt` → `.pdf` | pass | pass (13.9 KB PDF) |

### P0-1 Windows needs `soffice.com`, not `soffice.exe` `[reported]`
- **Roadmap said:** Phase 8 uses `soffice.exe` as the Windows binary.
- **Actual:** `soffice.com` is used. `soffice.exe` is a GUI launcher; called headless from a shell, it detached or hung (the first `--version` call timed out at 60 s).
- **Also found:** headless calls need `--headless --norestore` and a timeout, and the first run is slow because it builds a LibreOffice profile.

### P0-2 A valid ODT package needs more than `content.xml` `[reported]`
- **Roadmap said:** nothing.
- **Actual:** a hand-built `.odt` failed to load until it included `META-INF/manifest.xml` and `styles.xml`. This matters for any code that builds `.odt` files directly.

---

## Phase 1 — Project Scaffold

### P1-1 What was built `[repo]`
- **Package:** `src/libreoffice_mcp/` with `__init__.py` (`__version__ = "0.1.0"`), `server.py`, `config.py`, `utils/libreoffice.py`, `utils/converters.py`, and an empty `tools/`.
- **Project files:** `pyproject.toml`, `uv.lock`, `.python-version`, `.env.example`, `.gitignore`, `libreoffice-mcp-helper.sh`.
- **Scripts:** `scripts/spike_docx.py`, `scripts/stdio_smoke.py`, `scripts/hermes_launch_test.py`.
- **Not built:** `tests/`, `docs/TOOL_REFERENCE.md`, `docs/CONFIGURATION.md`, `docs/AGENT_PROMPTING.md`, `docs/WINDOWS.md`. The README is the GitHub default (two lines).
- **Tools registered:** 0, which is correct for Phase 1.

### P1-2 `mcp` pinned below 2 `[repo]`
- **Roadmap said:** `mcp[cli]>=1.0.0`.
- **Actual:** `mcp[cli]>=1.0.0,<2`. `server.py` imports `mcp.server.fastmcp.FastMCP`.
- **Why:** `[reported]` mcp 2.x renamed `FastMCP` to `MCPServer`. The resolved version is 1.30.0. Migrating to 2.x is deferred.

### P1-3 Python pin `[repo]`
- **Roadmap said:** `requires-python >=3.12`. A `.python-version` file was not mentioned.
- **Actual:** `requires-python = ">=3.12"` and `.python-version` = `3.12`. `uv init` had generated 3.13, which was changed.
- **Why:** both machines have several interpreters (conda on CachyOS, miniconda on Windows). The pin keeps uv on one version.
- **CachyOS check:** `[reported]` `uv sync` succeeded with uv 0.10.4, even though `pyproject.toml` requires the `uv_build>=0.11.1,<0.12.0` build backend.

### P1-4 Entry point behavior `[repo]`
- **Roadmap said:** `libreoffice-mcp = "libreoffice_mcp.server:main"`, smoke-tested with `--help`. What happens with no arguments was not specified.
- **Actual:** with no arguments, `main()` starts the stdio MCP server, which is how Hermes launches it. With arguments, it runs a Typer CLI with `version`, `serve`, `check-libreoffice` and `--help`.
- **Why:** `[reported]` the roadmap's Hermes config calls the binary with no subcommand. The first version printed help instead, and the connection closed.
- **Loose ends:** `typer` is imported but not declared in `pyproject.toml`; it is only present because `mcp[cli]` pulls it in. The `serve --timeout` option is never used. `no_args_is_help=True` can no longer be reached.

### P1-5 Configuration `[repo]`
- **Actual:** the variables match the roadmap: `LIBREOFFICE_PATH`, `LIBREOFFICE_MCP_WORKING_DIR`, `LIBREOFFICE_MCP_AUTHOR_NAME`, `LIBREOFFICE_MCP_AUTHOR_INITIALS`, `LIBREOFFICE_MCP_CONVERSION_TIMEOUT`. Defaults are `libreoffice`, `~/Documents/libreoffice-mcp`, `AI Assistant`, `AI` and `30`.
- **Author override:** `Settings.effective_author_name()` and `effective_author_initials()` support a per-call override, as the roadmap's Phase 4 requires.
- **Timeout:** 30 seconds, as in the roadmap. A change to 60 was proposed and not applied (see Open items).

### P1-6 Binary resolution `[repo]` `[reported]`
- **Actual:** `resolve_libreoffice_binary` uses `LIBREOFFICE_PATH` when it points at a file. Otherwise it looks the value up on PATH (so the bare default `libreoffice` works), then probes the Windows install folder, preferring `soffice.com`.
- **Bug fixed during the build:** `[reported]` the first version treated any configured value as a file path, so the default `libreoffice` failed.
- **Notes:** the Windows probe runs on every platform, which is harmless on Linux. There is no fallback to a `soffice` command on PATH.

### P1-7 Hermes launches the server; `UV_PYTHON` removed `[reported]`
- **Roadmap said:** the Phase 8 Hermes block sets `UV_PYTHON` to the miniconda interpreter.
- **Actual:** the working Windows config has no `UV_PYTHON`. Pointing it at Python 3.13.9 made uv delete and rebuild the project's 3.12 `.venv` on every launch.
- **Result:** `hermes mcp test libreoffice-mcp` connected (600 ms, 0 tools), and `/reload_mcp` reported `➕ Added: libreoffice-mcp` alongside agentmail and walrus-memory (50 tools across 3 servers).
- The Hermes config lives outside the repo, so this cannot be checked from GitHub.

### P1-8 `PYTHONPATH` `[reported]`
- **Roadmap said:** nothing.
- **Actual:** Hermes puts its own venv on `PYTHONPATH` in the shells it spawns. In Cypryx's shell this shadowed the project's `.venv` and loaded a broken `mcp`/`pydantic`, so manual `uv run` needs `env -u PYTHONPATH`.
- **When Hermes launches the server:** it connects with or without a blank `PYTHONPATH` line (743 ms, 0 tools, without the line). The line was removed from the config.

### P1-9 `hermes mcp add` dropped environment variables `[reported]`
- **Actual:** the CLI absorbed the `--env` values into the positional args and kept one of four variables. The config block was edited by hand.
- **Implication:** setup docs should tell people to edit `config.yaml` directly.

### P1-10 Library spike: comments and tracked changes coexist `[repo]` `[reported]`
- **Roadmap said:** "python-docx v1.2.0 native `add_comment()`", with no signature.
- **Actual API** `[repo]` (from `scripts/spike_docx.py`):
  - `Document.add_comment(runs=, text=, author=, initials=)`
  - `RevisionParagraph.from_paragraph(para).add_tracked_insertion(text, author=)` from `docx-revisions` (resolved 0.1.5)
- **Result** `[reported]`: one `.docx` contained both a comment (`word/comments.xml`, `w:commentRangeStart`) and a tracked insertion (`<w:ins>`). The comment read back after save and reload (`author='Spike'`, `initials='SP'`). The insertion kept its author. The file converted to PDF through the wrapper.
- **Not proven** `[analysis]`: that comments and tracked changes are visible in LibreOffice Writer (PDF export hides them by default), or that they survive a LibreOffice round trip. The Phase 4 visual check is still needed.

### P1-11 Helper script `[repo]`
- **Roadmap said:** `check`, `test` and `demo` commands.
- **Actual:** `check` finds the binary in bash and gets the version from `env -u PYTHONPATH uv run libreoffice-mcp check-libreoffice`. A `version` command was added.
- **Why:** `[reported]` on Windows, `soffice.com --version` returned empty output inside a bash `$(...)`. The cause was not settled and the investigation was stopped.
- **Gaps:** `test` runs `uv run pytest -q`, but pytest is not a declared dependency and there is no `tests/` folder. In `demo`, `$REPO_DIR` is not expanded inside the quoted heredoc; this is harmless because the value is unused.

### P1-12 Per-call temporary LibreOffice profile (commit `953f83e`) `[repo]` `[reported]`
- **Roadmap said:** "LibreOffice headless wrapper with timeout handling". A per-call profile was not in the roadmap; the architect added it as a requirement.
- **Actual** `[repo]` (read at commit `953f83e`): `run_headless` imports `tempfile` and runs the subprocess inside `with tempfile.TemporaryDirectory() as profile_dir:`. The command is `[binary, "--headless", "--norestore", f"-env:UserInstallation={profile_uri}", *args]`, with the URI built by `Path.as_uri()`. The diff was 30 insertions and 22 deletions in one file.
- **Windows results** `[reported]`: the spike converted in 3.13 s cold, and no temp profile folders were left after success or after a forced 0.05 s timeout.
- **CachyOS results** `[reported]` (Claude Code, 4 conversions at once, 3 runs each):

| | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Without the fix | 4/4, 0.3 s | 4/4, 0.3 s | 4/4, 0.3 s |
| With the fix | 4/4, 2.4 s | 4/4, 0.7 s | 4/4, 0.8 s |

- **The baseline did not test collisions** `[reported]` `[analysis]`: a LibreOffice window was already open (PID 23067). Headless calls using the default profile were most likely handed to that window, which explains the 0.3 s times. That itself supports the fix: without isolation, agent conversions run inside the user's open LibreOffice session.
- **Timeout test** `[reported]`: at 1.0 s the conversion finished in 0.8 s, so no timeout happened. At 0.2 s it raised `LibreOfficeError` and left no temp folders. Only the user's own LibreOffice process remained afterwards.
- **Still untested:** a timeout kills the launcher only. On Linux `/usr/bin/libreoffice` is a shell script, so an orphaned `soffice.bin` may survive. Testing this needs LibreOffice closed.
- **Minor bug:** the timeout message formats seconds with `:.0f`, so sub-second timeouts print `0s`.

### P1-13 Phase 1 close-out `[repo]` `[reported]`
- `953f83e` was pushed. `git ls-remote origin main` matched local HEAD on Windows, and CachyOS fast-forwarded `3ccee8f..953f83e` with the same one-file diff.
- **Repo state:** Windows has untracked `profile_spike.docx`, `profile_spike.pdf`, `scripts/spike_profile.py` and (reportedly) `scripts/spike_docx.py`. CachyOS has untracked `CLAUDE.md`. None should be committed.
- **Unresolved discrepancy:** `scripts/spike_docx.py` is listed as untracked on Windows, but it is on GitHub `main` from `3ccee8f`. Either the local copy differs from the pushed one, or the status output was not verbatim.

---

## Process notes

- **Status reports did not always match the repo.** `953f83e`'s change was at first reported as pushed at `3ccee8f` while it was still uncommitted. A requested concurrency test was not run, and only part of a requested status check was returned. From Phase 2 on, completion is confirmed against GitHub (reading files pinned to a commit hash) or a `git pull`, not against reports alone.
- **Hermes agents work best with one task per prompt.** Multi-item prompts were partly done or misread.
- **Verification that costs agent tokens can move to Claude Code** on the CachyOS laptop, which also tests the priority machine.
- **GitHub caching:** a read of `main` returned an older copy of `libreoffice.py`. Reading at a specific commit hash avoided it.
- **Pushing:** the Windows clone's `origin` URL has no credentials, so `git fetch` fails and Cypryx pushes through a token URL and updates the tracking ref by hand. Her "up to date with origin/main" line is therefore not reliable on its own.

---

## Roadmap inconsistencies (noted, not corrected)

- Phase 9 says 26 tools. The five tool groups total 27 (6 + 3 + 5 + 6 + 7).
- Phase 2 says "Run full Phase 3 verification suite", which does not apply to Phase 2.
- Phase 8 and the Known Limitations table use `soffice.exe` (see P0-1).
- Phase 8's Hermes block includes `UV_PYTHON` (see P1-7).
- The license is listed as MIT, but the repo is AGPL-3.0 (see Open items).

---

## Open items carried into Phase 2

| Item | Ref | Owner |
|---|---|---|
| Confirm AGPL-3.0 is intended (the roadmap says MIT) | — | Project owner |
| Decide the default timeout: 30 s (current, assumed) or 60 s | P1-5 | Project owner |
| Kill the whole process tree on timeout, and test with LibreOffice closed | P1-12 | Phase 2 |
| Fix the `0s` timeout message | P1-12 | Phase 2 |
| Declare `typer`; add a dev group with `pytest`; add `tests/` | P1-4, P1-11 | Phase 2 |
| Delete `hermes_launch_test.py`; make `stdio_smoke.py` cross-platform and test the bare launch path | P1-1 | Phase 2 |
| Check comments and tracked changes visually in LibreOffice Writer, and after a LibreOffice round trip | P1-10 | Phase 4 |
| Resolve the `scripts/spike_docx.py` discrepancy; delete local spike files | P1-13 | Cypryx |
| Write `docs/WINDOWS.md` | P0-1, P1-7, P1-8 | Phase 2 or later |
| Decide whether the owner's GitHub account can push to the repo, which determines who builds Phase 2 | — | Project owner |
