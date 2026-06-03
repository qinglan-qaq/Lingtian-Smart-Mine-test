"""
LangGraph ReAct Agent — Plan → Execute → Evaluate 三阶段循环

  START
    │
    ▼
┌──────────┐    plan     ┌──────────┐  results   ┌──────────┐
│  THINK   │ ──────────► │ EXECUTE  │ ─────────► │ EVALUATE │
│ (Plan)   │             │ (MCP)    │            │ (Judge)  │
└──────────┘             └──────────┘            └──────────┘
      ▲                                               │
      │           insufficient + missing_info         │
      └───────────────────────────────────────────────┘
                                                      │  sufficient
                                                      ▼
                                                    END
"""

import json
import logging
import re
from typing import Literal

from langgraph.graph import END, StateGraph

from .prompts import (
    EVALUATE_SYSTEM_PROMPT,
    EVALUATE_USER_PROMPT,
    PLAN_SYSTEM_PROMPT,
    PLAN_USER_PROMPT,
)
from .state import AgentState
from .tools import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

# ── 配置常量 ───────────────────────────────────────────────
MAX_ITERATIONS = 5  # 最大 ReAct 循环轮次


# ── Graph 构建 ─────────────────────────────────────────────

def create_agent_graph():
    """
    构建 Plan → Execute → Evaluate 三阶段 Agent。

    返回 CompiledStateGraph，有 ainvoke / astream / astream_events 方法。
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("think", think_node)
    workflow.add_node("execute", executor_node)
    workflow.add_node("evaluate", evaluate_node)

    workflow.set_entry_point("think")

    # think → execute (无需条件，总是执行计划)
    workflow.add_edge("think", "execute")

    # execute → evaluate (执行完后评估)
    workflow.add_edge("execute", "evaluate")

    # evaluate → think (信息不足) 或 END (充足/达到上限)
    workflow.add_conditional_edges(
        "evaluate",
        _route_after_evaluate,
        {
            "think": "think",
            "end": END,
        },
    )

    logger.info("Agent graph built: think → execute → evaluate → [think|end]")
    return workflow.compile()


# ── 路由 ───────────────────────────────────────────────────

def _route_after_evaluate(state: AgentState) -> Literal["think", "end"]:
    """评估节点后的路由决策"""
    is_sufficient = state.get("is_sufficient", False)
    iteration = state.get("iteration_count", 0)

    if is_sufficient:
        logger.info(f"✓ 信息充足，结束 (iter={iteration})")
        return "end"

    if iteration >= MAX_ITERATIONS:
        logger.warning(f"⚠ 达到最大迭代次数 {MAX_ITERATIONS}，强制结束")
        return "end"

    logger.info(f"↻ 信息不足，进入下一轮 (iter={iteration})")
    return "think"


# ── Think 节点（Plan 阶段）─────────────────────────────────

async def think_node(state: AgentState, config: dict) -> dict:
    """
    推理节点 — 分析当前状态，制定行动计划。

    支持 SSE 流式输出：LLM 推理过程通过 LangGraph 的
    astream_events() 暴露 on_chat_model_stream 事件。

    Returns:
        {"plan": ActionPlan, "iteration_count": int}
    """
    llm = _build_llm(config)
    iteration = state.get("iteration_count", 0)

    # 拼接 prompt
    system_prompt = PLAN_SYSTEM_PROMPT.format(
        tool_descriptions=_format_tool_descriptions(),
    )

    user_request = ""
    if state.get("messages"):
        first_msg = state["messages"][0]
        user_request = first_msg.get("content", "") if isinstance(first_msg, dict) else str(first_msg)

    collected_info = _format_collected_results(state.get("execution_results", []))

    user_prompt = PLAN_USER_PROMPT.format(
        user_request=user_request,
        iteration_count=iteration,
        collected_info=collected_info or "（暂无）",
        missing_info=state.get("missing_info") or "（首轮，全面收集）",
    )

    # LLM 推理（流式 — 上游 astream_events 可捕获）
    response = await llm.ainvoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])

    # 解析 JSON 计划
    plan = _parse_json_response(response.content, default={
        "reasoning": response.content,
        "tool_calls": [],
    })

    logger.info(
        "[Think] iter=%d, tool_calls=%d, reasoning=%.120s...",
        iteration,
        len(plan.get("tool_calls", [])),
        plan.get("reasoning", ""),
    )

    return {
        "plan": plan,
        "iteration_count": iteration + 1,
    }


# ── Execute 节点（MCP 工具调用）────────────────────────────

async def executor_node(state: AgentState, config: dict) -> dict:
    """
    执行节点 — 根据 Think 节点的计划，调用 MCP 工具。

    从 config 中获取 MCPClientManager，逐个执行 tool_calls。
    工具可并行调用以提升效率。
    """
    import asyncio

    plan = state.get("plan") or {}
    tool_calls = plan.get("tool_calls", [])
    mcp_manager = _get_mcp_manager(config)

    if not tool_calls:
        logger.info("[Execute] 无工具调用，跳过")
        return {"execution_results": state.get("execution_results", [])}

    async def _call_one(tc: dict) -> dict:
        name = tc.get("tool_name", "")
        args = tc.get("arguments", {})
        try:
            result = await mcp_manager.call_tool(name, args)
            return {"tool_name": name, "arguments": args, "result": result, "error": None}
        except Exception as exc:
            logger.error(f"[Execute] {name} 调用失败: {exc}")
            return {"tool_name": name, "arguments": args, "result": None, "error": str(exc)}

    # 并行执行所有工具调用
    new_results = await asyncio.gather(*[_call_one(tc) for tc in tool_calls])

    accumulated = list(state.get("execution_results", [])) + list(new_results)

    logger.info(
        "[Execute] 完成 %d 个工具调用 (累计 %d)",
        len(new_results), len(accumulated),
    )

    return {"execution_results": accumulated}


# ── Evaluate 节点（评估阶段）───────────────────────────────

async def evaluate_node(state: AgentState, config: dict) -> dict:
    """
    评估节点 — 审核已收集信息是否足以生成简报。

    - 充足 → 直接输出 final_report
    - 不足 → 返回 missing_info，触发下一轮 Think
    """
    llm = _build_llm(config)
    iteration = state.get("iteration_count", 0)

    user_request = ""
    if state.get("messages"):
        first_msg = state["messages"][0]
        user_request = first_msg.get("content", "") if isinstance(first_msg, dict) else str(first_msg)

    collected_results = _format_collected_results(state.get("execution_results", []))

    user_prompt = EVALUATE_USER_PROMPT.format(
        user_request=user_request,
        collected_results=collected_results or "（无）",
        iteration_count=iteration,
    )

    response = await llm.ainvoke([
        {"role": "system", "content": EVALUATE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])

    verdict = _parse_json_response(response.content, default={
        "sufficient": False,
        "reasoning": response.content,
        "missing": "解析失败",
        "final_report": None,
    })

    # 强制兜底：迭代达到上限时无论如何生成报告
    if iteration >= MAX_ITERATIONS and not verdict.get("sufficient"):
        logger.warning("[Evaluate] 强制生成报告（已达最大迭代）")
        verdict["sufficient"] = True
        if not verdict.get("final_report"):
            verdict["final_report"] = _force_generate_report(state, verdict)

    logger.info(
        "[Evaluate] iter=%d, sufficient=%s",
        iteration, verdict.get("sufficient"),
    )

    return {
        "is_sufficient": verdict.get("sufficient", False),
        "missing_info": verdict.get("missing"),
        "final_report": verdict.get("final_report"),
    }


# ── 辅助函数 ───────────────────────────────────────────────

def _build_llm(config: dict):
    """
    从运行时 config 构建 LLM 实例。

    config 结构（由 main.py 注入）:
        {"configurable": {"llm_api_key": ..., "llm_model": ..., "llm_base_url": ...}}
    """
    from langchain_openai import ChatOpenAI

    cfg = config.get("configurable", {})

    return ChatOpenAI(
        api_key=cfg.get("llm_api_key", ""),
        model=cfg.get("llm_model", "gpt-4o"),
        base_url=cfg.get("llm_base_url", "https://api.openai.com/v1"),
        temperature=0.2,
        streaming=True,  # 启用流式输出 — astream_events 可捕获
    )


def _get_mcp_manager(config: dict):
    """
    从 runtime config 获取 MCPClientManager。
    由 main.py 在调用前注入 configurable.mcp_manager。
    """
    manager = config.get("configurable", {}).get("mcp_manager")
    if manager is None:
        # 兜底：返回一个空壳 manager
        from ..mcp.client import MCPClientManager
        logger.warning("[Execute] MCP manager 未注入，使用空壳")
        return MCPClientManager(servers=[])
    return manager


def _format_tool_descriptions() -> str:
    """将 TOOL_DEFINITIONS 格式化为 prompt 可用的文本"""
    lines = []
    for t in TOOL_DEFINITIONS:
        params = t.get("parameters", {})
        props = params.get("properties", {})
        required = params.get("required", [])
        param_str = ", ".join(
            f"{k}: {v.get('type','str')}{' (required)' if k in required else ''}"
            for k, v in props.items()
        )
        lines.append(f"- **{t['name']}**: {t['description']}\n  参数: {param_str}")
    return "\n".join(lines)


def _format_collected_results(results: list[dict]) -> str:
    """将执行结果格式化为可读文本"""
    if not results:
        return ""
    lines = []
    for i, r in enumerate(results, 1):
        name = r.get("tool_name", "unknown")
        err = r.get("error")
        if err:
            lines.append(f"{i}. [{name}] ❌ 错误: {err}")
        else:
            result_str = json.dumps(r.get("result"), ensure_ascii=False, indent=2)
            # 截断过长结果
            if len(result_str) > 2000:
                result_str = result_str[:2000] + "...(truncated)"
            lines.append(f"{i}. [{name}] ✅\n{result_str}")
    return "\n\n".join(lines)


def _parse_json_response(content: str, default: dict) -> dict:
    """
    从 LLM 响应中提取 JSON。
    支持 ```json ... ``` 代码块和纯 JSON。
    """
    # 尝试提取 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # 尝试找到第一个 { 和最后一个 }
        brace_start = content.find("{")
        brace_end = content.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            json_str = content[brace_start:brace_end + 1]
        else:
            logger.warning("无法从响应中提取 JSON，使用默认值")
            return default

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON 解析失败: {e}")
        return default


def _force_generate_report(state: AgentState, verdict: dict) -> str:
    """兜底：用现有数据拼一个简陋的简报"""
    results = state.get("execution_results", [])
    collected = _format_collected_results(results)

    user_request = ""
    if state.get("messages"):
        first_msg = state["messages"][0]
        user_request = first_msg.get("content", "") if isinstance(first_msg, dict) else str(first_msg)

    return f"""# 矿权日报（自动生成）

**说明**: 达到最大迭代次数，以下基于已收集信息自动生成。

## 用户需求
{user_request}

## 已收集数据
{collected or "（无数据）"}

## ⚠️ 风险提示
- 数据不完整，建议人工复核
- 部分数据源可能未响应
"""
