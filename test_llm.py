"""
Isolated connectivity test — bypasses LangGraph entirely.
If this hangs or errors, the problem is the Gemini API call itself
(key, network, or model name), not the graph/checkpointer.
"""
import os
os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from src import config
from langchain_google_genai import ChatGoogleGenerativeAI

config.validate_config()
print(f"Using model: {config.GEMINI_MODEL}")
print(f"API key loaded: {'yes' if config.GEMINI_API_KEY else 'NO'} (length={len(config.GEMINI_API_KEY)})")

llm = ChatGoogleGenerativeAI(
    model=config.GEMINI_MODEL,
    google_api_key=config.GEMINI_API_KEY,
    temperature=0,
)

print("Calling Gemini...")
response = llm.invoke("Say hello in one short sentence.")
print("Response received:")
print(response.content)