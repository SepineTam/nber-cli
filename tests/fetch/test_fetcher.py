#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : fetch/test_fetcher.py

from datetime import date
from urllib.error import URLError
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nber_cli.config import NBER_CLI_CONFIG
from nber_cli.fetch.fetcher import (
    _NBER_REQUEST_HEADERS,
    _build_search_params,
    _load_json_sync,
    _load_text_sync,
    _parse_search_payload,
    get_nber,
)


class TestConfigDefaults:
    def test_request_defaults(self):
        assert NBER_CLI_CONFIG.request_timeout_seconds == 60
        assert NBER_CLI_CONFIG.request_retry_count == 3
        assert NBER_CLI_CONFIG.request_attempts == 4


class TestBuildSearchParams:
    def test_keyword_search_params(self):
        params = _build_search_params(" inflation ", page=2, per_page=50)
        assert params == {
            "page": 2,
            "perPage": 50,
            "q": "inflation",
        }

    def test_start_date_adds_today_as_end_date(self):
        params = _build_search_params(
            "inflation",
            start_date="2024-01-01",
            today=date(2024, 2, 3),
        )
        assert params["startDate"] == "2024-01-01"
        assert params["endDate"] == "2024-02-03"

    def test_end_date_can_be_used_by_itself(self):
        params = _build_search_params("inflation", end_date=date(2024, 1, 1))
        assert params["endDate"] == "2024-01-01"
        assert "startDate" not in params

    def test_rejects_empty_query(self):
        with pytest.raises(ValueError, match="query must not be empty"):
            _build_search_params("")

    def test_rejects_invalid_date(self):
        with pytest.raises(ValueError, match="expected YYYY-MM-DD"):
            _build_search_params("inflation", start_date="01/01/2024")

    def test_rejects_reversed_dates(self):
        with pytest.raises(ValueError, match="start_date"):
            _build_search_params(
                "inflation",
                start_date="2024-02-01",
                end_date="2024-01-01",
            )

    def test_rejects_unsupported_page_size(self):
        with pytest.raises(ValueError, match="20, 50, or 100"):
            _build_search_params("inflation", per_page=1)


class TestParseSearchPayload:
    def test_parse_result_payload(self):
        payload = {
            "totalResults": 1,
            "results": [
                {
                    "authors": [
                        '<a href="/people/person_a">Person A</a>',
                        '<a href="/people/person_b">Person &amp; B</a>',
                    ],
                    "displaydate": "January 2024",
                    "abstract": "Abstract with <em>markup</em>.",
                    "title": "A Test Paper",
                    "url": "/papers/w32000",
                }
            ],
        }
        params = {
            "q": "inflation",
            "page": 1,
            "perPage": 20,
            "startDate": "2024-01-01",
            "endDate": "2024-02-01",
        }

        results = _parse_search_payload(payload, params)

        assert results.total_results == 1
        assert results.query == "inflation"
        assert results.start_date == "2024-01-01"
        assert results.end_date == "2024-02-01"
        assert results.results[0].paper_id == 32000
        assert results.results[0].authors == ["Person A", "Person & B"]
        assert results.results[0].url == "https://www.nber.org/papers/w32000"
        assert results.results[0].abstract == "Abstract with markup."


class TestLoadTextSyncHeaders:
    def test_includes_accept_and_accept_language_headers(self):
        captured_request = {}

        class FakeResponse:
            def __init__(self):
                self.headers = MagicMock()
                self.headers.get_content_charset.return_value = "utf-8"
                self.status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"ok"

        def fake_urlopen(request, timeout, context=None):
            captured_request["headers"] = {k.lower(): v for k, v in request.headers.items()}
            return FakeResponse()

        with patch("nber_cli.fetch.fetcher.urlopen", side_effect=fake_urlopen):
            _load_text_sync("https://example.com")

        assert "accept" in captured_request["headers"]
        assert "accept-language" in captured_request["headers"]
        assert captured_request["headers"]["accept-language"] == "en-US,en;q=0.9"


