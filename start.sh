#!/bin/bash

echo "Lancement du bot Telegram..."

# Installer les dépendances à partir de requirements.txt
pip install -r requirements.txt

# Lancer le bot
python bot.py
