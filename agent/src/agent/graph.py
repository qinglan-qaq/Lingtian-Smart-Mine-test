"""
LangGraph ReAct Agent 图定义

流程:
  START → agent (LLM 推理 + 工具调用决策)
        → tools (执行 MCP 工具) / END
        → agent → ... (ReAct 循环)
"""

import logging

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from .prompts import SYSTEM_PROMPT
from .state import AgentState
from .tools import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)


def create_agent_graph() -> StateGraph:
    """
    构建 ReAct Agent 状态图。
    实际运行时通过 config 注入 MCP 工具绑定。
    """
    workflow = StateGraph(AgentState)

    # TODO: 添加 agent 节点（LLM 推理）
    # workflow.add_node("agent", agent_node)

    # TODO: 添加 tools 节点（MCP 工具执行）
    # workflow.add_node("tools", ToolNode(tools))

    # TODO: 设置路由边
    # workflow.set_entry_point("agent")
    # workflow.add_conditional_edges("agent", should_continue, {...})
    # workflow.add_edge("tools", "agent")

    logger.info("Agent graph skeleton created (nodes to be implemented)")
    return workflow.compile()
