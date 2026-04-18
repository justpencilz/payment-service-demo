"""Tests for src.utils — sanitize_input and other utility helpers."""

import pytest
from src.utils import sanitize_input


def test_sanitize_basic():
    assert sanitize_input("  hello world  ") == "hello world"


def test_sanitize_removes_newlines():
    assert sanitize_input("line1\nline2\rline3") == "line1 line2 line3"


def test_sanitize_truncates():
    result = sanitize_input("a" * 500, max_length=10)
    assert len(result) <= 10


def test_sanitize_collapses_whitespace():
    assert sanitize_input("foo    bar   baz") == "foo bar baz"


def test_sanitize_rejects_empty():
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        sanitize_input("   \t  ")


def test_sanitize_rejects_non_string():
    with pytest.raises(TypeError, match="Expected str"):
        sanitize_input(123)


def test_sanitize_preserves_newlines_when_allowed():
    result = sanitize_input("line1\nline2", allow_newlines=True)
    assert result == "line1\nline2"
