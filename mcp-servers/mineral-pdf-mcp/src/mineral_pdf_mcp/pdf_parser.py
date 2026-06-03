"""
PDF 解析引擎 — 下载 PDF 并提取 NI 43-101 表格数据
"""

import logging
from io import BytesIO

import httpx

logger = logging.getLogger(__name__)


class PDFResourceExtractor:
    """NI 43-101 报告 PDF 资源提取器"""

    # 需要匹配的关键词
    RESOURCE_KEYWORDS = [
        "indicated",
        "inferred",
        "measured",
        "proven",
        "probable",
        "ni 43-101",
        "mineral resource",
        "ore reserve",
    ]

    async def download_pdf(self, url: str) -> bytes:
        """下载 PDF 文件"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    async def extract_tables(self, pdf_bytes: bytes) -> list[dict]:
        """从 PDF 中提取表格数据"""
        # TODO: 使用 pdfplumber 提取表格
        # import pdfplumber
        # with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        #     for page in pdf.pages:
        #         tables = page.extract_tables()
        ...
        return []

    async def parse_resource_table(self, tables: list[dict]) -> dict:
        """解析资源量表格，提取 Indicated/Inferred 数据"""
        # TODO: 匹配关键词，结构化提取
        ...
        return {}
