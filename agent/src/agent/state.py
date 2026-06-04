"""
Agent 状态定义 — Plan → Execute → Evaluate → Generate 四阶段循环
"""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class ToolCallPlan(TypedDict, total=False):
    tool_name: str
    arguments: dict[str, Any]
    reason: str


class ActionPlan(TypedDict, total=False):
    reasoning: str
    tool_calls: list[ToolCallPlan]
    direct_response: str


class ExecutionResult(TypedDict, total=False):
    tool_name: str
    arguments: dict[str, Any]
    result: Any
    error: str | None


class AgentState(TypedDict):
    """ReAct Agent 状态 — 贯穿四个节点"""
    messages: Annotated[list, add_messages]
    plan: ActionPlan | None
    execution_results: list[ExecutionResult]
    iteration_count: int
    is_sufficient: bool | None
    missing_info: str | None
    final_report: str | None
