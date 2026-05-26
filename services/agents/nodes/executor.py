import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from llm import get_llm
from state import AgentState
from tools import dispatch_tool

EXECUTOR_SYSTEM = """
Execute ONE plan step. If you need a tool, respond with JSON:
{"tool": "tool_name", "input": {...}}
Otherwise respond with JSON: {"done": true, "summary": "what you accomplished"}
"""


async def run(state: AgentState) -> AgentState:
    plan = state.get("plan", [])
    step_idx = state.get("step", 0)

    if step_idx >= len(plan):
        return {**state, "status": "running"}

    current_step = plan[step_idx]
    llm = get_llm(1024)
    resp = await llm.ainvoke(
        [
            SystemMessage(content=EXECUTOR_SYSTEM),
            HumanMessage(
                content=(
                    f"Step {step_idx + 1}: {current_step}\n\n"
                    f"Prior results: {state.get('tool_results', [])[-3:]}"
                )
            ),
        ]
    )
    text = resp.content if isinstance(resp.content, str) else str(resp.content)

    match = re.search(r"\{[\s\S]*\}", text)
    tool_results = list(state.get("tool_results", []))

    if match:
        try:
            data = json.loads(match.group())
            if data.get("tool"):
                result = await dispatch_tool(data["tool"], data.get("input", {}))
                tool_results.append(
                    {"step": step_idx, "tool": data["tool"], "result": result}
                )
                return {
                    **state,
                    "tool_results": tool_results,
                    "step": step_idx,
                    "progress_message": f"Ran {data['tool']}",
                }
            if data.get("done"):
                return {
                    **state,
                    "step": step_idx + 1,
                    "progress_message": data.get(
                        "summary",
                        f"Completed step {step_idx + 1}",
                    ),
                }
        except json.JSONDecodeError:
            pass

    return {
        **state,
        "step": step_idx + 1,
        "progress_message": f"Completed step {step_idx + 1}",
    }
