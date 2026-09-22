import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django

django.setup()

from asgiref.sync import sync_to_async
from decouple import config
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from apps.users.telegram import complete_bot_start


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            'Animee bot. Kirish yoki Telegram ulash uchun saytdagi havolani oching.'
        )
        return

    unic_id = context.args[0]
    user = update.effective_user
    photo_url = ''
    try:
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            file = await context.bot.get_file(photos.photos[0][-1].file_id)
            path = file.file_path or ''
            if path.startswith('http'):
                photo_url = path
            elif path:
                photo_url = f'https://api.telegram.org/file/bot{context.bot.token}/{path}'
    except Exception:
        photo_url = ''

    payload = {
        'telegram_id': user.id,
        'username': user.username or '',
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
        'photo_url': photo_url,
    }
    reply = await sync_to_async(complete_bot_start)(unic_id, payload)
    await update.message.reply_text(reply)


app = ApplicationBuilder().token(config('BOT_TOKEN')).build()
app.add_handler(CommandHandler('start', start))
app.run_polling()
