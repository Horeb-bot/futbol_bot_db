import os
import psycopg2
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, CallbackContext

load_dotenv()

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

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
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("¡Hola, campeón! ⚽️ Bienvenido al bot de los partidos 1 a 1, ¿qué te gustaría hacer?", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 Comandos disponibles:\n"
        "/start - Iniciar el bot\n"
        "/register <nombre> - Registrar jugador\n"
        "/match <jug1> <goles1> <jug2> <goles2>\n"
        "/match_copa <jug1> <goles1> <jug2> <goles2>\n"
        "/match_apuesta <jug1> <goles1> <jug2> <goles2> <monto> <alias>\n"
        "/consultar_historial_entre <jug1> <jug2>\n"
        "/historial - Ver historial global\n"
        "/achievements - Ver logros"
    )

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    if data == 'achievements':
        await achievements(update, context)
    elif data == 'help':
        await help_command(update, context)

async def register_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = ' '.join(context.args)
    if not name:
        await update.message.reply_text("⚠️ Usa: /register NombreJugador")
        return
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("INSERT INTO players (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id", (name,))
    added = cur.fetchone()
    conn.commit()
    conn.close()
    if added:
        await update.message.reply_text(f"{name} registrado.")
    else:
        await update.message.reply_text(f"{name} ya estaba registrado.")

async def register_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 4:
        await update.message.reply_text("Usa: /match jugador1 goles1 jugador2 goles2")
        return
    p1, s1, p2, s2 = context.args
    s1, s2 = int(s1), int(s2)
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT id FROM players WHERE name = %s", (p1,))
    p1_id = cur.fetchone()
    cur.execute("SELECT id FROM players WHERE name = %s", (p2,))
    p2_id = cur.fetchone()
    if not p1_id or not p2_id:
        await update.message.reply_text("Jugadores no registrados.")
        return
    cur.execute("INSERT INTO matches (player1_id, player2_id, score1, score2) VALUES (%s, %s, %s, %s)", (p1_id[0], p2_id[0], s1, s2))
    conn.commit()
    conn.close()
    update_statistics(p1, s1, p2, s2)
    await update.message.reply_text(f"{p1} {s1} - {p2} {s2} registrado.")

async def register_match_copa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 4:
        await update.message.reply_text("Usa: /match_copa jugador1 goles1 jugador2 goles2")
        return
    p1, s1, p2, s2 = context.args
    s1, s2 = int(s1), int(s2)
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT id FROM players WHERE name = %s", (p1,))
    p1_id = cur.fetchone()
    cur.execute("SELECT id FROM players WHERE name = %s", (p2,))
    p2_id = cur.fetchone()
    if not p1_id or not p2_id:
        await update.message.reply_text("Jugadores no registrados.")
        return
    cur.execute("INSERT INTO matches (player1_id, player2_id, score1, score2) VALUES (%s, %s, %s, %s)", (p1_id[0], p2_id[0], s1, s2))
    if s1 > s2:
        cur.execute("UPDATE statistics SET titles = titles + 1 WHERE player = %s", (p1,))
    elif s2 > s1:
        cur.execute("UPDATE statistics SET titles = titles + 1 WHERE player = %s", (p2,))
    conn.commit()
    conn.close()
    update_statistics(p1, s1, p2, s2)
    await update.message.reply_text(f"🏆 Partido de copa: {p1} {s1} - {p2} {s2} registrado.")

async def register_match_apuesta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 6:
        await update.message.reply_text("Usa: /match_apuesta jugador1 goles1 jugador2 goles2 monto alias")
        return
    p1, s1, p2, s2, monto, alias = context.args
    s1, s2 = int(s1), int(s2)
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT id FROM players WHERE name = %s", (p1,))
    p1_id = cur.fetchone()
    cur.execute("SELECT id FROM players WHERE name = %s", (p2,))
    p2_id = cur.fetchone()
    if not p1_id or not p2_id:
        await update.message.reply_text("Jugadores no registrados.")
        return
    cur.execute("INSERT INTO matches (player1_id, player2_id, score1, score2) VALUES (%s, %s, %s, %s)", (p1_id[0], p2_id[0], s1, s2))
    conn.commit()
    conn.close()
    update_statistics(p1, s1, p2, s2)
    link = f"https://www.mercadopago.com.ar?alias={alias}&monto={monto}"
    await update.message.reply_text(f"💰 Partido apuesta registrado: {p1} {s1} - {p2} {s2}\n🔗 Link: {link}")

