"""
测试 tools.py — extract_resources
"""

from unittest.mock import AsyncMock, patch

import pytest

from mineral_pdf_mcp.tools import extract_resources


class TestExtractResources:
    """extract_resources 端到端测试"""

    @pytest.mark.asyncio
    async def test_returns_error_on_invalid_url(self):
        result = await extract_resources("not-a-url")
        assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_returns_error_on_download_failure(self):
        with patch(
            "mineral_pdf_mcp.pdf_parser.httpx.AsyncClient",
            autospec=True,
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=OSError("Connection refused"))
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            result = await extract_resources("https://example.com/report.pdf")
            assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_returns_full_text_and_metadata(self, sample_pdf_bytes):
        """端到端: 下载 → 解析 → 资源提取"""
        with patch(
            "mineral_pdf_mcp.pdf_parser.httpx.AsyncClient",
            autospec=True,
        ) as mock_client_cls:
            mock_response = AsyncMock()
            mock_response.content = sample_pdf_bytes
            mock_response.raise_for_status = lambda: None

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            result = await extract_resources("https://example.com/report.pdf")

            assert result.get("error") is None
            assert len(result.get("full_text", "")) > 0
            assert result.get("page_count", 0) > 0
            assert result.get("source_url") == "https://example.com/report.pdf"
