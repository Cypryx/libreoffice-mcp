from __future__ import annotations

import os
from pathlib import Path

import pytest

from libreoffice_mcp.config import Settings
from libreoffice_mcp.utils.envelope import ToolError, tool_envelope
from libreoffice_mcp.utils.paths import (
    require_existing_file,
    resolve_directory,
    resolve_output_file,
    resolve_path,
)


def make_settings(work: Path, restrict: bool = False) -> Settings:
    return Settings(working_dir=work, restrict_to_working_dir=restrict)


@pytest.fixture
def work(tmp_path: Path) -> Path:
    d = tmp_path / "work"
    d.mkdir()
    return d


def can_symlink(tmp_path: Path) -> bool:
    probe_target = tmp_path / "_probe_target"
    probe_target.mkdir(exist_ok=True)
    try:
        os.symlink(probe_target, tmp_path / "_probe_link", target_is_directory=True)
    except OSError:
        return False
    return True


@pytest.fixture
def symlinks_ok(tmp_path: Path) -> None:
    if not can_symlink(tmp_path):
        pytest.skip("os.symlink is not permitted on this system (e.g. Windows without privileges)")


def code_of(excinfo) -> str:
    return excinfo.value.code


# --- resolve_path -----------------------------------------------------------

def test_relative_resolves_under_working_dir(work):
    out = resolve_path("a.docx", make_settings(work))
    assert out.is_absolute()
    assert out == work.resolve() / "a.docx"


def test_korean_filename_and_umlaut_dir(tmp_path):
    work = tmp_path / "Noöm"
    work.mkdir()
    out = resolve_path("보고서.docx", make_settings(work))
    assert out == work.resolve() / "보고서.docx"


def test_tilde_expands_to_patched_home(work):
    home = Path(os.environ["HOME"]).resolve()
    out = resolve_path("~/x.docx", make_settings(work))
    assert out == home / "x.docx"


def test_unrestricted_allows_outside(work, tmp_path):
    s = make_settings(work)
    outside = tmp_path / "elsewhere" / "x.docx"
    assert resolve_path(str(outside), s) == outside.resolve()
    assert resolve_path("../x.docx", s) == (tmp_path / "x.docx").resolve()


def test_restricted_inside_and_self_ok(work):
    s = make_settings(work, restrict=True)
    assert resolve_path("sub/a.docx", s) == work.resolve() / "sub" / "a.docx"
    assert resolve_path(str(work / "a.docx"), s) == work.resolve() / "a.docx"
    assert resolve_path(str(work), s) == work.resolve()


def test_restricted_absolute_outside(work, tmp_path):
    with pytest.raises(ToolError) as e:
        resolve_path(str(tmp_path / "other.docx"), make_settings(work, True))
    assert code_of(e) == "PATH_NOT_ALLOWED"
    assert str(work.resolve()) in e.value.message


def test_restricted_dotdot_escape(work):
    with pytest.raises(ToolError) as e:
        resolve_path("../escape.docx", make_settings(work, True))
    assert code_of(e) == "PATH_NOT_ALLOWED"


def test_restricted_shared_prefix_sibling(work, tmp_path):
    evil = tmp_path / "work-evil"
    evil.mkdir()
    with pytest.raises(ToolError) as e:
        resolve_path(str(evil / "x.docx"), make_settings(work, True))
    assert code_of(e) == "PATH_NOT_ALLOWED"


def test_restricted_symlink_pointing_outside(work, tmp_path, symlinks_ok):
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(outside, work / "link", target_is_directory=True)
    with pytest.raises(ToolError) as e:
        resolve_path("link/x.docx", make_settings(work, True))
    assert code_of(e) == "PATH_NOT_ALLOWED"


def test_restricted_symlink_pointing_inside(work, symlinks_ok):
    (work / "real").mkdir()
    os.symlink(work / "real", work / "link", target_is_directory=True)
    out = resolve_path("link/x.docx", make_settings(work, True))
    assert out == work.resolve() / "real" / "x.docx"


def test_restricted_working_dir_itself_symlink(tmp_path, symlinks_ok):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    os.symlink(real, link, target_is_directory=True)
    s = make_settings(link, restrict=True)
    assert resolve_path("a.docx", s) == real.resolve() / "a.docx"
    assert resolve_path(str(link / "b.docx"), s) == real.resolve() / "b.docx"


@pytest.mark.parametrize("raw", ["", "   ", "a\x00b"])
def test_invalid_strings(work, raw):
    with pytest.raises(ToolError) as e:
        resolve_path(raw, make_settings(work))
    assert code_of(e) == "INVALID_ARGUMENT"


# --- require_existing_file --------------------------------------------------

def test_require_existing_file_ok(work):
    f = work / "a.docx"
    f.write_bytes(b"x")
    assert require_existing_file("a.docx", make_settings(work)) == f.resolve()


