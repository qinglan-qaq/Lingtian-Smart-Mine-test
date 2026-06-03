"""
Agent 状态定义
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """ReAct Agent 的状态图节点"""
    messages: Annotated[list, add_messages]
    # 附加上下文
    news_summary: str | None       # 新闻摘要
    resource_data: str | None      # 储量数据
    price_data: str | None         # 价格行情
    final_report: str | None       # 最终简报
