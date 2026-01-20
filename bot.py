from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import Config, logger
from assistant import WineAssistant
from handlers import BotHandlers


async def post_init(application: Application):
    """Настройка команд бота после инициализации"""
    commands = [
        BotCommand("start", "🍷 Начать работу с ботом"),
        BotCommand("menu", "📋 Показать винную карту"),
        BotCommand("clear", "🗑 Очистить историю диалога"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Команды бота установлены")


def main():
    """Запуск бота"""
    try:
        Config.validate()
        logger.info("Инициализация бота...")

        assistant = WineAssistant()
        handlers = BotHandlers(assistant)

        app = Application.builder().token(Config.TELEGRAM_TOKEN).build()

        app.add_handler(CommandHandler("start", handlers.start))
        app.add_handler(CommandHandler("clear", handlers.clear))
        app.add_handler(CommandHandler("menu", handlers.menu_command))
        app.add_handler(CallbackQueryHandler(handlers.menu_pagination))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
        app.add_error_handler(handlers.error_handler)

        app.post_init = post_init

        logger.info("Бот успешно запущен!")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
