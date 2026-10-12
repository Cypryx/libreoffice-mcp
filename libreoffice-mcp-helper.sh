#!/usr/bin/env bash
# libreoffice-mcp-helper.sh
#
# Verification and smoke-test script for the libreoffice-mcp server.
# Works on both CachyOS (POSIX) and Windows (git-bash/MSYS) shells.
#
# Commands:
#   ./libreoffice-mcp-helper.sh check    - verify prerequisites (binary, python, uv)
#   ./libreoffice-mcp-helper.sh test     - run the test suite (pytest)
#   ./libreoffice-mcp-helper.sh demo     - end-to-end: create .odt, convert to .pdf
#   ./libreoffice-mcp-helper.sh version  - print server + LibreOffice versions

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# Resolve the LibreOffice binary like the server does, preferring soffice.com on Windows.
find_binary() {
    if [[ -n "${LIBREOFFICE_PATH:-}" && -f "${LIBREOFFICE_PATH}" ]]; then
        echo "${LIBREOFFICE_PATH}"
        return
    fi
    if command -v libreoffice >/dev/null 2>&1; then
        command -v libreoffice
        return
    fi
    local win_bin="/c/Program Files/LibreOffice/program/soffice.com"
    [[ -f "$win_bin" ]] && { echo "$win_bin"; return; }
    echo ""
}

case "${1:-}" in
  check)
    echo "== libreoffice-mcp helper: check =="
    # Delegate LibreOffice resolution/version to the server's own commands:
    # they use subprocess.run (no shell pipe), which is deterministic, whereas
    # `soffice.com --version` via a bash pipe on Windows can race on first run.
    bin="$(find_binary)"
    if [[ -n "$bin" ]]; then
        echo "  [OK] LibreOffice binary: $bin"
        env -u PYTHONPATH uv run libreoffice-mcp check-libreoffice 2>&1 | sed 's/^/       /'
    else
        echo "  [FAIL] LibreOffice binary not found (set LIBREOFFICE_PATH)"
    fi
    python --version 2>/dev/null || echo "  [FAIL] python not found"
    uv --version 2>/dev/null || echo "  [FAIL] uv not found"
    ;;
  test)
    echo "== libreoffice-mcp helper: test =="
    uv run pytest -q
    ;;
  demo)
    echo "== libreoffice-mcp helper: demo =="
    bin="$(find_binary)"
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    # Create a minimal valid .odt via the server package's config import path:
    # we build it directly here with python to avoid requiring the server tools yet.
    (cd "$tmp" && uv run --project "$REPO_DIR" python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"""$REPO_DIR""")/ "src"))
out = Path("demo.odt")
import zipfile
z = zipfile.ZipFile(out, "w")
z.writestr("mimetype", "application/vnd.oasis.opendocument.text")
z.writestr("META-INF/manifest.xml", (
    '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
    'manifest:version="1.2">'
    '<manifest:file-entry manifest:full-path="/" manifest:version="1.2" manifest:media-type="application/vnd.oasis.opendocument.text"/>'
    '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
    '<manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>'
    '</manifest:manifest>'))
z.writestr("styles.xml", ('<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.2"><office:styles/></office:document-styles>'))
z.writestr("content.xml", ('<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.2"><office:body><office:text><text:p>libreoffice-mcp demo document</text:p></office:text></office:body></office:document-content>'))
z.close()
print("created demo.odt")
PY
    )
    echo "  Converting demo.odt -> demo.pdf ..."
    "$bin" --headless --norestore --convert-to pdf --outdir "$tmp" "$tmp/demo.odt" >/dev/null 2>&1
    if [[ -f "$tmp/demo.pdf" ]]; then
        echo "  [OK] demo.pdf produced: $(stat -c%s "$tmp/demo.pdf" 2>/dev/null || du -h "$tmp/demo.pdf" | cut -f1) bytes"
    else
        echo "  [FAIL] conversion did not produce demo.pdf"
    fi
    ;;
  version)
    echo "server: $(env -u PYTHONPATH uv run libreoffice-mcp version 2>/dev/null)"
    echo "libreoffice:"
    env -u PYTHONPATH uv run libreoffice-mcp check-libreoffice 2>&1 | sed 's/^/  /'
    ;;
  *)
    echo "Usage: $0 {check|test|demo|version}"
    exit 1
    ;;
esac