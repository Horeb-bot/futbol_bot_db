#!/bin/bash

echo "📦 Installation des dépendances..."

# 🔁 On désinstalle python-telegram-bot pour éviter les conflits de version
pip uninstall -y python-telegram-bot

# ✅ On installe la version correcte
pip install python-telegram-bot==20.8

# 🔁 Facultatif : (ré)installation des autres dépendances si besoin
pip install -r requirements.txt

echo "🚀 Lancement du bot Telegram..."
python bot.py
