from langgraph.graph import END, StateGraph

from state import AgentState
from nodes import planner, executor, summarizer, router

graph = StateGraph(AgentState)
graph.add_node("planner", planner.run)
graph.add_node("executor", executor.run)
graph.add_node("summarizer", summarizer.run)
graph.set_entry_point("planner")
graph.add_edge("planner", "executor")
graph.add_conditional_edges(
    "executor",
    router.should_continue,
    {"continue": "executor", "summarize": "summarizer", "error": "summarizer"},
)
graph.add_edge("summarizer", END)

email_agent = graph.compile()
