"""
PDF 解析引擎 — 下载 PDF 并提取文本 / 表格数据

使用 PyMuPDF (fitz) 进行文本提取，纯内存操作，无需落盘。
适用于文本型 PDF（不含扫描件 OCR）。
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import fitz
import httpx

logger = logging.getLogger(__name__)

# ── 常量 ─────────────────────────────────────────────────
REQUEST_TIMEOUT = 30.0            # PDF 下载超时（秒）
MAX_FILE_SIZE = 50 * 1024 * 1024  # 最大 PDF 文件大小 (50MB)
SECTION_SPLIT_RE = re.compile(r"\n{2,}")  # 段落/章节分隔


# ── 数据结构 ─────────────────────────────────────────────

@dataclass
class PDFContent:
    """PDF 解析结果"""
    full_text: str                          # 按页顺序拼接的全文
    pages: list[str] = field(default_factory=list)   # 每页文本
    page_count: int = 0
    file_size: int = 0


@dataclass
class ResourceData:
    """NI 43-101 资源数据"""
    project_name: str | None = None
    mineral: str | None = None
    indicated: dict[str, Any] | None = None   # {tonnage, grade, unit}
    inferred: dict[str, Any] | None = None
    measured: dict[str, Any] | None = None
    proven: dict[str, Any] | None = None
    report_date: str | None = None
    source_url: str | None = None


# ── 解析器 ───────────────────────────────────────────────

class PDFResourceExtractor:
    """
    NI 43-101 技术报告 PDF 解析器。

    工作流:
        1. download_pdf(url)  → 下载 PDF 到内存
        2. extract_text(content)  → PyMuPDF 逐页提取纯文本
        3. parse_resources(full_text) → 正则+关键词匹配提取储量数据

    用法:
        extractor = PDFResourceExtractor()
        pdf_bytes = await extractor.download_pdf("https://.../report.pdf")
        content = extractor.extract_text(pdf_bytes)
        resources = extractor.parse_resources(content.full_text)
    """

    # NI 43-101 资源量关键词 — 按优先级排序
    RESOURCE_CATEGORIES = [
        ("measured",  ["measured", "测定"]),
        ("indicated", ["indicated", "控制"]),
        ("inferred",  ["inferred", "推断"]),
        ("proven",    ["proven", "证实", "探明"]),
        ("probable",  ["probable", "概略"]),
    ]

    # 矿产名称关键词
    MINERAL_KEYWORDS = [
        "lithium", "copper", "gold", "silver", "iron", "nickel",
        "cobalt", "uranium", "rare earth", "zinc", "lead", "tin",
        "platinum", "palladium", "diamond", "potash", "phosphate",
        "锂", "铜", "金", "银", "铁", "镍", "钴", "铀", "稀土",
    ]

    # ── 下载 ──────────────────────────────────────────

    @staticmethod
    async def download_pdf(url: str) -> bytes:
        """
        下载 PDF 文件到内存。

        Args:
            url: PDF 文件 URL

        Returns:
            PDF 文件字节内容

        Raises:
            ValueError: URL 无效
            httpx.HTTPError: 下载失败
        """
        if not url or not url.startswith(("http://", "https://")):
            raise ValueError(f"无效的 PDF URL: {url!r}")

        logger.info("下载 PDF: %s", url)

        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

            content = resp.content
            size_mb = len(content) / (1024 * 1024)

            if len(content) > MAX_FILE_SIZE:
                raise ValueError(
                    f"PDF 文件过大: {size_mb:.1f}MB (上限 {MAX_FILE_SIZE // 1024 // 1024}MB)"
                )

            logger.info("PDF 下载完成: %.1fMB", size_mb)
            return content

    # ── 文本提取 ───────────────────────────────────────

    def extract_text(self, pdf_bytes: bytes) -> PDFContent:
        """
        使用 PyMuPDF 从 PDF 字节流中提取纯文本。

        在内存中打开，逐页调用 page.get_text()，保留原始换行结构。
        不涉及 OCR，仅适用于文字型 PDF。

        Args:
            pdf_bytes: PDF 文件的字节内容

        Returns:
            PDFContent(full_text, pages, page_count, file_size)

        Raises:
            ValueError: pdf_bytes 为空或无法解析
        """
        if not pdf_bytes:
            raise ValueError("pdf_bytes 为空")

        logger.info("开始解析 PDF (size=%d bytes)", len(pdf_bytes))

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            raise ValueError(f"PyMuPDF 无法打开 PDF: {exc}") from exc

        pages_text: list[str] = []
        page_count = doc.page_count

        for i in range(page_count):
            page = doc[i]
            text = page.get_text(sort=True)  # sort=True 按阅读顺序排列
            pages_text.append(text)

        doc.close()

        # 用双换行连接各页，保留段落结构
        full_text = "\n\n".join(pages_text)

        logger.info(
            "PDF 解析完成: pages=%d, chars=%d",
            page_count, len(full_text),
        )

        return PDFContent(
            full_text=full_text,
            pages=pages_text,
            page_count=page_count,
            file_size=len(pdf_bytes),
        )

    # ── 资源提取 ───────────────────────────────────────

    def parse_resources(self, content: PDFContent) -> ResourceData:
        """
        从 PDF 全文提取 NI 43-101 资源储量数据。

        使用关键词匹配 + 正则模式识别储量表格中的数据行。

        Args:
            content: extract_text() 返回的 PDFContent

        Returns:
            ResourceData 含从文本中提取的资源信息
        """
        text = content.full_text.lower()
        result = ResourceData(
            source_url=None,
        )

        # 1. 查找矿产类型
        for mineral in self.MINERAL_KEYWORDS:
            if mineral in text:
                result.mineral = mineral
                break

        # 2. 查找项目名称（通常出现在首页顶部附近）
        first_page = content.pages[0] if content.pages else ""
        # 取首页前 500 字符作为候选标题区域
        title_area = first_page[:500]
        result.project_name = title_area.split("\n")[0].strip() if title_area else None

        # 3. 按类别匹配资源量数据
        for category, keywords in self.RESOURCE_CATEGORIES:
            data = self._find_resource_line(text, keywords)
            if data:
                setattr(result, category, data)

        # 4. 查找报告日期
        date_match = re.search(
            r"(?:report date|effective date|date)[:\s]*([A-Z][a-z]+ \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2})",
            content.full_text, re.IGNORECASE,
        )
        if date_match:
            result.report_date = date_match.group(1)

        logger.info(
            "资源提取: mineral=%s, indicated=%s, inferred=%s",
            result.mineral,
            "found" if result.indicated else "not found",
            "found" if result.inferred else "not found",
        )

        return result

    @staticmethod
    def _find_resource_line(text: str, keywords: list[str]) -> dict[str, Any] | None:
        """
        在文本中查找指定类别的资源量数据行。

        匹配模式: 类别关键词 + 吨位数字 + 品位数字 + 单位

        Returns:
            {tonnage, grade, unit} 或 None
        """
        for kw in keywords:
            # 构建正则: 关键词附近找数字（吨位）+ 数字（品位）
            pattern = re.compile(
                rf"{kw}[^\n]*?(\d[\d,.]*)\s*(?:Mt|kt|t|万吨|百万吨)[^\n]*?(\d+\.?\d*)\s*%?",
                re.IGNORECASE,
            )
            match = pattern.search(text)
            if match:
                tonnage_str = match.group(1).replace(",", "")
                grade_str = match.group(2)
                return {
                    "tonnage": float(tonnage_str),
                    "grade": float(grade_str),
                    "unit": "Mt" if "Mt" in match.group(0) or "百万吨" in match.group(0) else "t",
                }
        return None
