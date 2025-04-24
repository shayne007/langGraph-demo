from common.types import GraphState
from langgraph.graph import StateGraph

from chat_agent import chat_agent
from classify_routing import route
from github_agent import github_agent
from checkpointing import load_checkpoint, save_checkpoint

from langchain_core.messages import HumanMessage

import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

graph_builder = StateGraph(GraphState)


builder = StateGraph(GraphState)
builder.add_node("chat_agent", chat_agent)
builder.add_node("github_agent", github_agent)
builder.add_node("route", lambda x: x)

builder.add_conditional_edges("route", route, {
    "chat_agent": "chat_agent",
    "github_agent": "github_agent"
})

builder.set_entry_point("route")
builder.set_finish_point("chat_agent")
builder.set_finish_point("github_agent")

try:
    graph = builder.compile()
except Exception as e:
    raise RuntimeError(f"❌ Failed to compile LangGraph: {e}")

def run_chat():
    try:
        thread_id = input("Enter chat ID (or press enter to start new): ").strip()
        if not thread_id:
            thread_id = os.urandom(4).hex()
            print(f"🆕 New conversation started: {thread_id}")
        else:
            print(f"🔁 Resuming conversation: {thread_id}")

        state = load_checkpoint(thread_id)

        while True:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit", "bye"]:
                save_checkpoint(thread_id, state)
                print(f"\n💾 Saved. Resume using ID: {thread_id}")
                break

            state["messages"].append(HumanMessage(content=user_input))
            try:
                state = graph.invoke(state)
                print("\nAI:", state["messages"][-1].content)
            except Exception as e:
                print(f"⚠️ Error during graph invocation: {e}")

    except Exception as e:
        print(f"❌ Critical error: {e}")


if __name__ == "__main__":
    print("🤖 LangGraph Chatbot (Deepseek + GitHub Agent with Routing)")
    run_chat()