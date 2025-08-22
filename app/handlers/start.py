
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from app.keyboards import main_menu

WELCOME = (
    "Ciao! Sono il tuo *Libretto di manutenzione digitale* 🧰\n\n"
    "Posso aiutarti a gestire più veicoli, registrare interventi, impostare promemoria e "
    "esportare tutto in CSV/Excel. Usa il menu qui sotto oppure i comandi /help."
)

HELP = (
    "Comandi utili:\n"
    "/start - menu principale\n"
    "/vehicles - gestisci veicoli\n"
    "/add_vehicle - aggiungi veicolo\n"
    "/update_km - aggiorna chilometraggio\n"
    "/add_maintenance - aggiungi intervento\n"
    "/history - storico interventi\n"
    "/set_time_reminder - promemoria a data/ora\n"
    "/set_km_reminder - promemoria al raggiungimento km\n"
    "/export - esporta dati in CSV/XLSX"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, reply_markup=main_menu(), parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP)

def get_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("help", help_cmd),
        MessageHandler(filters.Regex("^ℹ️ Aiuto$"), help_cmd),
    ]
