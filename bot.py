import os

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo
)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)


TOKEN = os.getenv("BOT_TOKEN")

WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://tg-homebakery.onrender.com"
).rstrip("/")


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    keyboard = [

        [
            InlineKeyboardButton(
                "🛍 Открыть магазин",
                web_app=WebAppInfo(
                    url=WEBAPP_URL
                )
            )
        ],

        [
            InlineKeyboardButton(
                "⚙️ Админ-панель",
                web_app=WebAppInfo(
                    url=WEBAPP_URL + "/admin"
                )
            )
        ]

    ]

    await update.message.reply_text(
        "Добро пожаловать в магазин!",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


if __name__ == "__main__":

    if not TOKEN:
        raise RuntimeError(
            "Не задан BOT_TOKEN"
        )

    application = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    print("Бот запущен")

    application.run_polling()
