from chat_with_memory import graph
from langchain_core.messages import HumanMessage
import uuid

def create_config():
    """Create a unique configuration for each test run"""
    return {
        "thread_id": str(uuid.uuid4()),
        "checkpoint_id": str(uuid.uuid4()),
        "checkpoint_ns": "default"
    }

# Test initial query with memory
messages = [HumanMessage(content="What is the latest news about artificial intelligence?")]
config = create_config()

# Run the graph with initial messages
result = graph.invoke(
    {"messages": messages},
    config=config
)

# Print the initial response
print("Bot's response:", result["messages"][-1].content)

# Test follow-up question using memory
messages.extend(result["messages"])
messages.append(HumanMessage(content="Can you provide more specific details about what you just mentioned?"))

# Get another response using the same configuration to maintain memory
result = graph.invoke(
    {"messages": messages},
    config=config
)
print("\nBot's follow-up response:", result["messages"][-1].content)

# Test memory persistence with a new query in the same thread
messages.extend(result["messages"])
messages.append(HumanMessage(content="How does this relate to recent developments in machine learning?"))

# Get final response using the same configuration
result = graph.invoke(
    {"messages": messages},
    config=config
)
print("\nBot's final response:", result["messages"][-1].content)