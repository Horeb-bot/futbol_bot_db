#!/bin/bash

echo "🔁 Suppression de python-telegram-bot..."
pip uninstall -y python-telegram-bot

echo "📦 Réinstallation propre de python-telegram-bot 20.8..."
pip install python-telegram-bot==20.8 psycopg2-binary python-dotenv

echo "🚀 Lancement du bot Telegram..."
python bot.py
