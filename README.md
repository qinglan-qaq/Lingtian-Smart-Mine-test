# Lingtian-Smart-Mining-test

## 主题 24h 用 MCP 协议搭一个“矿权日报 Agent”

按 MCP (Model Context Protocol) 协议，实现至少 **3 个 MCP server + 1 个 Agent client**，组合成“矿权日报”Agent：

| # | MCP server | 必须工具 | 备注 |
|---|------------|---------|------|
| 1 | `mining-news-mcp` | `search(query, days)` · `fetch_article(url)` | 新闻聚合 |
| 2 | `mineral-pdf-mcp` | `extract_resources(pdf_url)` — NI 43-101 Indicated/Inferred 储量 | PDF 解析 |
| 3 | `lme-price-mcp` | `get_price(commodity, date)` · `get_trend(commodity, days)` | 价格行情 |

## 交付清单

- **Agent 主流程**（你自己设计）：  
  输入 `"给我生成一份关于 Pilbara 锂矿的今日简报"`，  
  输出 **Markdown 简报**（新闻摘要 + 储量数据 + 价格走势 + 风险提示）+ 引用源链接。

- **3 个 MCP server**（Python 或 TypeScript，你选）

- **1 个 client 端的 Agent 编排**（LangGraph / 自写 ReAct / 你的方案）

- **`mcp-config.json`** — 可直接接到 Claude Desktop / Cursor 验证

- **`RUN.md`** — 我们能在 5 分钟内跑起来（含一条 `docker-compose`）

---

## 项目结构

```text
Lingtian-Smart-Mine-test/
│
├── .env.example              # 环境变量模板（统一管理敏感信息）
├── .gitignore
├── mcp-config.json           # MCP 配置（可接入 Claude Desktop / Cursor）
├── docker-compose.yml        # 一键启动所有服务
├── RUN.md                    # 5 分钟快速启动指南
├── README.md                 # 本文件
│
├── agent/                    # 🤖 LangGraph Agent (ReAct 编排)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── src/
│   │   ├── main.py           # 入口：解析参数，运行 Agent
│   │   ├── agent/
│   │   │   ├── graph.py      # StateGraph 定义（ReAct 循环）
│   │   │   ├── state.py      # AgentState 类型定义
│   │   │   ├── tools.py      # 工具 schema 定义
│   │   │   └── prompts.py    # System prompt 模板
│   │   ├── mcp/
│   │   │   └── client.py     # MCP Client 管理器
│   │   └── utils/
│   │       └── config.py     # 配置读取（从 .env）
│   └── tests/
│
├── mcp-servers/
│   │
│   ├── mining-news-mcp/      # 📰 新闻聚合 MCP Server
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── src/mining_news_mcp/
│   │   │   ├── server.py     # MCP Server 入口
│   │   │   ├── tools.py      # search_news / fetch_article
│   │   │   └── news_api.py   # NewsAPI 封装
│   │   └── tests/
│   │
│   ├── mineral-pdf-mcp/      # 📄 PDF 储量解析 MCP Server
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── src/mineral_pdf_mcp/
│   │   │   ├── server.py     # MCP Server 入口
│   │   │   ├── tools.py      # extract_resources
│   │   │   └── pdf_parser.py # PDF 下载 & NI 43-101 表格提取
│   │   └── tests/
│   │
│   └── lme-price-mcp/        # 💰 价格行情 MCP Server
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── pyproject.toml
│       ├── src/lme_price_mcp/
│       │   ├── server.py     # MCP Server 入口
│       │   ├── tools.py      # get_price / get_trend
│       │   └── price_api.py  # 价格 API 封装
│       └── tests/
│
└── docs/                     # 文档（可扩展）
```

## 架构概览

```text
用户输入
   │
   ▼
┌─────────────────────────┐
│   Agent (LangGraph)      │
│   ReAct Pattern          │
│                          │
│   Think → Act → Observe  │
│          │               │
│          ▼               │
│   ┌──────────┐           │
│   │ MCP Client│──────────┼──── stdio/HTTP ────┐
│   └──────────┘           │                    │
└─────────────────────────┘                    │
                                               ▼
         ┌──────────────────┬──────────────────┬──────────────────┐
         │                  │                  │                  │
         ▼                  ▼                  ▼                  ▼
   mining-news-mcp    mineral-pdf-mcp    lme-price-mcp      (可扩展)
   NewsAPI 新闻       NI 43-101 PDF     LME 矿产价格
```

## 技术栈

| 层 | 技术 |
| --- | --- |
| Agent 编排 | Python + LangGraph + ReAct |
| MCP 协议 | MCP Python SDK (stdio transport) |
| LLM | OpenAI API (兼容) |
| 新闻数据 | NewsAPI |
| PDF 解析 | pdfplumber / pypdf |
| 价格数据 | LME / 自定义 API |
| 部署 | Docker Compose |
