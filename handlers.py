from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import logger
from utils import split_long_message


class BotHandlers:
    """Обработчики команд Telegram бота"""

    def __init__(self, assistant):
        self.assistant = assistant

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        await update.message.reply_text(
            "🍷 **Добро пожаловать в Винную Лавку!**\n\n"
            "Я - ваш личный сомелье и консультант по винам.\n\n"
            "**Я могу помочь вам:**\n"
            "🔍 Найти идеальное вино по описанию\n"
            "🌍 Рассказать о винодельческих регионах\n"
            "🍇 Объяснить особенности сортов винограда\n"
            "🍽️ Подобрать вино к вашему блюду\n"
            "💰 Узнать цены\n"
            "📋 Показать меню\n\n"
            "Просто напишите, что вас интересует! 🥂",
            parse_mode="Markdown"
        )

    async def clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка истории"""
        user_id = update.effective_user.id
        self.assistant.clear_session(user_id)
        await update.message.reply_text("✨ История диалога очищена")

    def _create_pagination_keyboard(self, page: int, total_pages: int) -> InlineKeyboardMarkup:
        """Создание клавиатуры пагинации"""
        keyboard = []

        buttons = []

        if page > 1:
            buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"menu_page_{page - 1}"))

        buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="ignore"))

        if page < total_pages:
            buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"menu_page_{page + 1}"))

        keyboard.append(buttons)

        return InlineKeyboardMarkup(keyboard)

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню (первая страница)"""
        wines = self.assistant.get_wines_list()

        if not wines:
            await update.message.reply_text("Меню временно недоступно 😔")
            return

        menu_text, total_pages = self.assistant.format_wines_page(wines, page=1)
        keyboard = self._create_pagination_keyboard(1, total_pages)

        await update.message.reply_text(
            menu_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    async def menu_pagination(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопок пагинации меню"""
        query = update.callback_query
        await query.answer()

        if query.data == "ignore":
            return

        if query.data.startswith("menu_page_"):
            page = int(query.data.split("_")[-1])

            wines = self.assistant.get_wines_list()
            menu_text, total_pages = self.assistant.format_wines_page(wines, page=page)
            keyboard = self._create_pagination_keyboard(page, total_pages)

            await query.edit_message_text(
                menu_text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_id = update.effective_user.id
        user_message = update.message.text

        await update.message.chat.send_action("typing")

        try:
            response = await self.assistant.process_message(user_id, user_message)

            parts = split_long_message(response)
            for part in parts:
                await update.message.reply_text(part, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Ошибка обработки: {e}", exc_info=True)
            await update.message.reply_text(
                "😔 Извините, произошла ошибка. Попробуйте переформулировать вопрос."
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ошибок"""
        logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
