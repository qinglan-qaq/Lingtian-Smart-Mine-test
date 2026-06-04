"""
mineral-pdf-mcp 业务逻辑层

纯函数，不依赖 FastMCP。被 server.py 的 @mcp.tool() 装饰器调用。
"""

import logging
from typing import Any

from .pdf_parser import PDFResourceExtractor

logger = logging.getLogger(__name__)

# 复用单例解析器
_extractor = PDFResourceExtractor()


async def extract_resources(pdf_url: str) -> dict[str, Any]:
    """
    从 PDF 报告中提取 NI 43-101 标准的矿产资源与储量数据。

    工作流:
      1. 下载 PDF 到内存
      2. PyMuPDF 逐页提取纯文本
      3. 关键词 + 正则匹配 Indicated/Inferred/Measured/Proven 资源量

    Args:
        pdf_url: NI 43-101 技术报告的 PDF URL

    Returns:
        {
            "project_name": str | None,
            "mineral": str | None,
            "full_text": str,              # 全文（供 Agent 后续分析）
            "full_text_length": int,
            "page_count": int,
            "indicated": {tonnage, grade, unit} | None,
            "inferred":  {tonnage, grade, unit} | None,
            "measured":  {tonnage, grade, unit} | None,
            "proven":    {tonnage, grade, unit} | None,
            "report_date": str | None,
            "source_url": str,
            "error": str | None,
        }
    """
    logger.info("extract_resources: url='%s'", pdf_url)

    result: dict[str, Any] = {
        "project_name": None,
        "mineral": None,
        "full_text": "",
        "full_text_length": 0,
        "page_count": 0,
        "indicated": None,
        "inferred": None,
        "measured": None,
        "proven": None,
        "report_date": None,
        "source_url": pdf_url,
        "error": None,
    }

    # 1. 下载 PDF
    try:
        pdf_bytes = await _extractor.download_pdf(pdf_url)
    except ValueError as exc:
        logger.warning("extract_resources URL 无效: %s", exc)
        result["error"] = f"Invalid URL: {exc}"
        return result
    except Exception as exc:
        logger.error("extract_resources 下载失败: %s", exc)
        result["error"] = f"Download failed: {exc}"
        return result

    # 2. 提取文本
    try:
        content = _extractor.extract_text(pdf_bytes)
    except ValueError as exc:
        logger.warning("extract_resources PDF 解析失败: %s", exc)
        result["error"] = f"PDF parse failed: {exc}"
        return result

    # 3. 提取资源数据
    try:
        resources = _extractor.parse_resources(content)
    except Exception as exc:
        logger.exception("extract_resources 资源提取异常: %s", exc)
        result["error"] = f"Resource extraction error: {exc}"
        return result

    # 4. 组装结果
    result.update({
        "project_name": resources.project_name,
        "mineral": resources.mineral,
        "full_text": content.full_text,
        "full_text_length": len(content.full_text),
        "page_count": content.page_count,
        "indicated": resources.indicated,
        "inferred": resources.inferred,
        "measured": resources.measured,
        "proven": resources.proven,
        "report_date": resources.report_date,
    })

    logger.info(
        "extract_resources 完成: pages=%d, chars=%d, mineral=%s, indicated=%s",
        content.page_count,
        len(content.full_text),
        resources.mineral,
        "found" if resources.indicated else "not found",
    )

    return result
