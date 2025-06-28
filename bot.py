import logging
import psycopg2
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)

load_dotenv()

TOKEN = os.getenv("TOKEN")
DB_URL = os.getenv("DATABASE_URL")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Connexion PostgreSQL
def connect_db():
    return psycopg2.connect(DB_URL, sslmode='require')

# Commande /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "👋 Bienvenue sur le Bot Futbol 1v1 !\n\n"
        "Commandes disponibles :\n"
        "/nouveau_match @adversaire score1 score2\n"
        "/historique\n"
        "/parier @joueur montant\n"
        "/statistiques"
    )

# Commande /nouveau_match
async def nouveau_match(update: Update, context: CallbackContext):
    if len(context.args) != 3:
        await update.message.reply_text("Utilisation : /nouveau_match @adversaire score1 score2")
        return

    try:
        adversaire = context.args[0].lstrip('@')
        score1 = int(context.args[1])
        score2 = int(context.args[2])
        joueur1 = update.effective_user.username

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO matchs (joueur1, joueur2, score1, score2)
                    VALUES (%s, %s, %s, %s)
                """, (joueur1, adversaire, score1, score2))
                conn.commit()
        await update.message.reply_text("✅ Match enregistré avec succès.")
    except Exception as e:
        logger.error(f"Erreur enregistrement match : {e}")
        await update.message.reply_text("❌ Une erreur s'est produite.")

# Commande /historique
async def historique(update: Update, context: CallbackContext):
    joueur = update.effective_user.username
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT joueur2, score1, score2, date FROM matchs
                    WHERE joueur1 = %s OR joueur2 = %s
                    ORDER BY date DESC LIMIT 10
                """, (joueur, joueur))
                matchs = cur.fetchall()

        if not matchs:
            await update.message.reply_text("Aucun match trouvé.")
            return

        texte = "📜 Historique de vos derniers matchs :\n"
        for m in matchs:
            texte += f"🆚 @{m[0]} — {m[1]}:{m[2]} ({m[3].strftime('%d/%m/%Y')})\n"

        await update.message.reply_text(texte)
    except Exception as e:
        logger.error(f"Erreur historique : {e}")
        await update.message.reply_text("Erreur lors de la récupération de l'historique.")

# Commande /parier
async def parier(update: Update, context: CallbackContext):
    if len(context.args) != 2:
        await update.message.reply_text("Utilisation : /parier @joueur montant")
        return

    try:
        joueur_parié = context.args[0].lstrip('@')
        montant = int(context.args[1])
        parieur = update.effective_user.username

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO paris (parieur, joueur_parié, montant)
                    VALUES (%s, %s, %s)
                """, (parieur, joueur_parié, montant))
                conn.commit()
        await update.message.reply_text("💸 Pari enregistré.")
    except Exception as e:
        logger.error(f"Erreur pari : {e}")
        await update.message.reply_text("Erreur lors de l'enregistrement du pari.")

# Commande /statistiques
async def statistiques(update: Update, context: CallbackContext):
    joueur = update.effective_user.username
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*),
                        SUM(CASE WHEN (joueur1 = %s AND score1 > score2) OR (joueur2 = %s AND score2 > score1) THEN 1 ELSE 0 END),
                        SUM(CASE WHEN (joueur1 = %s AND score1 < score2) OR (joueur2 = %s AND score2 < score1) THEN 1 ELSE 0 END)
                    FROM matchs
                    WHERE joueur1 = %s OR joueur2 = %s
                """, (joueur, joueur, joueur, joueur, joueur, joueur))
                total, victoires, defaites = cur.fetchone()

        await update.message.reply_text(
            f"📊 Statistiques @{joueur} :\n"
            f"• Matchs joués : {total}\n"
            f"• Victoires : {victoires}\n"
            f"• Défaites : {defaites}"
        )
    except Exception as e:
        logger.error(f"Erreur stats : {e}")
        await update.message.reply_text("Erreur lors de la récupération des statistiques.")

# Gestion des messages inconnus
async def inconnu(update: Update, context: CallbackContext):
    await update.message.reply_text("Commande non reconnue. Tape /start pour voir les options.")

# Fonction principale
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nouveau_match", nouveau_match))
    app.add_handler(CommandHandler("historique", historique))
    app.add_handler(CommandHandler("parier", parier))
    app.add_handler(CommandHandler("statistiques", statistiques))
    app.add_handler(MessageHandler(filters.COMMAND, inconnu))

    print("✅ Bot démarré...")
    app.run_polling()

if __name__ == "__main__":
    main()
