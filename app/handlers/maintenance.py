
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler,
                          ConversationHandler, filters)
from app import storage
from app.utils.formatting import parse_date
from datetime import date

ASK_VEH, ASK_TYPE, ASK_DATE, ASK_KM, ASK_NOTES, ASK_COST = range(6)

COMMON_TYPES = ["Tagliando", "Cambio olio", "Filtro aria", "Filtro abitacolo", "Pneumatici", "Freni", "Batteria", "Altro"]

async def add_maintenance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    vehicles = storage.list_vehicles(context.bot_data["db_path"], chat_id)
    if not vehicles:
        await update.message.reply_text("Prima aggiungi un veicolo con /add_vehicle.")
        return ConversationHandler.END
    buttons = [[InlineKeyboardButton((v["alias"] or v["brand"] or '') + ' ' + (v["model"] or ''), callback_data=f"mv:{v['id']}")] for v in vehicles]
    await update.message.reply_text("Per quale veicolo?", reply_markup=InlineKeyboardMarkup(buttons))
    return ASK_VEH

async def add_maintenance_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["m_vehicle_id"] = int(query.data.split(":")[1])
    buttons = [[InlineKeyboardButton(t, callback_data=f"mt:{t}")] for t in COMMON_TYPES]
    await query.edit_message_text("Tipo di intervento?", reply_markup=InlineKeyboardMarkup(buttons))
    return ASK_TYPE

async def add_maintenance_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mtype = query.data.split(":")[1]
    if mtype == "Altro":
        await query.edit_message_text("Scrivi il tipo di intervento:")
        context.user_data["m_custom_type"] = True
        return ASK_TYPE
    context.user_data["m_type"] = mtype
    await query.edit_message_text(f"Data dell'intervento? (formato YYYY-MM-DD o DD/MM/YYYY, default {date.today().isoformat()})")
    return ASK_DATE

async def add_maintenance_type_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["m_type"] = update.message.text.strip()
    await update.message.reply_text(f"Data dell'intervento? (formato YYYY-MM-DD o DD/MM/YYYY, default {date.today().isoformat()})")
    return ASK_DATE

async def add_maintenance_km(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = update.message.text.strip()
    if d == "":
        d_iso = date.today().isoformat()
    else:
        d_iso = parse_date(d)
        if not d_iso:
            await update.message.reply_text("Formato data non valido. Riprova (YYYY-MM-DD o DD/MM/YYYY):")
            return ASK_DATE
    context.user_data["m_date"] = d_iso
    await update.message.reply_text("Km al momento dell'intervento? (oppure '-' per saltare)")
    return ASK_KM

async def add_maintenance_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    km_s = update.message.text.strip().replace(".", "").replace(" ", "")
    km = None if km_s == "-" else (int(km_s) if km_s.isdigit() else None)
    if km_s != "-" and km is None:
        await update.message.reply_text("Scrivi un numero oppure '-' per saltare:")
        return ASK_KM
    context.user_data["m_km"] = km
    await update.message.reply_text("Note? (oppure '-' per nessuna)")
    return ASK_NOTES

async def add_maintenance_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes_s = update.message.text.strip()
    context.user_data["m_notes"] = None if notes_s == "-" else notes_s
    await update.message.reply_text("Costo? (es. 120.50) oppure '-' per saltare")
    return ASK_COST

async def add_maintenance_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cost_s = update.message.text.strip().replace(",", ".")
    cost = None if cost_s == "-" else (float(cost_s) if cost_s.replace('.', '', 1).isdigit() else None)
    if cost_s != "-" and cost is None:
        await update.message.reply_text("Inserisci un numero (es. 89.90) oppure '-' per saltare:")
        return ASK_COST
    vid = context.user_data["m_vehicle_id"]
    rec_id = storage.add_maintenance(
        context.bot_data["db_path"],
        vehicle_id=vid,
        date_iso=context.user_data["m_date"],
        km=context.user_data["m_km"],
        mtype=context.user_data["m_type"],
        notes=context.user_data["m_notes"],
        cost=cost
    )
    context.user_data.clear()
    await update.message.reply_text(f"Intervento registrato ✅ (ID {rec_id})")
    return ConversationHandler.END

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    vehicles = storage.list_vehicles(context.bot_data["db_path"], chat_id)
    if not vehicles:
        await update.message.reply_text("Prima aggiungi un veicolo con /add_vehicle.")
        return
    buttons = [[InlineKeyboardButton((v["alias"] or v["brand"] or '') + ' ' + (v["model"] or ''), callback_data=f"hv:{v['id']}")] for v in vehicles]
    await update.message.reply_text("Storico per quale veicolo?", reply_markup=InlineKeyboardMarkup(buttons))

async def history_show_from_vehicle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vid = int(query.data.split(":")[1])
    recs = storage.list_maintenance(context.bot_data["db_path"], vid, limit=30)
    if not recs:
        await query.edit_message_text("Nessun intervento registrato.")
        return
    lines = []
    for r in recs:
        line = f"• {r['date']} — {r['type']}"
        if r["km"]:
            line += f" ({r['km']} km)"
        if r["cost"]:
            line += f" — €{r['cost']:.2f}"
        if r["notes"]:
            line += f" — {r['notes']}"
        lines.append(line)
    await query.edit_message_text("\n".join(lines))

async def history_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vid = int(query.data.split(":")[1])
    recs = storage.list_maintenance(context.bot_data["db_path"], vid, limit=30)
    if not recs:
        await query.edit_message_text("Nessun intervento registrato.")
        return
    lines = []
    for r in recs:
        line = f"• {r['date']} — {r['type']}"
        if r["km"]:
            line += f" ({r['km']} km)"
        if r["cost"]:
            line += f" — €{r['cost']:.2f}"
        if r["notes"]:
            line += f" — {r['notes']}"
        lines.append(line)
    await query.edit_message_text("\n".join(lines))

def get_handlers():
    conv_add = ConversationHandler(
        entry_points=[CommandHandler("add_maintenance", add_maintenance_start)],
        states={
            ASK_VEH: [CallbackQueryHandler(add_maintenance_type, pattern="^mv:")],
            ASK_TYPE: [
                CallbackQueryHandler(add_maintenance_date, pattern="^mt:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_maintenance_type_text)
            ],
            ASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_maintenance_km)],
            ASK_KM: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_maintenance_notes)],
            ASK_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_maintenance_cost)],
            ASK_COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_maintenance_save)],
        },
        fallbacks=[],
        name="add_maint_conv",
        persistent=True,
    )
    return [
        conv_add,
        CommandHandler("history", history),
        CallbackQueryHandler(history_show_from_vehicle, pattern="^vehhist:"),
        CallbackQueryHandler(history_show, pattern="^hv:")
    ]
