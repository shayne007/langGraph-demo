import pytest
from chat_with_human_interrupt import graph, State
import uuid
from langchain_core.messages import AIMessage

def test_graph_initialization():
    """Test that the graph is properly initialized"""
    assert graph is not None
    
def test_basic_chat_flow():
    """Test basic chat interaction without human interruption"""
    # Initialize state with a simple message
    initial_state = State(messages=[{
        "role": "user",
        "content": "What is the capital of France?"
    }])
    
    # Run the graph with required checkpointer configuration
    config = {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "checkpoint_ns": "test",
            "checkpoint_id": str(uuid.uuid4())
        }
    }
    result = graph.invoke(initial_state, config=config)
    
    # Verify response exists
    assert "messages" in result
    assert len(result["messages"]) > 0
    assert isinstance(result["messages"][-1], AIMessage)
    
def test_state_structure():
    """Test that State class is properly structured"""
    state = State(messages=[])
    assert "messages" in state
    assert isinstance(state["messages"], list)

def test_tool_availability():
    """Test that required tools are available"""
    from chat_with_human_interrupt import tools
    for tool in tools:
      print(tool.name)
    assert len(tools) == 2
    assert any(tool.name == "human_assistance" for tool in tools)
    assert any(tool.name == "tavily_search_results_json" for tool in tools)  # Fixed tool name