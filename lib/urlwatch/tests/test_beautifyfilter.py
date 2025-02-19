import pytest
import logging
from unittest.mock import patch, MagicMock
from urlwatch.filters import BeautifyFilter


def test_beautify_filter_missing_bs4():
    """
    1. If BeautifulSoup is None, we raise ImportError immediately.
    This ensures we cover the branch where `BeautifulSoup` is missing.
    """
    # We patch "BeautifulSoup" to be None, simulating an environment without bs4 installed.
    with patch("urlwatch.filters.BeautifulSoup", new=None):
        bf = BeautifyFilter(job=MagicMock(), state=MagicMock())
        # The filter call should raise ImportError with a specific message.
        with pytest.raises(ImportError, match="Please install BeautifulSoup"):
            bf.filter("<html></html>", None)


def test_beautify_filter_all_present():
    """
    2. All dependencies installed, and both <script> and <style> have .string.
       Covers the main "happy path" where jsbeautifier and cssbeautifier are used.
    """
    # HTML containing both a <script> and a <style> so we can check beautification of both.
    sample_html = """
    <html>
      <head>
        <style>body { color: red; }</style>
      </head>
      <body>
        <script>console.log("hello");</script>
      </body>
    </html>
    """

    # We patch BeautifulSoup, jsbeautifier, and cssbeautifier to be present.
    with patch("urlwatch.filters.BeautifulSoup") as mock_bs4, \
         patch("urlwatch.filters.jsbeautifier") as mock_js, \
         patch("urlwatch.filters.cssbeautifier") as mock_css:
        # Mock the beautify calls to return specific strings.
        mock_js.beautify.return_value = "// beautified JS"
        mock_css.beautify.return_value = "/* beautified CSS */"

        # Mock a BeautifulSoup instance that finds a <script> and a <style>.
        mock_soup_instance = MagicMock()
        mock_script_tag = MagicMock()
        mock_script_tag.string = 'console.log("hello");'
        mock_style_tag = MagicMock()
        mock_style_tag.string = 'body { color: red; }'

        def fake_find_all(tag):
            if tag == 'script':
                return [mock_script_tag]
            elif tag == 'style':
                return [mock_style_tag]
            return []

        mock_soup_instance.find_all.side_effect = fake_find_all
        # prettify() is called at the end of BeautifyFilter; we mock its return.
        mock_soup_instance.prettify.return_value = "prettified HTML"
        mock_bs4.return_value = mock_soup_instance

        # Instantiate and call the filter with the sample HTML.
        bf = BeautifyFilter(job=MagicMock(), state=MagicMock())
        result = bf.filter(sample_html, None)

        # Verify that both the <script> and <style> got replaced with the "beautified" strings.
        assert mock_script_tag.string == "// beautified JS"
        assert mock_style_tag.string == "/* beautified CSS */"
        # The final prettified output.
        assert result == "prettified HTML"


def test_beautify_filter_js_missing(caplog):
    """
    3. jsbeautifier is None => logs an info message and does NOT beautify <script>.
       Covers the branch where jsbeautifier is unavailable, skipping script beautification.
    """
    caplog.set_level(logging.INFO)
    sample_html = "<html><body><script>console.log('test');</script></body></html>"

    with patch("urlwatch.filters.jsbeautifier", new=None), \
         patch("urlwatch.filters.BeautifulSoup") as mock_bs4, \
         patch("urlwatch.filters.cssbeautifier") as mock_css:
        # cssbeautifier is present here but won't be used if there's no <style>.
        mock_css.beautify.return_value = "/* beautified CSS */"

        # Mock a BeautifulSoup instance that only finds a <script> tag.
        mock_soup_instance = MagicMock()
        mock_script_tag = MagicMock()
        mock_script_tag.string = "console.log('test');"

        def fake_find_all(tag):
            if tag == 'script':
                return [mock_script_tag]
            return []

        mock_soup_instance.find_all.side_effect = fake_find_all
        mock_soup_instance.prettify.return_value = "prettified HTML"
        mock_bs4.return_value = mock_soup_instance

        bf = BeautifyFilter(job=MagicMock(), state=MagicMock())
        result = bf.filter(sample_html, None)

        # Since jsbeautifier is None, the script remains unchanged.
        assert "console.log('test');" in mock_script_tag.string
        assert result == "prettified HTML"

        # The code logs an info message about jsbeautifier not being installed.
        log_msgs = [rec.message for rec in caplog.records]
        assert '"jsbeautifier" is not installed' in " ".join(log_msgs)