class TestLoadTextSyncRetry:
    def test_retries_on_network_error(self):
        class FakeResponse:
            def __init__(self, text_value: str):
                self._text_value = text_value
                self.headers = MagicMock()
                self.headers.get_content_charset.return_value = "utf-8"
                self.status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return self._text_value.encode("utf-8")

        calls = [URLError("temporary failure"), URLError("temporary failure"), FakeResponse("ok")]

        def fake_urlopen(request, timeout, context=None):
            result = calls.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with patch("nber_cli.fetch.fetcher.urlopen", side_effect=fake_urlopen):
            with patch("nber_cli.fetch.fetcher.time.sleep") as mock_sleep:
                text = _load_text_sync("https://example.com")

        assert text == "ok"
        assert mock_sleep.call_count == 2


class TestLoadJsonSyncRetry:
    def test_retries_when_success_response_is_not_json(self):
        with (
            patch(
                "nber_cli.fetch.fetcher._load_text_sync",
                side_effect=["<html>temporary error</html>", '{"results": []}'],
            ) as mock_load,
            patch("nber_cli.fetch.fetcher.time.sleep") as mock_sleep,
        ):
            payload = _load_json_sync("https://example.com/search", {"q": "labor"})

        assert payload == {"results": []}
        assert mock_load.call_count == 2
        assert mock_sleep.call_count == 1


class TestParsePage:
    def test_parses_full_page(self):
        page = """<html><head>
<meta name="citation_title" content="Test Paper Title">
<meta name="citation_author" content="Author One">
<meta name="citation_author" content="Author Two">
<meta name="citation_publication_date" content="2024/01/15">
<meta name="citation_technical_report_number" content="w32000">
</head><body>
<div class="page-header__intro-inner">  <p>This is the <em>abstract</em> of the paper.</p></div>
<h2>Published Versions</h2>  <p>Published in <em>Journal of Economics</em>, 2024.</p>
<div class="info-grid__item">
  <h3 class="info-grid__item-title">Topics</h3>
  <div class="info-grid__item-body">
    <div class="info-grid__link-container"><a href="/topics/labor-economics">Labor Economics</a></div>
    <div class="info-grid__link-container"><a href="/taxonomy/term/571">Labor Supply &amp; Demand</a></div>
  </div>
</div>
<div class="info-grid__item">
  <h3 class="info-grid__item-title">Programs</h3>
  <div class="info-grid__item-body">
    <div class="info-grid__link-container"><a href="/programs/labor-studies">Labor Studies</a></div>
    <div class="info-grid__link-container"><a href="/programs/development">Development Economics</a></div>
  </div>
</div>
</body></html>"""
        from nber_cli.fetch.fetcher import parse_page
        result = parse_page(page)
        assert result.paper_id == 32000
        assert result.title == "Test Paper Title"
        assert result.authors == ["Author One", "Author Two"]
        assert result.date == "2024/01/15"
        assert result.abstract == "This is the abstract of the paper."
        assert result.published_version == "Published in Journal of Economics, 2024."
        assert result.topic == "Labor Economics; Labor Supply & Demand"
        assert result.programs == "Labor Studies; Development Economics"

    def test_decodes_entities_and_accepts_reordered_meta_attributes(self):
        page = """
<meta content="Women&#039;s Work &amp; Family" name="citation_title">
<meta content="A &amp; B" name="citation_author">
<meta content="w1234" name="citation_technical_report_number">
"""
        from nber_cli.fetch.fetcher import parse_page

        result = parse_page(page)

        assert result.title == "Women's Work & Family"
        assert result.authors == ["A & B"]

    def test_parses_historical_series_id(self):
        page = """
<meta name="citation_title" content="Historical Paper">
<meta name="citation_technical_report_number" content="h0065">
"""
        from nber_cli.fetch.fetcher import parse_page

        result = parse_page(page)

        assert result.paper_id == 65
        assert result.series == "h"

    def test_rejects_missing_required_fields(self):
        page = "<html><head></head><body></body></html>"
        from nber_cli.fetch.fetcher import parse_page

        with pytest.raises(ValueError, match="missing citation title"):
            parse_page(page)

    def test_parses_paper_id_with_leading_zeros(self):
        page = """
<meta name="citation_title" content="A Paper">
<meta name="citation_technical_report_number" content="w00123">
"""
        from nber_cli.fetch.fetcher import parse_page
        result = parse_page(page)
        assert result.paper_id == 123

    def test_parses_paper_id_without_w_prefix(self):
        page = """
<meta name="citation_title" content="A Paper">
<meta name="citation_technical_report_number" content="456">
"""
        from nber_cli.fetch.fetcher import parse_page
        result = parse_page(page)
        assert result.paper_id == 456

    @pytest.mark.parametrize("paper_id", ["", "w0", "0", "invalid", "w-1"])
    def test_rejects_invalid_paper_id(self, paper_id):
        page = f"""
<meta name="citation_title" content="A Paper">
<meta name="citation_technical_report_number" content="{paper_id}">
"""
        from nber_cli.fetch.fetcher import parse_page

        with pytest.raises(ValueError, match="citation ID"):
            parse_page(page)

    def test_allows_missing_optional_fields(self):
        page = """
<meta name="citation_title" content="A Paper">
<meta name="citation_technical_report_number" content="w123">
"""
        from nber_cli.fetch.fetcher import parse_page

        result = parse_page(page)

        assert result.authors == []
        assert result.date == ""
        assert result.abstract == ""
        assert result.published_version is None
        assert result.topic is None
        assert result.programs is None


