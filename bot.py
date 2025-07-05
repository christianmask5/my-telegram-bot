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
                config = json.load(f)
                # Conversion pour compatibilité avec ancienne version
                if isinstance(config.get("channel"), dict):
                    return config
                return {"channel": None, "welcome_text": "", "welcome_pic": ""}
    except Exception as e:
        logger.error(f"Erreur chargement config: {e}")
    return {"channel": None, "welcome_text": "", "welcome_pic": ""}

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
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Désolé, vous n'êtes pas autorisé.")
        return

    bot_info = await context.bot.get_me()
    bot_name = bot_info.first_name

    commands = [
        "/channelinfo - Voir la configuration actuelle",
        "/addchannel <id> - Ajouter un canal",
        "/removechannel - Supprimer le canal configuré",
        "/setwelcometext - Définir le message de bienvenue",
        "/setwelcomepic - Définir la photo de bienvenue"
    ]

    welcome_msg = (
        f"Bienvenue sur 🤖 *{bot_name}* !\n\n"
        "📚 *Commandes disponibles :*\n"
        + "\n".join(commands) + "\n\n"
        "⚙️ *Ajoute-moi comme administrateur de ton canal pour commencer !*\n\n"
        #f"👨🏾‍💻 *DEV :* @christian\\{chr(95)}mask5\n\n"
    )

    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def channelinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Vous n'êtes pas autorisé.")
        return
        
    if not bot_config["channel"]:
        await update.message.reply_text("Aucun canal n'est configuré pour le moment.")
        return
        
    channel = bot_config["channel"]
    message = (
        f"📌 *Canal configuré* :\n\n"
        f"• *Nom* : {channel.get('title', 'Inconnu')}\n\n"
        f"      • *ID* : `{channel['id']}`\n\n"
        f"      • *Message* : {'✅' if bot_config['welcome_text'] else '❌'}\n"
        f"      • *Photo* : {'✅' if bot_config.get('welcome_pic') else '❌'}"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Vous n'êtes pas autorisé.")
        return
    
    if bot_config["channel"]:
        await update.message.reply_text("❌ Un canal est déjà configuré. Utilisez /removechannel pour le supprimer avant d'en ajouter un nouveau.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addchannel <channel_id>")
        return

    channel_id = context.args[0]
    try:
        chat = await context.bot.get_chat(channel_id)
        bot_member = await chat.get_member(context.bot.id)
        
        if bot_member.status not in ["administrator", "creator"]:
            await update.message.reply_text("❌ Je ne suis pas admin de ce canal.")
            return

        bot_config["channel"] = {
            "id": channel_id,
            "title": chat.title,
            "username": chat.username,
            "added_at": datetime.now().isoformat()
        }
        save_config(bot_config)
        await update.message.reply_text(
            f"✅ *Canal configuré avec succès !*\n\n"
            f"*Nom* : {chat.title}\n"
            f"*ID* : `{channel_id}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Erreur add_channel: {e}")
        await update.message.reply_text(f"❌ Erreur: {e}")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Vous n'êtes pas autorisé.")
        return
    
    if not bot_config["channel"]:
        await update.message.reply_text("ℹ️ Aucun canal n'a été configuré.")
        return
        
    bot_config.update({
        "channel": None,
        "welcome_text": "",
        "welcome_pic": ""
    })
    save_config(bot_config)
    await update.message.reply_text("✅ Canal supprimé avec succès.")

async def set_welcome_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Vous n'êtes pas autorisé.")
        return
        
    if not bot_config["channel"]:
        await update.message.reply_text("❌ Aucun canal configuré. Ajoutez-en un d'abord.")
        return

    context.user_data["setting_welcome_text"] = True
    await update.message.reply_text(
        "📝 Envoyez maintenant le message de bienvenue :\n\n"
        "Vous pouvez utiliser :\n"
        "`{user}` - Insérer le nom du nouvel abonné\n"
        "`{channel}` - Insérer le nom du canal",
        parse_mode="Markdown"
    )

async def set_welcome_pic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Vous n'êtes pas autorisé.")
        return
        
    if not bot_config["channel"]:
        await update.message.reply_text("❌ Aucun canal configuré. Ajoutez-en un d'abord.")
        return

    context.user_data["setting_welcome_pic"] = True
    await update.message.reply_text("📸 Envoyez maintenant la photo de bienvenue :")

# ===============================
# HANDLERS POUR LES DONNÉES
# ===============================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
        
    if "setting_welcome_text" in context.user_data:
        bot_config["welcome_text"] = update.message.text
        save_config(bot_config)
        await update.message.reply_text("✅ Message de bienvenue enregistré !")
        context.user_data.pop("setting_welcome_text", None)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
        
    if "setting_welcome_pic" in context.user_data:
        bot_config["welcome_pic"] = update.message.photo[-1].file_id
        save_config(bot_config)
        await update.message.reply_text("✅ Photo de bienvenue enregistrée !")
        context.user_data.pop("setting_welcome_pic", None)

# ===============================
# CHAT JOIN REQUEST HANDLER
# ===============================
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_config["channel"]:
        return
        
    channel_id = str(update.chat_join_request.chat.id)
    if channel_id != bot_config["channel"]["id"]:
        return

    user = update.chat_join_request.from_user
    logger.info(f"Nouvelle demande de {user.full_name}")
    
    try:
        # 1. Approuver la demande
        await context.bot.approve_chat_join_request(
            chat_id=update.chat_join_request.chat.id,
            user_id=user.id
        )
        
        # 2. Envoyer le message de bienvenue
        if bot_config["welcome_text"]:
            welcome_text = bot_config["welcome_text"].replace(
                "{user}", user.full_name
            ).replace(
                "{channel}", bot_config["channel"]["title"]
            )
            
            if bot_config.get("welcome_pic"):
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=bot_config["welcome_pic"],
                    caption=welcome_text
                )
            else:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=welcome_text
                )
                
    except Exception as e:
        logger.error(f"Erreur traitement demande: {e}")

# ===============================
# MAIN
# ===============================
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commandes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("channelinfo", channelinfo))
    app.add_handler(CommandHandler("addchannel", add_channel))
    app.add_handler(CommandHandler("removechannel", remove_channel))
    app.add_handler(CommandHandler("setwelcometext", set_welcome_text))
    app.add_handler(CommandHandler("setwelcomepic", set_welcome_pic))

    # Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))

    logger.info("Bot démarré...")
    app.run_polling()