"""
mineral-pdf-mcp — FastMCP Server 入口

基于 MCP 协议，通过 stdio transport 暴露工具:
    - extract_resources: 从 PDF 提取 NI 43-101 资源储量数据

使用 PyMuPDF (fitz) 进行文本提取，纯内存操作。

启动方式:
    python -m mineral_pdf_mcp
    python -m mineral_pdf_mcp.server
"""

import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .tools import extract_resources as _extract_resources_impl

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mineral-pdf-mcp")

mcp = FastMCP("mineral-pdf-mcp")


@mcp.tool()
async def extract_resources(pdf_url: str) -> dict[str, Any]:
    """
    从 NI 43-101 技术报告中提取矿产资源与储量数据。

    工作流:
        1. 下载 PDF 文件到内存
        2. 使用 PyMuPDF 逐页提取纯文本
        3. 关键词+正则匹配 Indicated/Inferred/Measured/Proven 储量

    返回完整的文本内容 + 结构化的储量数据。

    Args:
        pdf_url: NI 43-101 技术报告的 PDF 文件 URL

    Returns:
        包含 full_text（全文）、page_count（页数）、
        indicated/inferred/measured/proven（储量数据）等字段的字典
    """
    logger.info("[tool:extract_resources] url='%s'", pdf_url)

    # 基本 URL 校验
    if not pdf_url or not pdf_url.strip():
        return {"error": "pdf_url 不能为空"}
    if not pdf_url.startswith(("http://", "https://")):
        return {"error": f"无效的 URL 格式: {pdf_url!r}"}

    return await _extract_resources_impl(pdf_url.strip())


def main():
    """stdio transport 入口"""
    logger.info("mineral-pdf-mcp 启动中... (PyMuPDF=%s)", "available")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
