import os
import psycopg2
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, CallbackContext
)

# Charger les variables d’environnement locales si en local
load_dotenv()

# Obtenir les secrets depuis les variables d’environnement
TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Créer la base de données et les tables
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            player1_id INTEGER REFERENCES players(id),
            player2_id INTEGER REFERENCES players(id),
            score1 INTEGER,
            score2 INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            player TEXT PRIMARY KEY,
            goals INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            titles INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("Logros", callback_data='achievements')],
        [InlineKeyboardButton("Ayuda", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        '¡Hola, campeón! ⚽️ Bienvenido al bot de los partidos 1 a 1, ¿qué te gustaría hacer ?',
        reply_markup=reply_markup
    )

# Gestion des boutons
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    if data == 'register':
        await query.message.reply_text('Usa: /register NombreJugador')
    elif data == 'achievements':
        await achievements(update, context)
    elif data == 'help':
        await help_command(update, context)

# Enregistrement de joueur
async def register_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = ' '.join(context.args)
    if not name:
        await update.message.reply_text('⚠️ Formato: /register NombreJugador')
        return

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        cursor.execute(
            'INSERT INTO players (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id',
            (name,)
        )
        player_id = cursor.fetchone()
        conn.commit()

        if player_id:
            await update.message.reply_text(f'Jugador {name} registrado ✅')
        else:
            await update.message.reply_text(f'Jugador {name} ya registrado.')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')
    finally:
        conn.close()

# Enregistrement d’un match simple
async def register_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 4:
            await update.message.reply_text('⚠️ Formato: /match jugador1 goles1 jugador2 goles2')
            return

        p1, g1, p2, g2 = context.args
        g1, g2 = int(g1), int(g2)

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM players WHERE name = %s', (p1,))
        id1 = cursor.fetchone()
        cursor.execute('SELECT id FROM players WHERE name = %s', (p2,))
        id2 = cursor.fetchone()

        if id1 and id2:
            cursor.execute(
                'INSERT INTO matches (player1_id, player2_id, score1, score2) VALUES (%s, %s, %s, %s)',
                (id1[0], id2[0], g1, g2)
            )
            conn.commit()
            update_statistics(p1, g1, p2, g2)
            await update.message.reply_text(f'✅ Partido registrado: {p1} {g1} - {p2} {g2}')
        else:
            await update.message.reply_text('Uno o ambos jugadores no registrados.')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')
    finally:
        conn.close()

# Enregistrement match de copa avec titre
async def register_match_copa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 4:
            await update.message.reply_text('⚠️ Formato: /match_copa jugador1 goles1 jugador2 goles2')
            return

        p1, g1, p2, g2 = context.args
        g1, g2 = int(g1), int(g2)

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM players WHERE name = %s', (p1,))
        id1 = cursor.fetchone()
        cursor.execute('SELECT id FROM players WHERE name = %s', (p2,))
        id2 = cursor.fetchone()

        if id1 and id2:
            cursor.execute(
                'INSERT INTO matches (player1_id, player2_id, score1, score2) VALUES (%s, %s, %s, %s)',
                (id1[0], id2[0], g1, g2)
            )
            if g1 > g2:
                cursor.execute('UPDATE statistics SET titles = titles + 1 WHERE player = %s', (p1,))
            elif g2 > g1:
                cursor.execute('UPDATE statistics SET titles = titles + 1 WHERE player = %s', (p2,))
            conn.commit()
            update_statistics(p1, g1, p2, g2)
            await update.message.reply_text(f'🏆 Partido de copa registrado: {p1} {g1} - {p2} {g2}')
        else:
            await update.message.reply_text('Uno o ambos jugadores no registrados.')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')
    finally:
        conn.close()

# Mettre à jour les stats
def update_statistics(p1, g1, p2, g2):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Joueur 1
    cursor.execute('''
        INSERT INTO statistics (player, goals, wins, losses)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (player)
        DO UPDATE SET
            goals = statistics.goals + %s,
            wins = statistics.wins + CASE WHEN %s > %s THEN 1 ELSE 0 END,
            losses = statistics.losses + CASE WHEN %s < %s THEN 1 ELSE 0 END
    ''', (p1, g1, g1 > g2, g1 < g2, g1, g1, g2, g1, g2))

    # Joueur 2
    cursor.execute('''
        INSERT INTO statistics (player, goals, wins, losses)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (player)
        DO UPDATE SET
            goals = statistics.goals + %s,
            wins = statistics.wins + CASE WHEN %s > %s THEN 1 ELSE 0 END,
            losses = statistics.losses + CASE WHEN %s < %s THEN 1 ELSE 0 END
    ''', (p2, g2, g2 > g1, g2 < g1, g2, g2, g1, g2, g1))

    conn.commit()
    conn.close()

# Historique complet
async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT p1.name, p2.name, m.score1, m.score2
            FROM matches m
            JOIN players p1 ON m.player1_id = p1.id
            JOIN players p2 ON m.player2_id = p2.id
            ORDER BY m.id DESC
        ''')
        rows = cursor.fetchall()
        if rows:
            msg = "📜 Historial de Partidos:\n"
            for p1, p2, g1, g2 in rows:
                msg += f'{p1} {g1} - {g2} {p2}\n'
        else:
            msg = "Aún no hay partidos registrados."
        await update.message.reply_text(msg)
    finally:
        conn.close()

# Historique entre 2 joueurs
async def consultar_historial_entre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("⚠️ Formato: /consultar_historial_entre jugador1 jugador2")
        return

    p1, p2 = context.args
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT id FROM players WHERE name = %s', (p1,))
        id1 = cursor.fetchone()
        cursor.execute('SELECT id FROM players WHERE name = %s', (p2,))
        id2 = cursor.fetchone()

        if not id1 or not id2:
            await update.message.reply_text("Uno o ambos jugadores no están registrados.")
            return

        id1, id2 = id1[0], id2[0]
        cursor.execute('''
            SELECT
                SUM(CASE WHEN player1_id = %s AND score1 > score2 THEN 1
                         WHEN player2_id = %s AND score2 > score1 THEN 1 ELSE 0 END) as p1_wins,
                SUM(CASE WHEN player1_id = %s AND score1 < score2 THEN 1
                         WHEN player2_id = %s AND score2 < score1 THEN 1 ELSE 0 END) as p2_wins
            FROM matches
            WHERE (player1_id = %s AND player2_id = %s) OR (player1_id = %s AND player2_id = %s)
        ''', (id1, id1, id2, id2, id1, id2, id2, id1))
        p1_wins, p2_wins = cursor.fetchone()
        await update.message.reply_text(
            f"📊 Enfrentamientos entre {p1} y {p2}:\n"
            f"{p1} ganó {p1_wins} veces.\n"
            f"{p2} ganó {p2_wins} veces."
        )
    finally:
        conn.close()

# Statistiques
async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('SELECT player, goals, wins, losses, titles FROM statistics ORDER BY titles DESC, wins DESC')
    stats = cursor.fetchall()
    msg = "🏅 Logros de los jugadores:\n"
    for p, g, w, l, t in stats:
        total = w + l
        winrate = (w / total * 100) if total > 0 else 0
        msg += f"{p} - Goles: {g}, Victorias: {w}, Derrotas: {l}, Winrate: {winrate:.1f}%, Títulos: {t}\n"
    await update.message.reply_text(msg)
    conn.close()

# Commande /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Comandos disponibles:\n"
        "/start - Menú principal\n"
        "/register NombreJugador\n"
        "/match jugador1 goles1 jugador2 goles2\n"
        "/match_copa jugador1 goles1 jugador2 goles2\n"
        "/consultar_historial_entre jugador1 jugador2\n"
        "/historial - Todos los partidos\n"
        "/achievements - Estadísticas y títulos"
    )

# Lancement principal
def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register_player))
    app.add_handler(CommandHandler("match", register_match))
    app.add_handler(CommandHandler("match_copa", register_match_copa))
    app.add_handler(CommandHandler("historial", historial))
    app.add_handler(CommandHandler("consultar_historial_entre", consultar_historial_entre))
    app.add_handler(CommandHandler("achievements", achievements))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Bot lanzado correctamente...")
    app.run_polling()

if __name__ == "__main__":
    main()
