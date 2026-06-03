# 🚀 5 分钟快速启动

## 前置条件

- Python 3.11+
- Docker & Docker Compose（可选）
- 有效的 API Key（NewsAPI / LME / LLM）

## 方式一：Docker Compose（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入真实 API Key

# 2. 启动所有服务
docker-compose up -d

# 3. 运行 Agent
docker-compose run agent python -m agent.src.main \
  --prompt "给我生成一份关于 Pilbara 锂矿的今日简报"
```

## 方式二：本地运行

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入真实 API Key

# 2. 安装依赖
pip install -r agent/requirements.txt
pip install -r mcp-servers/mining-news-mcp/requirements.txt
pip install -r mcp-servers/mineral-pdf-mcp/requirements.txt
pip install -r mcp-servers/lme-price-mcp/requirements.txt

# 3. 分别启动 MCP Server（三个终端）
python -m mining_news_mcp.server &
python -m mineral_pdf_mcp.server &
python -m lme_price_mcp.server &

# 4. 运行 Agent
python -m agent.src.main \
  --prompt "给我生成一份关于 Pilbara 锂矿的今日简报"
```

## 项目结构

```
├── agent/                  # LangGraph Agent (ReAct)
├── mcp-servers/
│   ├── mining-news-mcp/    # 新闻聚合
│   ├── mineral-pdf-mcp/    # PDF 储量解析
│   └── lme-price-mcp/      # 价格行情
├── .env.example            # 环境变量模板
├── mcp-config.json         # MCP 配置
└── docker-compose.yml      # 容器编排
```
