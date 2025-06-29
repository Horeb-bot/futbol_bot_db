import os
import logging
import psycopg2
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

load_dotenv()
TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def connect_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Erreur connexion DB: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bienvenue dans le Bot Football 1v1 !")

async def nouveau_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Utilise /nouveau_match joueur1 joueur2 score")
        return
    joueur1, joueur2, score = args[0], args[1], args[2]
    conn = connect_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO matchs (joueur1, joueur2, score, date) VALUES (%s, %s, %s, NOW())",
                        (joueur1, joueur2, score))
            conn.commit()
            await update.message.reply_text("✅ Match enregistré.")
        except Exception as e:
            await update.message.reply_text("❌ Erreur lors de l'ajout du match.")
            logger.error(e)
        finally:
            cur.close()
            conn.close()

async def modifier_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Utilise /modifier_match id_nouveau_score")
        return
    match_id, score = args[0], args[1]
    conn = connect_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("UPDATE matchs SET score = %s WHERE id = %s", (score, match_id))
            conn.commit()
            await update.message.reply_text("🛠️ Score modifié.")
        except Exception as e:
            await update.message.reply_text("❌ Erreur modification.")
            logger.error(e)
        finally:
            cur.close()
            conn.close()

async def supprimer_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Utilise /supprimer_match id")
        return
    match_id = args[0]
    conn = connect_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM matchs WHERE id = %s", (match_id,))
            conn.commit()
            await update.message.reply_text("🗑️ Match supprimé.")
        except Exception as e:
            await update.message.reply_text("❌ Erreur suppression.")
            logger.error(e)
        finally:
            cur.close()
            conn.close()

async def historique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, joueur1, joueur2, score, date FROM matchs ORDER BY date DESC LIMIT 5")
            rows = cur.fetchall()
            if rows:
                msg = "\n".join([f"{r[0]}. {r[1]} vs {r[2]}: {r[3]} ({r[4].strftime('%d/%m %H:%M')})" for r in rows])
                await update.message.reply_text("📜 Derniers matchs :\n" + msg)
            else:
                await update.message.reply_text("Aucun match trouvé.")
        except Exception as e:
            logger.error(e)
            await update.message.reply_text("❌ Erreur historique.")
        finally:
            cur.close()
            conn.close()

async def parier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎲 Ton pari a été enregistré !")

async def statistiques(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Statistiques à venir...")

async def classement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT joueur1, COUNT(*) FROM matchs
                GROUP BY joueur1 ORDER BY COUNT(*) DESC
            """)
            rows = cur.fetchall()
            msg = "\n".join([f"{r[0]} - {r[1]} matchs" for r in rows])
            await update.message.reply_text("🏆 Classement :\n" + msg)
        except Exception as e:
            logger.error(e)
            await update.message.reply_text("❌ Erreur classement.")
        finally:
            cur.close()
            conn.close()

async def ajouter_joueur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Utilise /ajouter_joueur nom")
        return
    nom = context.args[0]
    conn = connect_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO joueurs (nom) VALUES (%s)", (nom,))
            conn.commit()
            await update.message.reply_text(f"✅ Joueur {nom} ajouté.")
        except Exception as e:
            logger.error(e)
            await update.message.reply_text("❌ Erreur ajout joueur.")
        finally:
            cur.close()
            conn.close()

async def joueurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT nom FROM joueurs ORDER BY nom ASC")
            rows = cur.fetchall()
            if rows:
                msg = "\n".join([r[0] for r in rows])
                await update.message.reply_text("👥 Joueurs :\n" + msg)
            else:
                await update.message.reply_text("Aucun joueur enregistré.")
        except Exception as e:
            logger.error(e)
            await update.message.reply_text("❌ Erreur liste joueurs.")
        finally:
            cur.close()
            conn.close()

async def inconnu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Commande inconnue. Utilise /start pour commencer.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nouveau_match", nouveau_match))
    app.add_handler(CommandHandler("modifier_match", modifier_match))
    app.add_handler(CommandHandler("supprimer_match", supprimer_match))
    app.add_handler(CommandHandler("historique", historique))
    app.add_handler(CommandHandler("parier", parier))
    app.add_handler(CommandHandler("statistiques", statistiques))
    app.add_handler(CommandHandler("classement", classement))
    app.add_handler(CommandHandler("ajouter_joueur", ajouter_joueur))
    app.add_handler(CommandHandler("joueurs", joueurs))
    app.add_handler(MessageHandler(filters.COMMAND, inconnu))

    logger.info("✅ Bot démarré avec succès.")
    app.run_polling()

if __name__ == '__main__':
    main()
