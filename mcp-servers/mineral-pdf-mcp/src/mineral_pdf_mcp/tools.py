"""
mineral-pdf-mcp 工具实现 — NI 43-101 储量数据提取
"""

import logging

logger = logging.getLogger(__name__)


async def extract_resources(pdf_url: str) -> dict:
    """
    从 PDF 报告中提取 NI 43-101 标准的资源储量数据
    Args:
        pdf_url: PDF 报告的 URL
    Returns:
        {
            "project_name": str,
            "mineral": str,
            "indicated": {"tonnage": float, "grade": float, "unit": str},
            "inferred": {"tonnage": float, "grade": float, "unit": str},
            "report_date": str,
            "source_url": str
        }
    """
    # TODO: 下载 PDF → 解析 → 提取 NI 43-101 储量表
    # 1. 下载 PDF
    # 2. 用 pdfplumber 提取表格
    # 3. 匹配 "Indicated" / "Inferred" 关键词
    # 4. 结构化输出
    logger.info(f"extract_resources: pdf_url={pdf_url}")
    return {
        "project_name": "",
        "mineral": "",
        "indicated": {"tonnage": 0.0, "grade": 0.0, "unit": ""},
        "inferred": {"tonnage": 0.0, "grade": 0.0, "unit": ""},
        "report_date": "",
        "source_url": pdf_url,
    }
