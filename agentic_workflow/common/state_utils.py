from typing import List
from langchain_core.messages import BaseMessage, HumanMessage
from common.types import GraphState
from common.llm import llm

def summarize_conversation(messages: List[BaseMessage]) -> str:
    conversation_text = "\n".join([msg.content for msg in messages])
    summary_prompt = (
        "You are a helpful assistant. Summarize the following conversation in a concise manner:\n"
        f"{conversation_text}\n"
        "Summarize in 2-3 sentences."
    )
    try:
        response = llm.invoke([HumanMessage(content=summary_prompt)])
        return response.content
    except Exception as e:
        return f"⚠️ Failed to summarize conversation: {e}"