@pytest.mark.asyncio
class TestGetNber:
    async def test_retries_invalid_page_then_parses_valid_page(self):
        invalid_page = "<html><body>temporary upstream page</body></html>"
        valid_page = """
<meta name="citation_title" content="Recovered Paper">
<meta name="citation_technical_report_number" content="w1234">
"""
        with (
            patch(
                "nber_cli.fetch.fetcher._load_page_sync",
                side_effect=[invalid_page, valid_page],
            ) as mock_load,
            patch("nber_cli.fetch.fetcher.time.sleep") as mock_sleep,
        ):
            paper = await get_nber(1234)

        assert paper.title == "Recovered Paper"
        assert mock_load.call_count == 2
        assert mock_sleep.call_count == 1

    async def test_fetches_historical_series(self):
        page = """
<meta name="citation_title" content="Historical Paper">
<meta name="citation_technical_report_number" content="h0065">
"""
        with patch("nber_cli.fetch.fetcher._load_page_sync", return_value=page):
            paper = await get_nber(65, series="h")

        assert paper.series == "h"
        assert paper.paper_id == 65

    async def test_rejects_mismatched_response_id_without_session(self):
        page = """
<meta name="citation_title" content="Another Paper">
<meta name="citation_technical_report_number" content="w5678">
"""
        with patch("nber_cli.fetch.fetcher._load_page_sync", return_value=page):
            with pytest.raises(ValueError, match="does not match"):
                await get_nber(1234)

    async def test_rejects_mismatched_response_id_with_session(self):
        page = """
<meta name="citation_title" content="Another Paper">
<meta name="citation_technical_report_number" content="w5678">
"""
        session = MagicMock()
        with patch(
            "nber_cli.fetch.fetcher._load_page",
            new_callable=AsyncMock,
            return_value=page,
        ):
            with pytest.raises(ValueError, match="does not match"):
                await get_nber(1234, session=session)


class TestExtractAbstract:
    def test_extracts_abstract(self):
        from nber_cli.fetch.fetcher import _extract_abstract
        page = '<div class="page-header__intro-inner">\n<p>This is the abstract.</p>\n</div>'
        assert _extract_abstract(page) == "This is the abstract."

    def test_strips_html_tags(self):
        from nber_cli.fetch.fetcher import _extract_abstract
        page = '<div class="page-header__intro-inner"><p>Abstract with <em>markup</em> and <a href="#">links</a>.</p></div>'
        assert _extract_abstract(page) == "Abstract with markup and links."

    def test_collapses_whitespace(self):
        from nber_cli.fetch.fetcher import _extract_abstract
        page = '<div class="page-header__intro-inner"><p>Abstract\n\nwith   spaces.</p></div>'
        assert _extract_abstract(page) == "Abstract with spaces."

    def test_returns_empty_when_missing(self):
        from nber_cli.fetch.fetcher import _extract_abstract
        assert _extract_abstract("<html></html>") == ""


