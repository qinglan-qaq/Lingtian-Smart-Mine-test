# 🚀 快速启动

## 前置条件

- Python 3.11+
- Docker & Docker Compose
- NewsAPI Key（[newsapi.org/register](https://newsapi.org/register)）
- LLM API Key（OpenAI / DeepSeek 兼容）

## 方式一：Docker Compose

```bash
# 1. 配置
cp .env.example .env
# 编辑 .env → 填入 NEWS_API_KEY + LLM_API_KEY

# 2. 一键启动
docker-compose up -d

# 3. 运行 Agent
docker-compose run agent python -m src.main \
  -p "给我生成一份关于 Pilbara 锂矿的今日简报"
```

## 方式二：本地运行

```bash
cp .env.example .env  # 编辑填入 Key

# 安装
pip install -r agent/requirements.txt
pip install -r mcp-servers/mining-news-mcp/requirements.txt
pip install -r mcp-servers/mineral-pdf-mcp/requirements.txt
pip install -r mcp-servers/lme-price-mcp/requirements.txt

# 启动 MCP Server（三个终端，或后台运行）
cd mcp-servers/mining-news-mcp && PYTHONPATH=src python -m mining_news_mcp &
cd mcp-servers/mineral-pdf-mcp && PYTHONPATH=src python -m mineral_pdf_mcp &
cd mcp-servers/lme-price-mcp   && PYTHONPATH=src python -m lme_price_mcp &

# 运行 Agent
cd agent && PYTHONPATH=src python -m src.main -p "..."

# 流式模式
cd agent && PYTHONPATH=src python -m src.main -p "..." --stream
```

## 验证 MCP Server

```bash
# 用 mcp 命令行工具验证（需安装 mcp CLI）
cd mcp-servers/mining-news-mcp
PYTHONPATH=src python -m mining_news_mcp --help
```