async def consultar_historial_entre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usa: /consultar_historial_entre jugador1 jugador2")
        return
    p1, p2 = context.args
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT id FROM players WHERE name = %s", (p1,))
    id1 = cur.fetchone()
    cur.execute("SELECT id FROM players WHERE name = %s", (p2,))
    id2 = cur.fetchone()
    if not id1 or not id2:
        await update.message.reply_text("Jugadores no registrados.")
        return
    cur.execute("""
        SELECT score1, score2 FROM matches
        WHERE (player1_id = %s AND player2_id = %s)
           OR (player1_id = %s AND player2_id = %s)
    """, (id1[0], id2[0], id2[0], id1[0]))
    results = cur.fetchall()
    conn.close()
    wins1, wins2 = 0, 0
    for s1, s2 in results:
        if s1 > s2:
            wins1 += 1
        elif s2 > s1:
            wins2 += 1
    await update.message.reply_text(f"📊 {p1} ganó {wins1} veces\n📊 {p2} ganó {wins2} veces")

async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT p1.name, p2.name, m.score1, m.score2 FROM matches m
        JOIN players p1 ON m.player1_id = p1.id
        JOIN players p2 ON m.player2_id = p2.id
        ORDER BY m.id DESC LIMIT 10
    """)
    matches = cur.fetchall()
    conn.close()
    msg = "📜 Últimos partidos:\n"
    for a, b, s1, s2 in matches:
        msg += f"{a} {s1} - {b} {s2}\n"
    await update.message.reply_text(msg)

async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT player, goals, wins, losses, titles FROM statistics ORDER BY titles DESC, wins DESC")
    stats = cur.fetchall()
    conn.close()
    msg = "🏆 Logros:\n"
    for p, g, w, l, t in stats:
        total = w + l
        rate = (w / total * 100) if total else 0
        msg += f"{p} - Goles: {g}, Wins: {w}, Losses: {l}, Títulos: {t}, Winrate: {rate:.2f}%\n"
    await update.message.reply_text(msg)

def update_statistics(p1, s1, p2, s2):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO statistics (player, goals, wins, losses)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (player) DO UPDATE SET
            goals = statistics.goals + %s,
            wins = statistics.wins + CASE WHEN %s > %s THEN 1 ELSE 0 END,
            losses = statistics.losses + CASE WHEN %s < %s THEN 1 ELSE 0 END
    """, (p1, s1, int(s1 > s2), int(s1 < s2), s1, s1, s2, s1, s2))
    cur.execute("""
        INSERT INTO statistics (player, goals, wins, losses)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (player) DO UPDATE SET
            goals = statistics.goals + %s,
            wins = statistics.wins + CASE WHEN %s > %s THEN 1 ELSE 0 END,
            losses = statistics.losses + CASE WHEN %s < %s THEN 1 ELSE 0 END
    """, (p2, s2, int(s2 > s1), int(s2 < s1), s2, s2, s1, s2, s1))
    conn.commit()
    conn.close()

def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("register", register_player))
    app.add_handler(CommandHandler("match", register_match))
    app.add_handler(CommandHandler("match_copa", register_match_copa))
    app.add_handler(CommandHandler("match_apuesta", register_match_apuesta))
    app.add_handler(CommandHandler("consultar_historial_entre", consultar_historial_entre))
    app.add_handler(CommandHandler("historial", historial))
    app.add_handler(CommandHandler("achievements", achievements))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == '__main__':
    main()