def test_beautify_filter_css_missing(caplog):
    """
    4. cssbeautifier is None => logs an info message and does NOT beautify <style>.
       Covers the branch where cssbeautifier is unavailable, skipping style beautification.
    """
    caplog.set_level(logging.INFO)
    sample_html = "<html><head><style>body { color:red; }</style></head></html>"

    with patch("urlwatch.filters.cssbeautifier", new=None), \
         patch("urlwatch.filters.BeautifulSoup") as mock_bs4, \
         patch("urlwatch.filters.jsbeautifier") as mock_js:
        # jsbeautifier is present here but won't be used if there's no <script>.
        mock_js.beautify.return_value = "// beautified JS"

        # Mock a BeautifulSoup instance that only finds a <style> tag.
        mock_soup_instance = MagicMock()
        mock_style_tag = MagicMock()
        mock_style_tag.string = "body { color:red; }"

        def fake_find_all(tag):
            if tag == 'style':
                return [mock_style_tag]
            return []

        mock_soup_instance.find_all.side_effect = fake_find_all
        mock_soup_instance.prettify.return_value = "prettified HTML"
        mock_bs4.return_value = mock_soup_instance

        bf = BeautifyFilter(job=MagicMock(), state=MagicMock())
        result = bf.filter(sample_html, None)

        # Since cssbeautifier is None, the style remains unchanged.
        assert "body { color:red; }" in mock_style_tag.string
        assert result == "prettified HTML"

        # The code logs an info message about cssbeautifier not being installed.
        log_msgs = [rec.message for rec in caplog.records]
        assert '"cssbeautifier" is not installed' in " ".join(log_msgs)


def test_beautify_filter_script_no_string():
    """
    5. A <script> tag whose .string is None => skip beautification, no error.
       Covers the case where script tags exist but contain no text to beautify.
    """
    sample_html = "<html><body><script></script></body></html>"

    with patch("urlwatch.filters.BeautifulSoup") as mock_bs4, \
         patch("urlwatch.filters.jsbeautifier") as mock_js, \
         patch("urlwatch.filters.cssbeautifier") as mock_css:
        # Both beautifiers exist, but won't be called if script.string is None.
        mock_js.beautify.return_value = "// beautified JS"
        mock_css.beautify.return_value = "/* beautified CSS */"

        mock_soup_instance = MagicMock()
        mock_script_tag = MagicMock()
        # The .string is None, so we won't call jsbeautifier on it.
        mock_script_tag.string = None

        def fake_find_all(tag):
            if tag == 'script':
                return [mock_script_tag]
            return []

        mock_soup_instance.find_all.side_effect = fake_find_all
        mock_soup_instance.prettify.return_value = "prettified HTML"
        mock_bs4.return_value = mock_soup_instance

        bf = BeautifyFilter(job=MagicMock(), state=MagicMock())
        result = bf.filter(sample_html, None)

        # We verify that jsbeautifier was NOT called because there's no .string to beautify.
        mock_js.beautify.assert_not_called()
        assert result == "prettified HTML"


def test_beautify_filter_style_no_string():
    """
    6. A <style> tag whose .string is None => skip beautification, no error.
       Covers the case where style tags exist but contain no text to beautify.
    """
    sample_html = "<html><head><style></style></head></html>"

    with patch("urlwatch.filters.BeautifulSoup") as mock_bs4, \
         patch("urlwatch.filters.jsbeautifier") as mock_js, \
         patch("urlwatch.filters.cssbeautifier") as mock_css:
        mock_js.beautify.return_value = "// beautified JS"
        mock_css.beautify.return_value = "/* beautified CSS */"

        mock_soup_instance = MagicMock()
        mock_style_tag = MagicMock()
        # .string is None, so we won't call cssbeautifier on it.
        mock_style_tag.string = None

        def fake_find_all(tag):
            if tag == 'style':
                return [mock_style_tag]
            return []

        mock_soup_instance.find_all.side_effect = fake_find_all
        mock_soup_instance.prettify.return_value = "prettified HTML"
        mock_bs4.return_value = mock_soup_instance

        bf = BeautifyFilter(job=MagicMock(), state=MagicMock())
        result = bf.filter(sample_html, None)

        # We verify that cssbeautifier was NOT called because there's no .string to beautify.
        mock_css.beautify.assert_not_called()
        assert result == "prettified HTML"