class TestExtractPublishedVersion:
    def test_extracts_published_version(self):
        from nber_cli.fetch.fetcher import _extract_published_version
        page = '<h2>Published Versions</h2>\n<p>Published in Journal, 2024.</p>'
        assert _extract_published_version(page) == "Published in Journal, 2024."

    def test_strips_html_tags(self):
        from nber_cli.fetch.fetcher import _extract_published_version
        page = '<h2>Published Versions</h2><p>Published in <em>Journal</em>.</p>'
        assert _extract_published_version(page) == "Published in Journal."

    def test_returns_none_when_missing(self):
        from nber_cli.fetch.fetcher import _extract_published_version
        assert _extract_published_version("<html></html>") is None


class TestNormalizeDate:
    def test_none_returns_none(self):
        from nber_cli.fetch.fetcher import _normalize_date
        assert _normalize_date(None) is None

    def test_date_object_returns_isoformat(self):
        from nber_cli.fetch.fetcher import _normalize_date
        assert _normalize_date(date(2024, 1, 15)) == "2024-01-15"

    def test_valid_string_returns_isoformat(self):
        from nber_cli.fetch.fetcher import _normalize_date
        assert _normalize_date("2024-01-15") == "2024-01-15"

    def test_rejects_invalid_format(self):
        from nber_cli.fetch.fetcher import _normalize_date
        with pytest.raises(ValueError, match="expected YYYY-MM-DD"):
            _normalize_date("01/15/2024")

    def test_rejects_malformed_date(self):
        from nber_cli.fetch.fetcher import _normalize_date
        with pytest.raises(ValueError, match="expected YYYY-MM-DD"):
            _normalize_date("2024-13-01")

    def test_rejects_empty_string(self):
        from nber_cli.fetch.fetcher import _normalize_date
        with pytest.raises(ValueError, match="expected YYYY-MM-DD"):
            _normalize_date("")


class TestParseSearchResult:
    def test_parses_complete_result(self):
        from nber_cli.fetch.fetcher import _parse_search_result
        raw = {
            "url": "/papers/w12345",
            "title": "A Paper",
            "authors": ['<a href="/people/a">Author A</a>'],
            "displaydate": "Jan 2024",
            "abstract": "Abstract text.",
        }
        result = _parse_search_result(raw)
        assert result.paper_id == 12345
        assert result.title == "A Paper"
        assert result.authors == ["Author A"]
        assert result.date == "Jan 2024"
        assert result.abstract == "Abstract text."
        assert result.url == "https://www.nber.org/papers/w12345"

    def test_preserves_historical_series_id(self):
        from nber_cli.fetch.fetcher import _parse_search_result

        result = _parse_search_result(
            {"url": "/papers/h0065", "title": "Historical Paper"}
        )

        assert result.paper_id == 65
        assert result.series == "h"

    def test_handles_missing_url(self):
        from nber_cli.fetch.fetcher import _parse_search_result
        result = _parse_search_result({})
        assert result.paper_id == 0
        assert result.url == ""

    def test_handles_missing_fields_gracefully(self):
        from nber_cli.fetch.fetcher import _parse_search_result
        raw = {"url": "/papers/w99999"}
        result = _parse_search_result(raw)
        assert result.paper_id == 99999
        assert result.title == ""
        assert result.authors == []
        assert result.date == ""
        assert result.abstract == ""

    def test_skips_empty_authors(self):
        from nber_cli.fetch.fetcher import _parse_search_result
        raw = {"authors": ["", "Author A", ""]}
        result = _parse_search_result(raw)
        assert result.authors == ["Author A"]

    def test_handles_external_url(self):
        from nber_cli.fetch.fetcher import _parse_search_result
        raw = {"url": "https://example.com/papers/w1"}
        result = _parse_search_result(raw)
        assert result.url == "https://example.com/papers/w1"

    def test_handles_none_values(self):
        from nber_cli.fetch.fetcher import _parse_search_result
        raw = {
            "url": None,
            "title": None,
            "authors": None,
            "displaydate": None,
            "abstract": None,
        }
        result = _parse_search_result(raw)
        assert result.paper_id == 0
        assert result.title == ""
        assert result.authors == []
        assert result.date == ""
        assert result.abstract == ""

    def test_cleans_html_in_all_fields(self):
        from nber_cli.fetch.fetcher import _parse_search_result
        raw = {
            "title": "Title with <em>markup</em>",
            "authors": ['<a href="#">A &amp; B</a>'],
            "displaydate": "Jan 2024",
            "abstract": "Abstract with <br>line break.",
        }
        result = _parse_search_result(raw)
        assert result.title == "Title with markup"
        assert result.authors == ["A & B"]
        assert result.abstract == "Abstract with line break."


