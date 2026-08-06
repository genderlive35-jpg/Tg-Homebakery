import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN=os.getenv("BOT_TOKEN","")
WEBAPP_URL=os.getenv("WEBAPP_URL","")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb=[[InlineKeyboardButton("🛍 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text("Добро пожаловать в магазин!", reply_markup=InlineKeyboardMarkup(kb))

if __name__=="__main__":
    if not TOKEN or not WEBAPP_URL:
        raise RuntimeError("Укажи BOT_TOKEN и WEBAPP_URL")
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.run_polling()
