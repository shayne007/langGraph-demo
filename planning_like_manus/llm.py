import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from langchain_openai import ChatOpenAI

def DeepSeekV3():
    return ChatOpenAI(
        model= "deepseek-chat",
        api_key= os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )

def Tongyi():
    return ChatOpenAI(
        model="qwen-max",
        api_key=os.environ.get("AI_DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

def DeepSeekR1():
    return ChatOpenAI(
        model= "deepseek-reasoner",
        api_key= os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )