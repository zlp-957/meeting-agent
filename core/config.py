import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "meeting.db")
DB_URL = f"sqlite:///{DB_PATH}"

RULES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rules")
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
CHROMA_COLLECTION = "meeting_room_rules"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
