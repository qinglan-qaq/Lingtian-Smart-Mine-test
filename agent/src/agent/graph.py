"""
LangGraph ReAct Agent — Plan → Execute → Evaluate → Generate 四阶段

  START
    │
    ▼
┌──────────┐    plan     ┌──────────┐  results   ┌──────────┐
│  THINK   │ ──────────► │ EXECUTE  │ ─────────► │ EVALUATE │
│ (Plan)   │             │ (MCP)    │            │ (Judge)  │
└──────────┘             └──────────┘            └──────────┘
     ▲                                               │
     │          insufficient + missing_info          │
     └───────────────────────────────────────────────┘
                                                     │ sufficient
                                                     ▼
                                               ┌──────────┐
                                               │ GENERATE │
                                               │ (Report) │
                                               └──────────┘
                                                     │
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
    GENERATE_SYSTEM_PROMPT,
    GENERATE_USER_PROMPT,
    PLAN_SYSTEM_PROMPT,
    PLAN_USER_PROMPT,
)
from .state import AgentState
from .tools import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5


# ── Graph 构建 ───────────────────────────────────────────

def create_agent_graph():
    """构建 Plan → Execute → Evaluate → Generate Agent"""
    workflow = StateGraph(AgentState)

    workflow.add_node("think", think_node)
    workflow.add_node("execute", executor_node)
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("generate", generate_node)

    workflow.set_entry_point("think")
    workflow.add_edge("think", "execute")
    workflow.add_edge("execute", "evaluate")

    workflow.add_conditional_edges(
        "evaluate",
        _route_after_evaluate,
        {"think": "think", "generate": "generate"},
    )

    workflow.add_edge("generate", END)

    logger.info("Graph: think → execute → evaluate → [think|generate] → END")
    return workflow.compile()


# ── 路由 ─────────────────────────────────────────────────

def _route_after_evaluate(state: AgentState) -> Literal["think", "generate"]:
    is_sufficient = state.get("is_sufficient", False)
    iteration = state.get("iteration_count", 0)

    if is_sufficient:
        logger.info("✓ 信息充足，进入生成阶段 (iter=%d)", iteration)
        return "generate"

    if iteration >= MAX_ITERATIONS:
        logger.warning("⚠ 达到最大迭代 %d，强制生成", MAX_ITERATIONS)
        return "generate"

    logger.info("↻ 信息不足，下一轮 (iter=%d)", iteration)
    return "think"


# ── Think 节点 ───────────────────────────────────────────

async def think_node(state: AgentState, config: dict) -> dict:
    """计划节点 — LLM 推理，制定行动计划"""
    llm = _build_llm(config)
    iteration = state.get("iteration_count", 0)

    system_prompt = PLAN_SYSTEM_PROMPT.format(
        tool_descriptions=_format_tool_descriptions(),
    )
    user_request = _extract_user_request(state)
    collected_info = _format_collected_results(state.get("execution_results", []))

    user_prompt = PLAN_USER_PROMPT.format(
        user_request=user_request,
        iteration_count=iteration,
        collected_info=collected_info or "（暂无）",
        missing_info=state.get("missing_info") or "（首轮，全面收集）",
    )

    response = await llm.ainvoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])

    plan = _parse_json(_response_text(response), default={
        "reasoning": _response_text(response),
        "tool_calls": [],
    })

    logger.info("[Think] iter=%d, tools=%d", iteration, len(plan.get("tool_calls", [])))
    return {"plan": plan, "iteration_count": iteration + 1}


# ── Execute 节点 ─────────────────────────────────────────

async def executor_node(state: AgentState, config: dict) -> dict:
    """执行节点 — 并行调用 MCP 工具"""
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
            logger.error("[Execute] %s 失败: %s", name, exc)
            return {"tool_name": name, "arguments": args, "result": None, "error": str(exc)}

    new_results = await asyncio.gather(*[_call_one(tc) for tc in tool_calls])
    accumulated = list(state.get("execution_results", [])) + list(new_results)

    logger.info("[Execute] +%d 结果 (累计 %d)", len(new_results), len(accumulated))
    return {"execution_results": accumulated}


# ── Evaluate 节点 ────────────────────────────────────────

async def evaluate_node(state: AgentState, config: dict) -> dict:
    """
    评估节点 — 仅判断信息充足性，不生成报告。

    Returns: {"is_sufficient": bool, "missing_info": str|None}
    充足时返回 is_sufficient=True，由 generate_node 生成报告。
    """
    llm = _build_llm(config)
    iteration = state.get("iteration_count", 0)

    user_request = _extract_user_request(state)
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

    verdict = _parse_json(_response_text(response), default={
        "sufficient": False,
        "reasoning": _response_text(response),
        "missing": "LLM 响应解析失败",
    })

    # 强制兜底
    if iteration >= MAX_ITERATIONS and not verdict.get("sufficient"):
        logger.warning("[Evaluate] 强制 sufficient=true (iter=%d)", iteration)
        verdict["sufficient"] = True

    logger.info("[Evaluate] iter=%d, sufficient=%s", iteration, verdict.get("sufficient"))

    return {
        "is_sufficient": verdict.get("sufficient", False),
        "missing_info": verdict.get("missing") if not verdict.get("sufficient") else None,
    }


# ── Generate 节点 ────────────────────────────────────────

async def generate_node(state: AgentState, config: dict) -> dict:
    """
    生成节点 — 使用 LLM 将所有已收集信息合成为 Markdown 简报。

    这是专用的报告生成阶段，不涉及工具调用或信息收集判断。
    """
    from datetime import date

    llm = _build_llm(config, temperature=0.4)  # 生成阶段略高温度，文笔更自然

    user_request = _extract_user_request(state)
    collected_results = _format_collected_results(state.get("execution_results", []))

    system_prompt = GENERATE_SYSTEM_PROMPT.format(date=date.today().isoformat())

    user_prompt = GENERATE_USER_PROMPT.format(
        user_request=user_request,
        collected_results=collected_results or "（无数据）",
    )

    response = await llm.ainvoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])

    report = _response_text(response).strip()

    # 如果 LLM 意外包裹了 JSON，清理掉
    if report.startswith("{") and report.endswith("}"):
        parsed = _parse_json(report, default={})
        if "final_report" in parsed:
            report = parsed["final_report"]

    logger.info("[Generate] 报告已生成 (%d chars)", len(report))
    return {"final_report": report}


# ── 辅助函数 ─────────────────────────────────────────────

def _extract_user_request(state: AgentState) -> str:
    if not state.get("messages"):
        return ""
    first = state["messages"][0]
    return first.get("content", "") if isinstance(first, dict) else str(first)


def _build_llm(config: dict, temperature: float = 0.2):
    from langchain_openai import ChatOpenAI

    cfg = config.get("configurable", {})
    return ChatOpenAI(
        api_key=cfg.get("llm_api_key", ""),
        model=cfg.get("llm_model", "gpt-4o"),
        base_url=cfg.get("llm_base_url", "https://api.openai.com/v1"),
        temperature=temperature,
        streaming=True,
    )


def _get_mcp_manager(config: dict):
    manager = config.get("configurable", {}).get("mcp_manager")
    if manager is None:
        from ..mcp.client import MCPClientManager

        logger.warning("[Execute] MCP manager 未注入")
        return MCPClientManager(servers=[])
    return manager


def _response_text(response) -> str:
    """提取 LangChain AIMessage 的纯文本内容（处理 str|list 联合类型）"""
    content = response.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b["text"] if isinstance(b, dict) and "text" in b else str(b)
            for b in content
        )
    return str(content)


def _format_tool_descriptions() -> str:
    lines = []
    for t in TOOL_DEFINITIONS:
        props = t.get("parameters", {}).get("properties", {})
        required = t["parameters"].get("required", [])
        param_str = ", ".join(
            f"{k}: {v.get('type','str')}{'*' if k in required else ''}"
            for k, v in props.items()
        )
        lines.append(f"- **{t['name']}**: {t['description']}\n  参数: {param_str}")
    return "\n".join(lines)


def _format_collected_results(results: list[dict]) -> str:
    if not results:
        return ""
    parts = []
    for i, r in enumerate(results, 1):
        name = r.get("tool_name", "unknown")
        if r.get("error"):
            parts.append(f"{i}. [{name}] ❌ {r['error']}")
        else:
            s = json.dumps(r.get("result"), ensure_ascii=False, indent=2)
            if len(s) > 2000:
                s = s[:2000] + "...(truncated)"
            parts.append(f"{i}. [{name}] ✅\n{s}")
    return "\n\n".join(parts)


def _parse_json(content: str, default: dict) -> dict:
    # 尝试 ```json ... ``` 代码块
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
    if m:
        json_str = m.group(1).strip()
    else:
        brace_start = content.find("{")
        brace_end = content.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            json_str = content[brace_start:brace_end + 1]
        else:
            return default

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse failed: %s", e)
        return default
