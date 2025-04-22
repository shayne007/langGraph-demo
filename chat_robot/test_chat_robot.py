from chat_robot import graph
from langchain_core.messages import HumanMessage, AIMessage

# Initialize the chat
messages = [HumanMessage(content="Hello! How are you?")]

# Run the graph with initial messages
result = graph.invoke({"messages": messages})

# Print the result
print("Bot's response:", result["messages"][-1].content)

# Continue the conversation
messages.extend(result["messages"])
messages.append(HumanMessage(content="What can you help me with?"))

# Get another response
result = graph.invoke({"messages": messages})
print("\nBot's response:", result["messages"][-1].content)