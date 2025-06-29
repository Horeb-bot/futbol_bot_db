import os
import logging
import psycopg2
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

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
    # Exemple d’insertion dans la base (adapter selon ta table)
    conn = connect_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO matchs (joueur1, joueur2, score, date) VALUES (%s, %s, %s, NOW())",
                        ("Joueur A", "Joueur B", "0-0"))
            conn.commit()
            await update.message.reply_text("Match ajouté avec succès.")
        except Exception as e:
            logger.error(f"Erreur insertion: {e}")
            await update.message.reply_text("Erreur lors de la création du match.")
        finally:
            cur.close()
            conn.close()

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
            message = "\n".join([f"{r[1]} vs {r[2]} - {r[3]}" for r in rows])
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

# Commande inconnue
async def inconnu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Commande inconnue. Tape /start pour commencer.")

# Fonction principale
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nouveau_match", nouveau_match))
    app.add_handler(CommandHandler("historique", historique))
    app.add_handler(CommandHandler("parier", parier))
    app.add_handler(CommandHandler("statistiques", statistiques))
    app.add_handler(MessageHandler(filters.COMMAND, inconnu))

    logger.info("✅ Bot démarré avec succès.")
    app.run_polling()

if __name__ == '__main__':
    main()
