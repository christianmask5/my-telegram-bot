# bot.py
import os
import json
import logging
from datetime import datetime
from typing import Dict

from telegram import Update, ChatJoinRequest, User
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatJoinRequestHandler,
    ContextTypes,
    filters
)

# ===============================
# CONFIGURATION & LOGGER
# ===============================
BOT_TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("OWNER_ID"))
CONFIG_FILE = "bot_config.json"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===============================
# UTILITAIRES POUR LE JSON
# ===============================
def load_config() -> Dict:
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Erreur chargement config: {e}")
    return {"channels": {}, "welcome_texts": {}, "welcome_pics": {}}

def save_config(config: Dict) -> None:
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.error(f"Erreur sauvegarde config: {e}")

bot_config = load_config()

# ===============================
# COMMANDES
# ===============================
from telegram.constants import ParseMode

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Désolé, vous n'êtes pas autorisé.")
        return

    # Récupérer le nom du bot
    bot_info = await context.bot.get_me()
    bot_name = bot_info.first_name

    # Récupérer le nom complet de l'admin humain
    try:
        admin_chat = await context.bot.get_chat(ADMIN_ID)
        admin_name = admin_chat.full_name
    except Exception as e:
        admin_name = "l'administrateur"
        print(f"Erreur récupération nom admin: {e}")

    # Créer le message stylé
    welcome_msg = (
        f"Bienvenue sur ton bot 🤖 *{bot_name}* !\n\n"
        f"👤 Administrateur : *{admin_name}*\n\n"
        "📚 *Commandes disponibles :*\n"
        "/addchannel <id> : pour ajouter un canal\n"
        "/listchannels : pour lister les canaux\n"
        "/setwelcometext <id> : pour définir le message à envoyer\n"
        "/setwelcomepic <id> : pour définir la photo à joindre au message\n\n"
        "⚙️ *Ajoute-moi comme administrateur de ton canal pour commencer !*"
    )

    await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN)


async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Vous n'êtes pas autorisé.")
        return
    if not bot_config["channels"]:
        await update.message.reply_text("Je ne gère encore aucun canal.")
        return

    message = "📋 Canaux gérés :\n\n"
    for cid, info in bot_config["channels"].items():
        message += (
            f"• {info.get('title', 'Inconnu')}\n\n"
            f"  ID : {cid}\n\n"
            f"  Texte : {'✅' if cid in bot_config['welcome_texts'] else '❌'}\n\n"
            f"  Photo : {'✅' if cid in bot_config['welcome_pics'] else '❌'}\n\n"
        )
    await update.message.reply_text(message)


async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Vous n'êtes pas autorisé.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /addchannel <channel_id>")
        return

    channel_id = context.args[0]
    try:
        chat = await context.bot.get_chat(channel_id)
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await update.message.reply_text("Je ne suis pas admin de ce canal.")
            return

        bot_config["channels"][channel_id] = {
            "title": chat.title,
            "username": chat.username,
            "added_at": datetime.now().isoformat()
        }
        save_config(bot_config)
        await update.message.reply_text(f"✅ Canal ajouté avec succès !\n\n"
                                        f"{'Nom :'} {chat.title}\n\n"
                                        f"{'ID : '} {channel_id}")
    except Exception as e:
        logger.error(f"Erreur add_channel: {e}")
        await update.message.reply_text(f"Erreur: {e}")

async def set_welcome_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Vous n'êtes pas autorisé.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /setwelcometext <channel_id>")
        return

    channel_id = context.args[0]
    if channel_id not in bot_config["channels"]:
        await update.message.reply_text("Canal non géré. Faites /addchannel d'abord.")
        return

    context.user_data["setting_welcome_text_for"] = channel_id
    await update.message.reply_text(
        f"Envoyez maintenant le message pour {bot_config['channels'][channel_id]['title']}."
    )

async def set_welcome_pic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Vous n'êtes pas autorisé.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /setwelcomepic <channel_id>")
        return

    channel_id = context.args[0]
    if channel_id not in bot_config["channels"]:
        await update.message.reply_text("Canal non géré. Faites /addchannel d'abord.")
        return

    context.user_data["setting_welcome_pic_for"] = channel_id
    await update.message.reply_text(f"Envoyez maintenant la photo pour {bot_config['channels'][channel_id]['title']}.")

# ===============================
# HANDLERS POUR LES DONNÉES
# ===============================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    data = context.user_data
    if "setting_welcome_text_for" in data:
        channel_id = data["setting_welcome_text_for"]
        bot_config["welcome_texts"][channel_id] = update.message.text
        save_config(bot_config)
        await update.message.reply_text("✅ Message enregistré !")
        del data["setting_welcome_text_for"]

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    data = context.user_data
    if "setting_welcome_pic_for" in data:
        channel_id = data["setting_welcome_pic_for"]
        photo_file_id = update.message.photo[-1].file_id
        bot_config["welcome_pics"][channel_id] = photo_file_id
        save_config(bot_config)
        await update.message.reply_text("✅ Photo enregistrée !")
        del data["setting_welcome_pic_for"]

# ===============================
# CHAT JOIN REQUEST HANDLER
# ===============================
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_id = str(update.chat_join_request.chat.id)
    user = update.chat_join_request.from_user
    logger.info(f"Nouvelle demande: {user.full_name} pour {channel_id}")

    try:
        await context.bot.approve_chat_join_request(
            chat_id=update.chat_join_request.chat.id,
            user_id=user.id
        )
        await send_welcome_message(user, channel_id, context)
    except Exception as e:
        logger.error(f"Erreur approbation: {e}")

async def send_welcome_message(user: User, channel_id: str, context: ContextTypes.DEFAULT_TYPE):
    try:
        welcome_text = bot_config["welcome_texts"].get(channel_id, "")
        welcome_pic = bot_config["welcome_pics"].get(channel_id)
        channel_name = bot_config["channels"].get(channel_id, {}).get("title", "ton canal")

        final_text = welcome_text.replace("{user}", user.full_name).replace("{channel}", channel_name)

        if welcome_pic:
            await context.bot.send_photo(chat_id=user.id, photo=welcome_pic, caption=final_text)
        else:
            await context.bot.send_message(chat_id=user.id, text=final_text)
    except Exception as e:
        logger.error(f"Erreur envoi message privé: {e}")

# ===============================
# MAIN
# ===============================
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("listchannels", list_channels))
    app.add_handler(CommandHandler("addchannel", add_channel))
    app.add_handler(CommandHandler("setwelcometext", set_welcome_text))
    app.add_handler(CommandHandler("setwelcomepic", set_welcome_pic))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.add_handler(ChatJoinRequestHandler(handle_join_request))

    app.run_polling()