class TestRetryAsync:
    @pytest.mark.asyncio
    async def test_returns_on_success(self):
        from nber_cli.fetch.fetcher import _retry_async
        async def _loader():
            return "ok"
        with patch("nber_cli.fetch.fetcher.asyncio.sleep") as mock_sleep:
            result = await _retry_async(_loader)
        assert result == "ok"
        assert mock_sleep.call_count == 0

    @pytest.mark.asyncio
    async def test_retries_on_retryable_http_error(self):
        from aiohttp import ClientResponseError
        from nber_cli.fetch.fetcher import _retry_async

        calls = [0]

        async def _loader():
            calls[0] += 1
            if calls[0] < 3:
                raise ClientResponseError(
                    request_info=MagicMock(), history=(), status=500, message="Internal Error"
                )
            return "ok"

        with patch("nber_cli.fetch.fetcher.asyncio.sleep") as mock_sleep:
            result = await _retry_async(_loader)

        assert result == "ok"
        assert calls[0] == 3
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_does_not_retry_404(self):
        from aiohttp import ClientResponseError
        from nber_cli.fetch.fetcher import _retry_async

        async def _loader():
            raise ClientResponseError(
                request_info=MagicMock(), history=(), status=404, message="Not Found"
            )

        with patch("nber_cli.fetch.fetcher.asyncio.sleep") as mock_sleep:
            with pytest.raises(ClientResponseError) as exc_info:
                await _retry_async(_loader)

        assert exc_info.value.status == 404
        assert mock_sleep.call_count == 0

    @pytest.mark.asyncio
    async def test_retries_on_client_error(self):
        from aiohttp import ClientError
        from nber_cli.fetch.fetcher import _retry_async

        calls = [0]

        async def _loader():
            calls[0] += 1
            if calls[0] < 2:
                raise ClientError("connection reset")
            return "ok"

        with patch("nber_cli.fetch.fetcher.asyncio.sleep") as mock_sleep:
            result = await _retry_async(_loader)

        assert result == "ok"
        assert calls[0] == 2
        assert mock_sleep.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_invalid_nber_response(self):
        from nber_cli.fetch.fetcher import NBERResponseError, _retry_async

        calls = [0]

        async def _loader():
            calls[0] += 1
            if calls[0] < 2:
                raise NBERResponseError("invalid response")
            return "ok"

        with patch("nber_cli.fetch.fetcher.asyncio.sleep") as mock_sleep:
            result = await _retry_async(_loader)

        assert result == "ok"
        assert calls[0] == 2
        assert mock_sleep.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self):
        import asyncio
        from nber_cli.fetch.fetcher import _retry_async

        calls = [0]

        async def _loader():
            calls[0] += 1
            if calls[0] < 2:
                raise asyncio.TimeoutError("timed out")
            return "ok"

        with patch("nber_cli.fetch.fetcher.asyncio.sleep") as mock_sleep:
            result = await _retry_async(_loader)

        assert result == "ok"
        assert calls[0] == 2
        assert mock_sleep.call_count == 1

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        from aiohttp import ClientResponseError
        from nber_cli.fetch.fetcher import _retry_async

        async def _loader():
            raise ClientResponseError(
                request_info=MagicMock(), history=(), status=500, message="Error"
            )

        with patch("nber_cli.fetch.fetcher.asyncio.sleep"):
            with pytest.raises(ClientResponseError) as exc_info:
                await _retry_async(_loader)

        assert exc_info.value.status == 500


