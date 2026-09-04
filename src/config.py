import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _resolve_project_path(raw_path: str | Path) -> Path:
    path = Path(raw_path).expanduser()
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

DB_URI = os.getenv("DB_URI")
POSTGRES_POOL_SIZE = int(os.getenv("POSTGRES_POOL_SIZE", "10"))

LOCAL_DB_PATH = _resolve_project_path(
    os.getenv("LOCAL_DB_PATH", "var/car_helper.db")
)
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "7860"))
CORS_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:7860,http://localhost:7860",
    ).split(",")
    if origin.strip()
)
