import asyncio
from typing import Dict, Tuple, List, Optional
from langchain_community.llms import Ollama
from config import Config, logger
from knowledge_base import WineKnowledgeBase, VectorStore


class WineAssistant:
    """Ассистент по винам с RAG"""

    def __init__(self):
        self.llm = Ollama(
            base_url=Config.OLLAMA_URL,
            model=Config.MODEL_NAME,
            temperature=0.7
        )

        self.kb = WineKnowledgeBase()
        self.vector_store = VectorStore(self.kb)
        self.sessions: Dict[int, Dict] = {}

    def get_wines_list(self) -> List[Dict]:
        """Получение полного списка вин из меню"""
        menu_content = self.kb.menu_info.get('drinks', '')
        wines = []

        if menu_content:
            lines = menu_content.strip().split('\n')

            for line in lines:
                if '|' in line and not line.strip().startswith('|---'):
                    cells = [c.strip() for c in line.split('|') if c.strip()]
                    if len(cells) >= 2:
                        if cells[0].lower() in ['wine', 'drink', 'название']:
                            continue

                        wines.append({
                            'name': cells[0] if len(cells) > 0 else '',
                            'producer': cells[1] if len(cells) > 1 else '',
                            'year': cells[2] if len(cells) > 2 else '',
                            'type': cells[3] if len(cells) > 3 else '',
                            'price': cells[4] if len(cells) > 4 else ''
                        })

        return wines

    def format_wines_page(self, wines: List[Dict], page: int, per_page: int = 8) -> Tuple[str, int]:
        """Форматирование страницы вин"""
        total_wines = len(wines)
        total_pages = (total_wines + per_page - 1) // per_page

        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_wines)
        page_wines = wines[start_idx:end_idx]

        result = f"📋 **Винная карта** (страница {page}/{total_pages})\n\n"

        for wine in page_wines:
            result += f"🍷 **{wine['name']}**\n"
            details = []
            if wine['producer']:
                details.append(wine['producer'])
            if wine['year']:
                details.append(wine['year'])
            if wine['type']:
                details.append(wine['type'])

            if details:
                result += f"_{', '.join(details)}_\n"

            if wine['price']:
                result += f"💰 {wine['price']} ₽\n"

            result += "\n"

        return result, total_pages

    def _detect_intent(self, message: str) -> Tuple[str, str]:
        """Определение намерения пользователя"""
        message_lower = message.lower()

        if any(word in message_lower for word in ['меню', 'menu', 'карта', 'что есть', 'покажи вина']):
            return 'menu', 'drinks'

        if any(word in message_lower for word in ['цена', 'стоимость', 'сколько стоит', 'price']):
            return 'price', message

        food_keywords = ['к ', 'под ', 'с ', 'стейк', 'рыба', 'мясо', 'курица', 'сыр', 'десерт', 'блюд']
        if any(word in message_lower for word in food_keywords):
            return 'food_pairing', message

        if any(word in message_lower for word in ['регион', 'из ', 'бордо', 'тоскан', 'шампань', 'риоха']):
            return 'region', message

        grape_keywords = ['каберне', 'мерло', 'пино', 'шардоне', 'совиньон', 'сорт']
        if any(word in message_lower for word in grape_keywords):
            return 'grape', message

        return 'general', message

    def _get_context_for_intent(self, intent: str, query: str) -> str:
        """Получение контекста в зависимости от намерения"""
        context = ""

        if intent == 'menu':
            context = "Клиент запросил меню. Покажи винную карту."

        elif intent == 'price':
            if self.kb.wine_prices is not None:
                context = "Информация о ценах доступна в базе данных.\n"

        elif intent == 'food_pairing':
            if self.kb.food_wine_table:
                lines = self.kb.food_wine_table.split('\n')
                relevant = []
                for line in lines:
                    if any(word in line.lower() for word in query.lower().split()):
                        relevant.append(line)

                if relevant:
                    context = "Рекомендации по сочетанию с едой:\n" + '\n'.join(relevant[:3])

        elif intent == 'region':
            docs = self.vector_store.search(query, k=2, filter_type="region")
            if docs:
                context = "Информация о регионе:\n" + docs[0].page_content[:500]

        elif intent == 'grape':
            docs = self.vector_store.search(query, k=2, filter_type="wine")
            if docs:
                context = "Информация о сорте:\n" + docs[0].page_content[:500]

        else:
            docs = self.vector_store.search(query, k=2)
            if docs:
                context = "Релевантная информация:\n" + docs[0].page_content[:400]

        return context

    def _get_system_prompt(self) -> str:
        """System prompt для сомелье"""
        return """Ты - опытный сомелье в винном бутике. 

ВАЖНО:
- НЕ ЗДОРОВАЙСЯ в каждом ответе (только если клиент первый раз обращается)
- Будь лаконичным, но информативным

Стиль общения:
- Дружелюбный профессионал
- Даешь конкретные рекомендации с деталями
- Делишься интересными фактами
- Не выдумываешь информацию - используешь только то, что есть в контексте
- Если информации нет, честно говоришь об этом

Формат ответов:
- Простой структурированный текст
- Используй **жирный** только для названий вин
- Нумерованные списки для нескольких вариантов
- Никаких эмодзи в середине текста

Твоя задача - помочь клиенту выбрать вино быстро и точно!"""

    def _get_session(self, user_id: int) -> Dict:
        """Получение или создание сессии"""
        if user_id not in self.sessions:
            self.sessions[user_id] = {"messages": []}
        return self.sessions[user_id]

    async def process_message(self, user_id: int, message: str) -> str:
        """Обработка сообщения пользователя"""
        session = self._get_session(user_id)

        intent, query = self._detect_intent(message)

        context = self._get_context_for_intent(intent, query)

        history = ""
        if session["messages"]:
            recent_messages = session["messages"][-4:]
            history = "\n".join([
                f"{'Клиент' if msg['role'] == 'user' else 'Ты'}: {msg['content']}"
                for msg in recent_messages
            ])
            history = f"\nПредыдущий диалог:\n{history}\n"

        full_prompt = f"""{self._get_system_prompt()}

{context}
{history}
Клиент: {message}
Ты:"""
        try:
            response = await asyncio.to_thread(self.llm.invoke, full_prompt)
            response = response.strip()

            response = response.replace('{"function":', '').replace('"arguments":', '')

        except Exception as e:
            logger.error(f"Ошибка LLM: {e}")
            return "Извините, произошла ошибка. Попробуйте переформулировать вопрос."

        session["messages"].append({"role": "user", "content": message})
        session["messages"].append({"role": "assistant", "content": response})

        if len(session["messages"]) > Config.MAX_HISTORY_MESSAGES:
            session["messages"] = session["messages"][-Config.MAX_HISTORY_MESSAGES:]

        return response

    def clear_session(self, user_id: int):
        """Очистка сессии пользователя"""
        if user_id in self.sessions:
            del self.sessions[user_id]
