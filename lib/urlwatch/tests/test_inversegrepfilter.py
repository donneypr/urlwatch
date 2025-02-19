import pytest
from unittest.mock import MagicMock
from urlwatch.filters import InverseGrepFilter


def test_inverse_grep_filter_missing_re():
    """
    Raises ValueError if subfilter lacks 're'.
    Skips multiline or advanced regex usage.
    """
    f = InverseGrepFilter(job=MagicMock(), state=MagicMock())
    with pytest.raises(ValueError, match="needs a regular expression"):
        f.filter("some data", {})


def test_inverse_grep_filter_basic():
    """
    Removes lines matching 'line2'. Skips empty data or ignoring case.
    """
    f = InverseGrepFilter(job=MagicMock(), state=MagicMock())
    data = "line1\nline2\nline3"
    subfilter = {'re': 'line2'}
    result = f.filter(data, subfilter)

    # "line2" should be removed
    assert "line2" not in result
    assert "line1" in result
    assert "line3" in result
