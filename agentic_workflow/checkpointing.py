import json
import os
from common.types import GraphState
from common.state_utils import summarize_conversation

def load_checkpoint(thread_id: str) -> GraphState:
    try:
        with open(f"checkpoints/{thread_id}.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"messages": []}

def save_checkpoint(thread_id: str, state: GraphState) -> None:
    os.makedirs("checkpoints", exist_ok=True)
    summary = summarize_conversation(state)
    with open(f"checkpoints/{thread_id}.json", "w") as f:
        json.dump(state, f)