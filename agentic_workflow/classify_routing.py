from langchain.schema import HumanMessage
from common.types import GraphState
from common.llm import llm

def route(state: GraphState) -> str:
    last_user_msg = state["messages"][-1].content
    system_prompt = (
        "You are a routing assistant. Classify the user's message as either:\n"
        "- 'github_agent': if it is about repositories, pull requests, GitHub-related tasks\n"
        "- 'chat_agent': for anything else (general conversation, non-GitHub questions)\n"
        "Respond with only the label: 'github_agent' or 'chat_agent'."
    )

    try:
        classification = llm.invoke([
            HumanMessage(content=system_prompt),
            HumanMessage(content=last_user_msg)
        ])
        route_decision = classification.content.strip().lower()
        if route_decision not in ["github_agent", "chat_agent"]:
            route_decision = "chat_agent"
        return route_decision
    except Exception as e:
        print(f"⚠️ Routing failed: {e}. Defaulting to 'chat_agent'")
        return "chat_agent"