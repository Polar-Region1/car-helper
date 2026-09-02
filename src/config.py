import os
from dotenv import load_dotenv

load_dotenv(override=True)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL")

LANGSMITH_API_KEY = os.getenv("LANSMITH_API_KEY")

SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

DB_URI = os.getenv("DB_URI", "postgresql://postgres:root@localhost:5432/car_helper_sessions")
SESSION_ID_PATH = "./session_id.json"