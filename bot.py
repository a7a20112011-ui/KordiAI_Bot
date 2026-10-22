
import os
import asyncio
import logging

from groq import Groq
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CHANNEL = "@zhyanetall99"
CHANNEL_LINK = "https://t.me/zhyanetall99"

logging.basicConfig(level=logging.INFO)

ai = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def join_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📢 چوونە ناو چەناڵ",
            url=CHANNEL_LINK
        )],
        [InlineKeyboardButton(
            "✅ پشکنین بکە",
            callback_data="check_join"
        )]
    ])


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🌐 وەرگێڕان",
                callback_data="translate"
            ),
            InlineKeyboardButton(
                "✍️ یارمەتی نووسین",
                callback_data="writing"
            )
        ],
        [
            InlineKeyboardButton(
                "🎓 یارمەتی خوێندن",
                callback_data="study"
            ),
            InlineKeyboardButton(
                "💡 بیرۆکە",
                callback_data="ideas"
            )
        ]
    ])


async def is_member(user_id, context):
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL,
            user_id=user_id
        )
        return member.status in (
            "member", "administrator", "creator"
        )
    except Exception:
        logging.exception("Membership check failed")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "general"
    user_id = update.effective_user.id

    if not await is_member(user_id, context):
        await update.effective_message.reply_text(
            "👋 بەخێربێیت بۆ KordiAI!\n\n"
            "بۆ بەکارهێنانی بۆتەکە، سەرەتا ئەندامی "
            "چەناڵەکەمان ببە، پاشان پشکنین بکە.",
            reply_markup=join_keyboard()
        )
        return

    await update.effective_message.reply_text(
        "🤖 بەخێربێیت بۆ KordiAI!\n\n"
        "خزمەتگوزارییەک هەڵبژێرە:",
        reply_markup=main_keyboard()
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_member(query.from_user.id, context):
        await query.message.reply_text(
            "⚠️ بۆ بەکارهێنان سەرەتا ئەندامی چەناڵ ببە.",
            reply_markup=join_keyboard()
        )
        return

    if query.data == "check_join":
        await query.message.reply_text(
            "✅ ئەندامبوونت پشتڕاست کرایەوە!\n\n"
            "خزمەتگوزارییەک هەڵبژێرە:",
            reply_markup=main_keyboard()
        )
        return

    options = {
        "translate": ("translate", "🌐 دەقی دەتەوێت وەریبگێڕین بنێرە."),
        "writing": ("writing", "✍️ بنووسە دەتەوێت چ دەقێکت بۆ ئامادە بکەین."),
        "study": ("study", "🎓 پرسیاری خوێندنەکەت بنێرە."),
        "ideas": ("ideas", "💡 بڵێ بۆ چی بیرۆکەت دەوێت.")
    }

    if query.data in options:
        mode, prompt = options[query.data]
        context.user_data["mode"] = mode
        await query.message.reply_text(prompt)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.effective_message

    if not await is_member(user_id, context):
        await message.reply_text(
            "بۆ بەکارهێنان سەرەتا ئەندامی چەناڵ ببە.",
            reply_markup=join_keyboard()
        )
        return

    if ai is None:
        await message.reply_text(
            "⚠️ کلیلەکەی AI نەدۆزرایەوە. تکایە کۆمپیوتەرەکەت بپشکنە."
        )
        return

    mode = context.user_data.get("mode", "general")

    instructions = {
        "translate": "دەقەکە وەربگێڕە. ئەگەر زمانی ئامانج دیاری نەکرا، پرسیاری لێ بکە.",
        "writing": "یارمەتی نووسین بدە و دەقێکی سروشتی و باش ئامادە بکە.",
        "study": "وەک مامۆستایەکی یارمەتیدەر بە سادەیی ڕوونی بکەرەوە و نموونە بهێنە.",
        "ideas": "بیرۆکەی بەسوود و ڕێکخراو پێشکەش بکە.",
        "general": "بە ڕوونی و بەسوود وەڵامی پرسیارەکە بدەرەوە."
    }

    await message.reply_text("⏳ کەمێک چاوەڕێ بکە...")

    try:
        result = await asyncio.to_thread(
            ai.chat.completions.create,
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "تۆ KordiAI یارمەتیاری زیرەکی دەستکردیت. "
                        "بە کوردیی سۆرانی وەڵام بدەرەوە، "
                        "مەگەر بەکارهێنەر زمانی تر داوا بکات. "
                        + instructions.get(mode, instructions["general"])
                    )
                },
                {"role": "user", "content": message.text}
            ],
            max_tokens=800
        )

        answer = result.choices[0].message.content
        if not answer:
            answer = "ببورە، وەڵامێکم ئامادە نەبوو. دووبارە هەوڵ بدەرەوە."

        for i in range(0, len(answer), 4000):
            await message.reply_text(answer[i:i + 4000])

    except Exception:
        logging.exception("AI request failed")
        await message.reply_text(
            "⚠️ ئێستا نەتوانرا وەڵامێک ئامادە بکرێت. "
            "تکایە دواتر دووبارە هەوڵ بدەرەوە."
        )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    print("KordiAI is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
