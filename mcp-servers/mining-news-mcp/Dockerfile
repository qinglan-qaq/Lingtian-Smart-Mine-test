FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY src/ ./src/

# 确保模块可被发现
ENV PYTHONPATH=/app/src

EXPOSE 8001
ENTRYPOINT ["python", "-m", "mining_news_mcp"]
