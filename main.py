import os
import requests
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

SHEETDB_URL = "https://sheetdb.io/api/v1/17cwkibodi8t9"  # ← Sostituisci con il tuo link
TOKEN = os.getenv("BOT_TOKEN")

risposte = {}
admin_ids = {5560352330, 1234567890}  # ← Inserisci qui i tuoi ID Telegram autorizzati

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    volontario_id = user.id
    nome = user.full_name

    data = {
        "data": {
            "id": str(volontario_id),
            "nome": nome
        }
    }

    try:
        response = requests.post(SHEETDB_URL, json=data)
        if response.status_code in [200, 201]:
            await update.message.reply_text("✅ Registrazione completata. Ora riceverai le allerte.")
            print(f"Registrato: {nome} - ID: {volontario_id}")
        else:
            await update.message.reply_text("⚠️ Errore durante la registrazione.")
            print(f"Errore registrazione: {response.text}")
    except Exception as e:
        print(f"Errore SheetDB: {e}")
        await update.message.reply_text("⚠️ Errore di connessione.")

async def allerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admin_ids:
        await update.message.reply_text("⛔ Non hai i permessi per inviare l’allerta.")
        return

    try:
        response = requests.get(SHEETDB_URL)
        json_data = response.json()
        ids = [int(entry["id"]) for entry in json_data if "id" in entry]

        global risposte
        risposte = {v: None for v in ids}

        keyboard = [[
            InlineKeyboardButton("✅ Confermo", callback_data='confermo'),
            InlineKeyboardButton("❌ Rifiuto", callback_data='rifiuto')
        ]]
        markup = InlineKeyboardMarkup(keyboard)

        for vid in ids:
            await context.bot.send_message(chat_id=vid, text="🚨 CHIAMATA URGENTE 🚨", reply_markup=markup)
            asyncio.create_task(notifica_ripetuta(context, vid, markup))

    except Exception as e:
        print(f"Errore durante allerta: {e}")
        await update.message.reply_text("⚠️ Errore durante l’invio dell’allerta.")

async def notifica_ripetuta(context, user_id, markup):
    for _ in range(6):  # 6 notifiche ogni 10s = 1 minuto
        await asyncio.sleep(10)
        if risposte.get(user_id) is None:
            try:
                await context.bot.send_message(chat_id=user_id, text="🔔 RISPOSTA URGENTE RICHIESTA!", reply_markup=markup)
            except Exception as e:
                print(f"Errore notifica ripetuta a {user_id}: {e}")
        else:
            break

async def risposta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    risposte[query.from_user.id] = query.data
    await query.edit_message_text(f"Hai risposto: {query.data}")

async def mostra_risposte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admin_ids:
        await update.message.reply_text("⛔ Non hai i permessi per vedere le risposte.")
        return

    if not risposte:
        await update.message.reply_text("ℹ️ Nessuna allerta attiva.")
        return

    testo = "📋 Risposte:\n"
    for uid, stato in risposte.items():
        nome = f"user_{uid}"
        risposta = stato if stato else "⏳ Nessuna risposta"
        testo += f"- {nome}: {risposta}\n"

    await update.message.reply_text(testo)

# Costruzione e avvio dell'app
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("allerta", allerta))
app.add_handler(CommandHandler("risposte", mostra_risposte))
app.add_handler(CallbackQueryHandler(risposta))
app.run_polling()
