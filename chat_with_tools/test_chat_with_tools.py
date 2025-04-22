from chat_with_tools import graph
from langchain_core.messages import HumanMessage

# Test a query that might require using the search tool
messages = [HumanMessage(content="What do you know about LangGraph?")]

# Run the graph with initial messages
result = graph.invoke({"messages": messages})

# Print the result
print("Bot's response:", result["messages"][-1].content)

# Test a follow-up question
messages.extend(result["messages"])
messages.append(HumanMessage(content="Can you explain more about LangGraph based on web search?"))

# Get another response
result = graph.invoke({"messages": messages})
print("\nBot's response:", result["messages"][-1].content)