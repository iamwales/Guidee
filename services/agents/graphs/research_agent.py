from langgraph.graph import END, StateGraph
from nodes import research
from state import AgentState

graph = StateGraph(AgentState)
graph.add_node("search", research.search)
graph.add_node("fetch", research.fetch_sources)
graph.add_node("synthesize", research.synthesize)
graph.set_entry_point("search")
graph.add_edge("search", "fetch")
graph.add_edge("fetch", "synthesize")
graph.add_edge("synthesize", END)

research_agent = graph.compile()
