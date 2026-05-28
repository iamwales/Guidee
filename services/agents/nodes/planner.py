from llm import complete_json
from state import AgentState

PLANNER_SYSTEM = """
Break the user's task into 3–7 concrete steps. For each step, name the tool to use.
Output JSON only: {"steps": ["Step 1: ... (tool: web_search)", ...]}
Available tools:
- web_search
- browse_url
- read_file
- write_file
- edit_file
- list_directory
- summarize_file
- send_email
- draft_email
- reply_email
- validate_recipients
- get_gmail_oauth_url
- exchange_gmail_oauth_code
- run_code
"""


async def run(state: AgentState) -> AgentState:
    task = state.get("task", "")
    data = await complete_json(
        PLANNER_SYSTEM,
        f"Task: {task}",
        max_tokens=1024,
    )
    plan = data.get("steps", [f"Complete the task: {task}"])
    return {
        **state,
        "plan": plan,
        "step": 0,
        "status": "running",
        "progress_message": f"Planned {len(plan)} steps",
    }
