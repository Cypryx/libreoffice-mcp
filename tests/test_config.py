from __future__ import annotations

import logging

import pytest

from libreoffice_mcp.config import RESTRICT_TO_WORKING_DIR_ENV, load_settings


def restrict(value: str | None):
    env = {} if value is None else {RESTRICT_TO_WORKING_DIR_ENV: value}
    return load_settings(env=env).restrict_to_working_dir


def test_unset_is_false():
    assert restrict(None) is False


def test_empty_is_false():
    assert restrict("") is False


@pytest.mark.parametrize("value", ["false", "0", "no", "off", "FALSE", " off "])
def test_false_values(value, caplog):
    with caplog.at_level(logging.WARNING, logger="libreoffice_mcp"):
        assert restrict(value) is False
    assert caplog.records == []


@pytest.mark.parametrize("value", ["true", "1", "yes", "on", "TRUE", " On "])
def test_true_values(value, caplog):
    with caplog.at_level(logging.WARNING, logger="libreoffice_mcp"):
        assert restrict(value) is True
    assert caplog.records == []


@pytest.mark.parametrize("value", ["banana", "ture"])
def test_unrecognized_fails_closed_and_warns(value, caplog, capsys):
    with caplog.at_level(logging.WARNING, logger="libreoffice_mcp"):
        assert restrict(value) is True
    warnings = [r for r in caplog.records if r.name == "libreoffice_mcp" and r.levelno == logging.WARNING]
    assert len(warnings) == 1
    text = warnings[0].getMessage()
    assert "not recognized" in text
    assert "strict mode" in text
    assert capsys.readouterr().out == ""


def test_other_defaults_unchanged():
    s = load_settings(env={})
    assert s.restrict_to_working_dir is False
    assert s.max_concurrent_conversions == 2
    assert s.conversion_timeout_seconds == 30
    assert s.author_name == "AI Assistant"
