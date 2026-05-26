import json
import re

from config import get_settings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import SecretStr

_client: ChatAnthropic | None = None


def get_llm(max_tokens: int = 1024) -> ChatAnthropic:
    global _client
    settings = get_settings()
    if _client is None:
        _client = ChatAnthropic(  # type: ignore[call-arg]
            model=settings.claude_model,
            api_key=SecretStr(settings.anthropic_api_key or "placeholder"),
            max_tokens=max_tokens,
        )
    return _client


async def complete_json(system: str, user: str, max_tokens: int = 1024) -> dict:
    llm = get_llm(max_tokens)
    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    resp = await llm.ainvoke(messages)
    text = resp.content if isinstance(resp.content, str) else str(resp.content)
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}
