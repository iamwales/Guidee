from langgraph.graph import END, StateGraph
from nodes import action_agent, dom_agent, instruction_agent, summarizer, vision_agent
from state import AgentState

graph = StateGraph(AgentState)
graph.add_node("vision", vision_agent.run)
graph.add_node("dom", dom_agent.run)
graph.add_node("instruct", instruction_agent.run)
graph.add_node("act", action_agent.run)
graph.add_node("summarize", summarizer.run)

graph.set_entry_point("vision")
graph.add_edge("vision", "dom")
graph.add_edge("dom", "instruct")
graph.add_edge("instruct", "act")
graph.add_edge("act", "summarize")
graph.add_edge("summarize", END)

browser_graph = graph.compile()
