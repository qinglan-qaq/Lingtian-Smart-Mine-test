"""
Agent 状态定义 — Plan → Execute → Evaluate 三阶段循环
"""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class ToolCallPlan(TypedDict, total=False):
    """单次工具调用计划"""
    tool_name: str
    arguments: dict[str, Any]
    reason: str  # 为什么要调这个工具


class ActionPlan(TypedDict, total=False):
    """Think 节点输出的完整行动计划"""
    reasoning: str          # LLM 推理链
    tool_calls: list[ToolCallPlan]  # 本轮要执行的工具调用
    direct_response: str    # 如果不需要工具，直接回复（用于首轮简单对话）


class ExecutionResult(TypedDict, total=False):
    """单次工具执行结果"""
    tool_name: str
    arguments: dict[str, Any]
    result: Any
    error: str | None


class AgentState(TypedDict):
    """ReAct Agent 状态

    贯穿 Plan → Execute → Evaluate 三个节点的上下文。
    """
    # ---- 消息历史（兼容 LangChain 消息格式） ----
    messages: Annotated[list, add_messages]

    # ---- Plan 阶段 ----
    plan: ActionPlan | None           # Think 节点输出的行动计划

    # ---- Execute 阶段 ----
    execution_results: list[ExecutionResult]  # 累计的工具执行结果

    # ---- Evaluate 阶段 ----
    iteration_count: int              # 当前迭代轮次
    is_sufficient: bool | None        # 信息是否充足
    missing_info: str | None          # 还缺什么信息（下一轮 Think 的输入）

    # ---- 最终输出 ----
    final_report: str | None          # Markdown 简报
