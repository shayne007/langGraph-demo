from typing import Annotated

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing_extensions import TypedDict

from mem0 import MemoryClient
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class State(TypedDict):
    messages: Annotated[list, add_messages]
    mem0_user_id: str


graph_builder = StateGraph(State)


tool = TavilySearchResults(max_results=2)
tools = [tool]
llm = ChatOpenAI(
    model="deepseek-chat",  
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0.0
)
llm_with_tools = llm.bind_tools(tools)
mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

def chatbot(state: State):
    messages = state["messages"]
    mem0_user_id = state["mem0_user_id"]
    print("messages::", messages)
    print("mem0_user_id::", mem0_user_id)
    # Retrieve relevant memories
    memories = mem0_client.search(messages[-1].content, user_id=mem0_user_id)
    print("memories::", memories)
    context = "Relevant information from previous conversations:\n"
    for memory in memories:
        context += f"- {memory['memory']}\n"

    system_message = SystemMessage(content=f"""You are a helpful customer support assistant. Use the provided context to personalize your responses and remember user preferences and past interactions.
{context}""")
    full_messages = [system_message] + messages
    print("full_messages::", full_messages)
    response = llm_with_tools.invoke(full_messages)

    # Store the interaction in Mem0
    mem0_client.add(f"User: {messages[-1].content}\nAssistant: {response.content}", user_id=mem0_user_id)
    
    return {"messages": [response]}


graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=[tool])
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
graph_builder.add_edge("tools", "chatbot")
graph_builder.set_entry_point("chatbot")


compiled_graph = graph_builder.compile()


def run_conversation(user_input: str, mem0_user_id: str):
    config = {"configurable": {"thread_id": mem0_user_id}}
    state = {"messages": [HumanMessage(content=user_input)], "mem0_user_id": mem0_user_id}

    for event in compiled_graph.stream(state, config):
        for value in event.values():
            if value.get("messages"):
                print("Customer Support:", value["messages"][-1].content)
                return

if __name__ == "__main__":
    print("Welcome to Customer Support! How can I assist you today?")
    mem0_user_id = "customer_123"  # You can generate or retrieve this based on your user management system
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Customer Support: Thank you for contacting us. Have a great day!")
            break
        run_conversation(user_input, mem0_user_id)
