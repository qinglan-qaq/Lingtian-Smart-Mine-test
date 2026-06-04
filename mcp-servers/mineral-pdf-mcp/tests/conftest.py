"""
测试 fixtures
"""

import io

import pytest


@pytest.fixture
def sample_pdf_bytes():
    """
    生成一个最小的、包含文本的有效 PDF。
    """
    buf = io.BytesIO()
    try:
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(
            (72, 72),  # 1 inch margins
            "NI 43-101 Technical Report\n"
            "Project: Pilbara Lithium Mine\n"
            "Effective Date: January 15, 2025\n\n"
            "Indicated Resource: 10.5 Mt @ 1.2% Li2O\n"
            "Inferred Resource: 5.2 Mt @ 0.9% Li2O\n"
            "Measured Resource: 3.1 Mt @ 1.5% Li2O\n\n"
            "This report complies with NI 43-101 standards.\n",
            fontsize=11,
        )
        doc.save(buf)
        doc.close()
    except Exception:
        # PyMuPDF not available — return minimal PDF bytes
        return b"%PDF-1.4 minimal pdf"
    return buf.getvalue()


@pytest.fixture
def sample_pdf_url():
    return "https://example.com/ni43-101-report.pdf"
