from common.types import GraphState
from common.llm import llm
from langchain.schema import AIMessage

def chat_agent(state: GraphState) -> GraphState:
    try:
        response = llm.invoke(state["messages"])
    except Exception as e:
        response = AIMessage(content=f"⚠️ Failed to generate chat response: {e}")
    return {"messages": state["messages"] + [response]}