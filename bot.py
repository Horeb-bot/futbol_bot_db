import os
import logging
import psycopg2
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

# --- Lignes de diagnostic temporaires ---
import telegram.ext # Import déjà existant, mais s'assurer qu'il est là
import sys
# --- Fin des lignes de diagnostic temporaires ---


# Chargement des variables d'environnement
load_dotenv()
TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Connexion à la base de données
def connect_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Erreur de connexion à la base de données: {e}")
        return None

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bienvenue dans le bot 1v1 Football !")

# Commande /nouveau_match
async def nouveau_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Création d'un nouveau match...")
    # Ici, tu pourrais insérer dans la DB un nouveau match

# Commande /historique
async def historique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect_db()
    if not conn:
        await update.message.reply_text("Erreur de connexion à la base de données.")
        return
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM matchs ORDER BY date DESC LIMIT 5")
        rows = cur.fetchall()
        if not rows:
            await update.message.reply_text("Aucun match trouvé.")
        else:
            message = "\n".join([str(row) for row in rows])
            await update.message.reply_text(f"Derniers matchs :\n{message}")
    except Exception as e:
        logger.error(f"Erreur de requête : {e}")
        await update.message.reply_text("Erreur lors de la récupération de l'historique.")
    finally:
        cur.close()
        conn.close()

# Commande /parier
async def parier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pari enregistré !")

# Commande /statistiques
async def statistiques(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Statistiques des joueurs à venir...")

# Réponse aux commandes inconnues
async def inconnu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Commande inconnue. Tape /start pour commencer.")

# Fonction principale
def main():
    # --- Lignes de diagnostic temporaires ---
    # Ces lignes t'aideront à vérifier quelle version de python-telegram-bot est réellement chargée
    # et où elle se trouve dans l'environnement d'exécution de Render.
    try:
        logger.info(f"DEBUG: python-telegram-bot version loaded: {telegram.ext.__version__}")
        logger.info(f"DEBUG: Path to telegram.ext: {os.path.dirname(telegram.ext.__file__)}")
        logger.info(f"DEBUG: sys.path: {sys.path}")
    except Exception as e:
        logger.error(f"DEBUG: Erreur lors de la récupération des infos telegram.ext: {e}")
    # --- Fin des lignes de diagnostic temporaires ---

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nouveau_match", nouveau_match))
    app.add_handler(CommandHandler("historique", historique))
    app.add_handler(CommandHandler("parier", parier))
    app.add_handler(CommandHandler("statistiques", statistiques))
    app.add_handler(MessageHandler(filters.COMMAND, inconnu))

    logger.info("Bot démarré avec succès...")
    app.run_polling()

if __name__ == '__main__':
    main()
