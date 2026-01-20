import pandas as pd
from typing import Dict, Optional
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from chromadb.config import Settings as ChromaSettings
from config import Config, logger


class WineKnowledgeBase:
    """Управление базой знаний о винах"""

    def __init__(self):
        self.wine_prices: Optional[pd.DataFrame] = None
        self.food_wine_table: Optional[str] = None
        self.regions_info: Dict[str, str] = {}
        self.wines_info: Dict[str, str] = {}
        self.menu_info: Dict[str, str] = {}

        self.load_all_data()

    def load_all_data(self):
        """Загрузка всех данных"""
        self.load_price_data()
        self.load_food_wine_table()
        self.load_structured_data()

    def load_price_data(self):
        """Загрузка прайс-листов"""
        try:
            price_files = [
                Config.DATA_DIR / "wine-price-ru.xlsx",
                Config.DATA_DIR / "wine-price.xlsx"
            ]

            for price_file in price_files:
                if price_file.exists():
                    self.wine_prices = pd.read_excel(price_file)
                    logger.info(f"Загружен прайс-лист: {len(self.wine_prices)} позиций")
                    break
        except Exception as e:
            logger.error(f"Ошибка загрузки прайс-листа: {e}")

    def load_food_wine_table(self):
        """Загрузка таблицы сочетаний еды и вина"""
        try:
            md_file = Config.DATA_DIR / "food_wine_table.md"

            if md_file.exists():
                with open(md_file, "r", encoding="utf-8") as f:
                    self.food_wine_table = f.read()
                logger.info("Загружена таблица сочетаний (markdown)")
        except Exception as e:
            logger.error(f"Ошибка загрузки таблицы сочетаний: {e}")

    def load_structured_data(self):
        """Загрузка структурированных данных"""
        regions_txt = Config.DATA_DIR / "regions.txt"
        if regions_txt.exists():
            for txt_file in regions_txt.glob("*.txt"):
                try:
                    with open(txt_file, "r", encoding="utf-8") as f:
                        self.regions_info[txt_file.stem] = f.read()
                except Exception as e:
                    logger.error(f"Ошибка загрузки региона {txt_file.name}: {e}")

        wines_txt = Config.DATA_DIR / "wines.txt"
        if wines_txt.exists():
            for txt_file in wines_txt.glob("*.txt"):
                try:
                    with open(txt_file, "r", encoding="utf-8") as f:
                        self.wines_info[txt_file.stem] = f.read()
                except Exception as e:
                    logger.error(f"Ошибка загрузки вина {txt_file.name}: {e}")

        menu_dir = Config.DATA_DIR / "menu"
        if menu_dir.exists():
            for md_file in menu_dir.glob("*.md"):
                try:
                    with open(md_file, "r", encoding="utf-8") as f:
                        self.menu_info[md_file.stem] = f.read()
                except Exception as e:
                    logger.error(f"Ошибка загрузки меню {md_file.name}: {e}")

        logger.info(f"Загружено: {len(self.regions_info)} регионов, "
                    f"{len(self.wines_info)} сортов вин, {len(self.menu_info)} меню")


class VectorStore:
    """Управление векторной базой данных"""

    def __init__(self, kb: WineKnowledgeBase):
        self.kb = kb

        self.embeddings = OllamaEmbeddings(
            base_url=Config.OLLAMA_URL,
            model=Config.EMBEDDING_MODEL
        )

        self.vectorstore = None
        self.initialize()

    def initialize(self):
        """Инициализация векторной базы"""
        try:
            documents = self._load_documents()

            if not documents:
                logger.warning("Нет документов для индексации")
                return

            splits = self._split_documents(documents)

            self.vectorstore = Chroma.from_documents(
                documents=splits,
                embedding=self.embeddings,
                persist_directory=str(Config.CHROMA_DIR),
                client_settings=ChromaSettings(anonymized_telemetry=False)
            )

            logger.info(f"Проиндексировано {len(documents)} документов, создано {len(splits)} чанков")

        except Exception as e:
            logger.error(f"Ошибка инициализации векторной базы: {e}")

    def _load_documents(self):
        """Загрузка документов"""
        documents = []

        wines_txt = Config.DATA_DIR / "wines.txt"
        if wines_txt.exists():
            for txt_file in wines_txt.glob("*.txt"):
                try:
                    with open(txt_file, "r", encoding="utf-8") as f:
                        documents.append(Document(
                            page_content=f.read(),
                            metadata={"source": str(txt_file), "type": "wine", "name": txt_file.stem}
                        ))
                except Exception as e:
                    logger.error(f"Ошибка загрузки {txt_file}: {e}")

        regions_txt = Config.DATA_DIR / "regions.txt"
        if regions_txt.exists():
            for txt_file in regions_txt.glob("*.txt"):
                try:
                    with open(txt_file, "r", encoding="utf-8") as f:
                        documents.append(Document(
                            page_content=f.read(),
                            metadata={"source": str(txt_file), "type": "region", "name": txt_file.stem}
                        ))
                except Exception as e:
                    logger.error(f"Ошибка загрузки {txt_file}: {e}")

        menu_dir = Config.DATA_DIR / "menu"
        if menu_dir.exists():
            for md_file in menu_dir.glob("*.md"):
                try:
                    with open(md_file, "r", encoding="utf-8") as f:
                        documents.append(Document(
                            page_content=f.read(),
                            metadata={"source": str(md_file), "type": "menu", "name": md_file.stem}
                        ))
                except Exception as e:
                    logger.error(f"Ошибка загрузки {md_file}: {e}")

        food_wine_md = Config.DATA_DIR / "food_wine_table.md"
        if food_wine_md.exists():
            try:
                with open(food_wine_md, "r", encoding="utf-8") as f:
                    documents.append(Document(
                        page_content=f.read(),
                        metadata={"source": str(food_wine_md), "type": "pairing"}
                    ))
            except Exception as e:
                logger.error(f"Ошибка загрузки таблицы сочетаний: {e}")

        return documents

    def _split_documents(self, documents):
        """Разбиение документов на чанки"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        return text_splitter.split_documents(documents)

    def search(self, query: str, k: int = 3, filter_type: Optional[str] = None):
        """Поиск в векторной базе"""
        if not self.vectorstore:
            return []

        try:
            filter_dict = {"type": filter_type} if filter_type else None
            docs = self.vectorstore.similarity_search(query, k=k, filter=filter_dict)
            return docs
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []