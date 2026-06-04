"""
测试 pdf_parser.py — PDFResourceExtractor
"""

import io

import pytest

from mineral_pdf_mcp.pdf_parser import (
    PDFContent,
    PDFResourceExtractor,
    ResourceData,
)


class TestDownloadPDF:
    """download_pdf"""

    @pytest.mark.asyncio
    async def test_rejects_invalid_url(self):
        with pytest.raises(ValueError, match="无效的 PDF URL"):
            await PDFResourceExtractor.download_pdf("not-a-url")

        with pytest.raises(ValueError, match="无效的 PDF URL"):
            await PDFResourceExtractor.download_pdf("")


class TestExtractText:
    """extract_text"""

    def test_extracts_text_from_pdf(self, sample_pdf_bytes):
        extractor = PDFResourceExtractor()
        content = extractor.extract_text(sample_pdf_bytes)

        assert isinstance(content, PDFContent)
        assert content.page_count >= 1
        assert len(content.full_text) > 0
        assert len(content.pages) == content.page_count
        assert content.file_size > 0

    def test_contains_report_content(self, sample_pdf_bytes):
        extractor = PDFResourceExtractor()
        content = extractor.extract_text(sample_pdf_bytes)

        assert "NI 43-101" in content.full_text
        assert "Pilbara" in content.full_text
        assert "Indicated" in content.full_text or "indicated" in content.full_text.lower()

    def test_rejects_empty_bytes(self):
        extractor = PDFResourceExtractor()
        with pytest.raises(ValueError, match="为空"):
            extractor.extract_text(b"")

    def test_rejects_invalid_pdf(self):
        extractor = PDFResourceExtractor()
        with pytest.raises(ValueError, match="无法打开 PDF"):
            extractor.extract_text(b"not a pdf file")


class TestParseResources:
    """parse_resources"""

    def test_parses_resource_data(self, sample_pdf_bytes):
        extractor = PDFResourceExtractor()
        content = extractor.extract_text(sample_pdf_bytes)
        resources = extractor.parse_resources(content)

        assert isinstance(resources, ResourceData)
        assert resources.mineral == "lithium" or resources.mineral is not None
        # indicated 应被找到
        assert resources.indicated is not None
        assert resources.indicated["tonnage"] >= 0
        assert resources.indicated["grade"] > 0

    def test_parses_indicated_and_inferred(self, sample_pdf_bytes):
        extractor = PDFResourceExtractor()
        content = extractor.extract_text(sample_pdf_bytes)
        resources = extractor.parse_resources(content)

        if resources.indicated:
            assert "tonnage" in resources.indicated
            assert "grade" in resources.indicated
        if resources.inferred:
            assert "tonnage" in resources.inferred
            assert "grade" in resources.inferred

    def test_empty_text_returns_none_resources(self):
        extractor = PDFResourceExtractor()
        content = PDFContent(
            full_text="Some text without any resource data.",
            pages=["Some text without any resource data."],
            page_count=1,
            file_size=50,
        )
        resources = extractor.parse_resources(content)
        assert resources.indicated is None
        assert resources.inferred is None

    def test_extracts_project_name(self, sample_pdf_bytes):
        extractor = PDFResourceExtractor()
        content = extractor.extract_text(sample_pdf_bytes)
        resources = extractor.parse_resources(content)
        assert resources.project_name is not None
