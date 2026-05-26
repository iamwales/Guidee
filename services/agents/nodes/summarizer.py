from langchain_core.messages import HumanMessage, SystemMessage
from llm import get_llm
from state import AgentState

SUMMARIZER_SYSTEM = """
Synthesize a clear, concise answer for the user based on the task and tool results.
Be direct. No filler. Use bullets only if helpful.
"""


async def run(state: AgentState) -> AgentState:
    task = state.get("task", "")
    results = state.get("tool_results", [])
    llm = get_llm(1024)
    resp = await llm.ainvoke([
        SystemMessage(content=SUMMARIZER_SYSTEM),
        HumanMessage(content=f"Task: {task}\n\nResults: {results}"),
    ])
    text = resp.content if isinstance(resp.content, str) else str(resp.content)
    return {
        **state,
        "result": text,
        "status": "done",
        "progress_message": "Task complete",
    }
