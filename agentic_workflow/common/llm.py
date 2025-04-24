from langchain_openai import ChatOpenAI
import os

# Use OpenAI API key from environment variables
llm = ChatOpenAI(
    model="deepseek-chat",  
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0.0
)