class TestRetryClassification:
    def test_http_500_is_retryable(self):
        from nber_cli.fetch.fetcher import _should_retry_http_error
        error = MagicMock()
        error.code = 500
        assert _should_retry_http_error(error) is True

    def test_http_599_is_retryable(self):
        from nber_cli.fetch.fetcher import _should_retry_http_error
        error = MagicMock()
        error.code = 599
        assert _should_retry_http_error(error) is True

    def test_http_408_is_retryable(self):
        from nber_cli.fetch.fetcher import _should_retry_http_error
        error = MagicMock()
        error.code = 408
        assert _should_retry_http_error(error) is True

    def test_http_429_is_retryable(self):
        from nber_cli.fetch.fetcher import _should_retry_http_error
        error = MagicMock()
        error.code = 429
        assert _should_retry_http_error(error) is True

    def test_http_404_is_not_retryable(self):
        from nber_cli.fetch.fetcher import _should_retry_http_error
        error = MagicMock()
        error.code = 404
        assert _should_retry_http_error(error) is False

    def test_http_400_is_not_retryable(self):
        from nber_cli.fetch.fetcher import _should_retry_http_error
        error = MagicMock()
        error.code = 400
        assert _should_retry_http_error(error) is False

    def test_http_200_is_not_retryable(self):
        from nber_cli.fetch.fetcher import _should_retry_http_error
        error = MagicMock()
        error.code = 200
        assert _should_retry_http_error(error) is False

    def test_aiohttp_500_is_retryable(self):
        from nber_cli.fetch.fetcher import _should_retry_aiohttp_error
        error = MagicMock()
        error.status = 500
        assert _should_retry_aiohttp_error(error) is True

    def test_aiohttp_408_is_retryable(self):
        from nber_cli.fetch.fetcher import _should_retry_aiohttp_error
        error = MagicMock()
        error.status = 408
        assert _should_retry_aiohttp_error(error) is True

    def test_aiohttp_429_is_retryable(self):
        from nber_cli.fetch.fetcher import _should_retry_aiohttp_error
        error = MagicMock()
        error.status = 429
        assert _should_retry_aiohttp_error(error) is True

    def test_aiohttp_404_is_not_retryable(self):
        from nber_cli.fetch.fetcher import _should_retry_aiohttp_error
        error = MagicMock()
        error.status = 404
        assert _should_retry_aiohttp_error(error) is False


class TestLoadPage:
    @pytest.mark.asyncio
    async def test_load_page_fetches_url(self):
        from nber_cli.fetch.fetcher import _load_page
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text.return_value = "page content"
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await _load_page("https://example.com", mock_session)

        assert result == "page content"
        mock_session.get.assert_called_once_with("https://example.com", headers=_NBER_REQUEST_HEADERS)

    @pytest.mark.asyncio
    async def test_load_page_raises_on_http_error(self):
        from nber_cli.fetch.fetcher import _load_page
        from aiohttp import ClientResponseError
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = ClientResponseError(
            request_info=MagicMock(), history=(), status=404, message="Not Found"
        )
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(ClientResponseError):
            await _load_page("https://example.com", mock_session)


class TestLoadJson:
    @pytest.mark.asyncio
    async def test_load_json_fetches_and_parses(self):
        from nber_cli.fetch.fetcher import _load_json
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text.return_value = '{"key": "value"}'
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await _load_json("https://example.com", mock_session, {"q": "test"})

        assert result == {"key": "value"}
        mock_session.get.assert_called_once_with(
            "https://example.com", headers=_NBER_REQUEST_HEADERS, params={"q": "test"}
        )
