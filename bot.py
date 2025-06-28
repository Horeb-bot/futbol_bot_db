import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

TOKEN = os.getenv("TOKEN", "7577492603:AAGcYaB4sWZ8ALAzwsygpF7BWrx7LIHhoGg")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://futbol:sjMqGaEZeXvXsXTbYkD5F9hTMlz4Yd7o@dpg-d1frueali9vc739tje6g-a.frankfurt-postgres.render.com/futbol_bot_db")

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("Logros", callback_data='achievements')],
        [InlineKeyboardButton("Ayuda", callback_data='help')]
    ]
    await update.message.reply_text(
        "¡Hola, campeón! ⚽️ Bienvenido al bot de los partidos 1 a 1, ¿qué te gustaría hacer?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Comandos Disponibles:\n"
        "/start - Inicia el bot\n"
        "/register <nombre>\n"
        "/match <jugador1> <goles1> <jugador2> <goles2>\n"
        "/match_copa <jugador1> <goles1> <jugador2> <goles2>\n"
        "/consultar_historial_entre <j1> <j2>\n"
        "/historial\n"
        "/achievements"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'achievements':
        await achievements(update, context)
    elif query.data == 'help':
        await help_command(update, context)

async def register_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = ' '.join(context.args)
    if not name:
        await update.message.reply_text("⚠️ Usa: /register NombreJugador")
        return
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO players (name) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id', (name,))
    if cursor.fetchone():
        await update.message.reply_text(f"✅ Jugador {name} registrado.")
    else:
        await update.message.reply_text(f"ℹ️ El jugador {name} ya está registrado.")
    conn.commit()
    conn.close()

async def register_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 4:
        await update.message.reply_text("⚠️ Usa: /match jugador1 goles1 jugador2 goles2")
        return
    player1, score1, player2, score2 = context.args
    score1, score2 = int(score1), int(score2)
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM players WHERE name = %s', (player1,))
    p1 = cursor.fetchone()
    cursor.execute('SELECT id FROM players WHERE name = %s', (player2,))
    p2 = cursor.fetchone()
    if p1 and p2:
        cursor.execute('INSERT INTO matches (player1_id, player2_id, score1, score2) VALUES (%s, %s, %s, %s)', (p1[0], p2[0], score1, score2))
        update_statistics(player1, score1, player2, score2)
        await update.message.reply_text(f"✅ Partido registrado: {player1} {score1} - {player2} {score2}")
    else:
        await update.message.reply_text("Uno o ambos jugadores no están registrados.")
    conn.commit()
    conn.close()

async def register_match_copa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 4:
        await update.message.reply_text("⚠️ Usa: /match_copa jugador1 goles1 jugador2 goles2")
        return
    player1, score1, player2, score2 = context.args
    score1, score2 = int(score1), int(score2)
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM players WHERE name = %s', (player1,))
    p1 = cursor.fetchone()
    cursor.execute('SELECT id FROM players WHERE name = %s', (player2,))
    p2 = cursor.fetchone()
    if p1 and p2:
        cursor.execute('INSERT INTO matches (player1_id, player2_id, score1, score2) VALUES (%s, %s, %s, %s)', (p1[0], p2[0], score1, score2))
        update_statistics(player1, score1, player2, score2)
        if score1 > score2:
            cursor.execute('UPDATE statistics SET titles = titles + 1 WHERE player = %s', (player1,))
        elif score2 > score1:
            cursor.execute('UPDATE statistics SET titles = titles + 1 WHERE player = %s', (player2,))
        await update.message.reply_text(f"🏆 Partido por la copa registrado: {player1} {score1} - {player2} {score2}")
    else:
        await update.message.reply_text("Uno o ambos jugadores no están registrados.")
    conn.commit()
    conn.close()

async def consultar_historial_entre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("⚠️ Usa: /consultar_historial_entre jugador1 jugador2")
        return
    player1, player2 = context.args
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM players WHERE name = %s', (player1,))
    p1 = cursor.fetchone()
    cursor.execute('SELECT id FROM players WHERE name = %s', (player2,))
    p2 = cursor.fetchone()
    if not p1 or not p2:
        await update.message.reply_text("Jugador no encontrado.")
        return
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN player1_id=%s AND score1 > score2 THEN 1 WHEN player2_id=%s AND score2 > score1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN player1_id=%s AND score1 < score2 THEN 1 WHEN player2_id=%s AND score2 < score1 THEN 1 ELSE 0 END)
        FROM matches
        WHERE (player1_id=%s AND player2_id=%s) OR (player1_id=%s AND player2_id=%s)
    ''', (p1[0], p1[0], p1[0], p1[0], p1[0], p2[0], p2[0], p1[0]))
    result = cursor.fetchone()
    await update.message.reply_text(f"📊 {player1} ha ganado {result[0]} veces.\n{player2} ha ganado {result[1]} veces.")
    conn.close()

async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p1.name, p2.name, m.score1, m.score2 FROM matches m
        JOIN players p1 ON m.player1_id = p1.id
        JOIN players p2 ON m.player2_id = p2.id
        ORDER BY m.id DESC
    ''')
    rows = cursor.fetchall()
    if rows:
        msg = '📜 Historial de Partidos:\n'
        for r in rows:
            msg += f"{r[0]} {r[2]} - {r[1]} {r[3]}\n"
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("No hay partidos registrados aún.")
    conn.close()

async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('SELECT player, goals, wins, losses, titles FROM statistics ORDER BY titles DESC, wins DESC, goals DESC')
    rows = cursor.fetchall()
    if rows:
        msg = "🏆 Logros:\n"
        for p, g, w, l, t in rows:
            total = w + l
            winrate = (w / total) * 100 if total > 0 else 0
            msg += f"{p} - Goles: {g}, Victorias: {w}, Derrotas: {l}, Títulos: {t}, Winrate: {winrate:.2f}%\n"
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("No hay estadísticas registradas aún.")
    conn.close()

def update_statistics(p1, s1, p2, s2):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO statistics (player, goals, wins, losses)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (player) DO UPDATE SET
            goals = statistics.goals + EXCLUDED.goals,
            wins = statistics.wins + EXCLUDED.wins,
            losses = statistics.losses + EXCLUDED.losses
    ''', (p1, s1, int(s1 > s2), int(s1 < s2)))
    cursor.execute('''
        INSERT INTO statistics (player, goals, wins, losses)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (player) DO UPDATE SET
            goals = statistics.goals + EXCLUDED.goals,
            wins = statistics.wins + EXCLUDED.wins,
            losses = statistics.losses + EXCLUDED.losses
    ''', (p2, s2, int(s2 > s1), int(s2 < s1)))
    conn.commit()
    conn.close()

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("register", register_player))
    app.add_handler(CommandHandler("match", register_match))
    app.add_handler(CommandHandler("match_copa", register_match_copa))
    app.add_handler(CommandHandler("consultar_historial_entre", consultar_historial_entre))
    app.add_handler(CommandHandler("historial", historial))
    app.add_handler(CommandHandler("achievements", achievements))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    init_db()
    print("✅ psycopg2 importé avec succès !")
    main()