def test_require_existing_file_missing(work):
    with pytest.raises(ToolError) as e:
        require_existing_file("nope.docx", make_settings(work))
    assert code_of(e) == "FILE_NOT_FOUND"
    assert e.value.message.startswith("No file at ")


def test_require_existing_file_directory(work):
    (work / "d").mkdir()
    with pytest.raises(ToolError) as e:
        require_existing_file("d", make_settings(work))
    assert code_of(e) == "INVALID_ARGUMENT"


# --- resolve_output_file ----------------------------------------------------

def test_output_creates_parents_not_file(work):
    out = resolve_output_file("a/b/c.docx", make_settings(work))
    assert out.parent.is_dir()
    assert not out.exists()


def test_output_existing_without_overwrite(work):
    (work / "a.docx").write_bytes(b"x")
    with pytest.raises(ToolError) as e:
        resolve_output_file("a.docx", make_settings(work))
    assert code_of(e) == "FILE_EXISTS"
    assert (work / "a.docx").read_bytes() == b"x"


def test_output_existing_with_overwrite(work):
    (work / "a.docx").write_bytes(b"x")
    out = resolve_output_file("a.docx", make_settings(work), overwrite=True)
    assert out == work.resolve() / "a.docx"
    assert (work / "a.docx").read_bytes() == b"x"


def test_output_target_is_directory(work):
    (work / "d").mkdir()
    for overwrite in (False, True):
        with pytest.raises(ToolError) as e:
            resolve_output_file("d", make_settings(work), overwrite=overwrite)
        assert code_of(e) == "INVALID_ARGUMENT"


def test_output_restricted_outside_creates_nothing(work, tmp_path):
    target = tmp_path / "outside_parent" / "sub" / "x.docx"
    with pytest.raises(ToolError) as e:
        resolve_output_file(str(target), make_settings(work, True))
    assert code_of(e) == "PATH_NOT_ALLOWED"
    assert not (tmp_path / "outside_parent").exists()


def test_output_parent_creation_failure(work):
    (work / "afile").write_bytes(b"x")
    with pytest.raises(ToolError) as e:
        resolve_output_file("afile/sub/x.docx", make_settings(work))
    assert code_of(e) == "INVALID_ARGUMENT"


# --- resolve_directory ------------------------------------------------------

def test_directory_none_returns_working_dir_without_creating(tmp_path):
    work = tmp_path / "missing_work"
    out = resolve_directory(None, make_settings(work))
    assert out == work.resolve()
    assert not work.exists()


def test_directory_missing(work):
    with pytest.raises(ToolError) as e:
        resolve_directory("nope", make_settings(work))
    assert code_of(e) == "FILE_NOT_FOUND"
    assert e.value.message.startswith("No directory at ")


def test_directory_is_file(work):
    (work / "f.txt").write_bytes(b"x")
    with pytest.raises(ToolError) as e:
        resolve_directory("f.txt", make_settings(work))
    assert code_of(e) == "INVALID_ARGUMENT"


def test_directory_given_ok(work):
    (work / "d").mkdir()
    assert resolve_directory("d", make_settings(work)) == work.resolve() / "d"


# --- reads never create -----------------------------------------------------

def test_reads_never_create_working_dir(tmp_path):
    work = tmp_path / "never_created"
    s = make_settings(work)
    resolve_path("a.docx", s)
    with pytest.raises(ToolError):
        require_existing_file("a.docx", s)
    resolve_directory(None, s)
    assert not work.exists()


# --- envelope integration ---------------------------------------------------

def test_codes_surface_in_envelope(work, tmp_path):
    (work / "a.docx").write_bytes(b"x")

    @tool_envelope
    def exists() -> dict:
        resolve_output_file("a.docx", make_settings(work))
        return {}

    @tool_envelope
    def outside() -> dict:
        resolve_path(str(tmp_path / "x.docx"), make_settings(work, True))
        return {}

    assert exists()["error"]["code"] == "FILE_EXISTS"
    assert outside()["error"]["code"] == "PATH_NOT_ALLOWED"


# --- path fidelity and tilde handling ---------------------------------------

def test_name_with_surrounding_spaces_is_kept(work):
    out = resolve_path(" a.docx ", make_settings(work))
    assert out == work.resolve() / " a.docx "


def test_unresolvable_tilde_user_is_invalid_argument(work, monkeypatch):
    def broken_expanduser(self):
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.setattr(Path, "expanduser", broken_expanduser)
    with pytest.raises(ToolError) as e:
        resolve_path("~nosuchuser/x.docx", make_settings(work))
    assert code_of(e) == "INVALID_ARGUMENT"


def test_restricted_tilde_outside_working_dir(work):
    with pytest.raises(ToolError) as e:
        resolve_path("~/x.docx", make_settings(work, True))
    assert code_of(e) == "PATH_NOT_ALLOWED"
