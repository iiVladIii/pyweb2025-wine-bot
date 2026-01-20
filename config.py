import os
from pathlib import Path
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    MODEL_NAME = os.getenv("MODEL_NAME", "mistral")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

    DATA_DIR = Path("data")
    CHROMA_DIR = Path("./chroma_db")

    MAX_HISTORY_MESSAGES = 20
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 150
    MAX_SEARCH_RESULTS = 3

    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN не найден в .env файле!")

        if not cls.DATA_DIR.exists():
            logger.warning(f"Директория {cls.DATA_DIR} не найдена")
            cls.DATA_DIR.mkdir(parents=True)

        logger.info("Конфигурация успешно загружена")
