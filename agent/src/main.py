"""
矿权日报 Agent — 主入口

基于 LangGraph ReAct 模式 (Plan → Execute → Evaluate)，
编排 3 个 MCP Server 生成日报简报。

支持两种运行模式：
  - 普通模式: python -m agent.src.main -p "..."
  - 流式模式: python -m agent.src.main -p "..." --stream
"""

import argparse
import asyncio
import json
import logging
import sys

from dotenv import load_dotenv

from .agent.graph import create_agent_graph
from .agent.state import AgentState
from .mcp.client import MCPClientManager, MCPServerConfig
from .utils.config import get_config

load_dotenv()

logger = logging.getLogger(__name__)


# ── SSE 事件编码 ────────────────────────────────────────────

def _sse_event(event: str, data: dict | str) -> str:
    """将事件编码为 SSE 格式"""
    payload = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else data
    return f"event: {event}\ndata: {payload}\n\n"


# ── 核心运行逻辑 ────────────────────────────────────────────

async def run(prompt: str, stream: bool = False):
    """
    运行 Agent。

    Args:
        prompt: 用户输入
        stream: 是否以 SSE 格式流式输出
    """
    config_obj = get_config()

    # 1. 初始化 MCP Client
    mcp_servers = [
        MCPServerConfig(
            name=s["name"],
            command=s.get("command", "python"),
            args=s.get("args", []),
        )
        for s in config_obj.mcp_servers
    ]
    mcp_manager = MCPClientManager(mcp_servers)
    await mcp_manager.connect_all()

    # 2. 构建 LangGraph
    graph = create_agent_graph()

    # 3. 运行时配置
    runtime_config = {
        "configurable": {
            "llm_api_key": config_obj.llm_api_key,
            "llm_model": config_obj.llm_model,
            "llm_base_url": config_obj.llm_base_url,
            "mcp_manager": mcp_manager,
        }
    }

    initial_state: AgentState = {
        "messages": [{"role": "user", "content": prompt}],
        "plan": None,
        "execution_results": [],
        "iteration_count": 0,
        "is_sufficient": None,
        "missing_info": None,
        "final_report": None,
    }

    try:
        if stream:
            await _run_streaming(graph, initial_state, runtime_config)
        else:
            result = await graph.ainvoke(initial_state, runtime_config)
            _print_result(result)
    finally:
        await mcp_manager.disconnect_all()


async def _run_streaming(graph, initial_state: AgentState, config: dict) -> None:
    """
    SSE 流式模式 — 使用 astream_events() 实时输出每个节点的进展。

    输出事件类型:
      - phase: 阶段切换 (think / execute / evaluate)
      - think_token: Think 节点 LLM 流式 token
      - tool_call: 工具调用开始
      - tool_result: 工具调用结果
      - report: 最终简报
      - error: 错误信息
    """
    print(_sse_event("phase", {"phase": "start", "message": "Agent 启动"}))

    iteration = 0

    async for event in graph.astream_events(initial_state, config, version="v2"):
        kind = event.get("event", "")
        name = event.get("name", "")
        data = event.get("data", {})

        # ── 节点进入/退出 ──
        if kind == "on_chain_start" and name in ("think", "execute", "evaluate"):
            phase_label = {"think": "规划中...", "execute": "执行工具...", "evaluate": "评估结果..."}
            print(_sse_event("phase", {
                "phase": name,
                "message": phase_label.get(name, name),
                "iteration": iteration,
            }))

        # ── LLM 流式 token（Think 节点） ──
        if kind == "on_chat_model_stream" and name == "think":
            chunk = data.get("chunk", {})
            if hasattr(chunk, "content") and chunk.content:
                print(_sse_event("think_token", {"token": chunk.content}))

        # ── 工具调用 ──
        if kind == "on_chain_end" and name == "execute":
            output = data.get("output", {})
            results = output.get("execution_results", [])
            for r in results:
                print(_sse_event("tool_result", {
                    "tool": r.get("tool_name", ""),
                    "error": r.get("error"),
                    "result_preview": str(r.get("result", ""))[:500],
                }))

        # ── 评估完成 ──
        if kind == "on_chain_end" and name == "evaluate":
            output = data.get("output", {})
            if output.get("is_sufficient"):
                print(_sse_event("phase", {"phase": "done", "message": "信息充足，生成简报"}))
            else:
                print(_sse_event("phase", {
                    "phase": "loop",
                    "message": f"信息不足: {output.get('missing_info', '')}",
                }))
                iteration += 1

        # ── 最终输出 ──
        if kind == "on_chain_end" and name == "LangGraph":
            final_output = data.get("output", {})
            report = final_output.get("final_report", "")
            if report:
                print(_sse_event("report", {"content": report}))

    print(_sse_event("phase", {"phase": "finish", "message": "Done"}))


def _print_result(result: dict) -> None:
    """普通模式：打印最终结果"""
    report = result.get("final_report", "")
    if report:
        print("\n" + "=" * 60)
        print(report)
        print("=" * 60)
    else:
        print("\n⚠️ 未能生成报告")
        print(f"迭代次数: {result.get('iteration_count', 0)}")
        print(f"执行结果数: {len(result.get('execution_results', []))}")


# ── CLI ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="矿权日报 Agent — LangGraph ReAct (Plan→Execute→Evaluate)",
    )
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        default="给我生成一份关于 Pilbara 锂矿的今日简报",
        help="输入提示词",
    )
    parser.add_argument(
        "--stream", "-s",
        action="store_true",
        default=False,
        help="启用 SSE 流式输出模式",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,  # 日志输出到 stderr，不污染 SSE 流
    )

    asyncio.run(run(args.prompt, stream=args.stream))


if __name__ == "__main__":
    main()
