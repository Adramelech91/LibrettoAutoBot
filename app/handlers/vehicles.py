
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler,
                          ConversationHandler, filters)
from app import storage
from app.keyboards import main_menu, vehicles_inline, vehicle_actions
from app.utils.formatting import clean_plate

ASK_ALIAS, ASK_PLATE, ASK_BRAND, ASK_MODEL, ASK_YEAR, ASK_NOTES = range(6)
ASK_KM_VEHICLE, ASK_KM_VALUE = range(6,8)

async def list_vehicles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    vehicles = storage.list_vehicles(context.bot_data["db_path"], chat_id)
    if not vehicles:
        await update.message.reply_text("Nessun veicolo ancora. Usa /add_vehicle per aggiungerne uno.", reply_markup=main_menu())
        return
    items = [(v["id"], v["alias"] or f"{v['brand']} {v['model']}".strip() or v["plate"] or f"Veicolo #{v['id']}") for v in vehicles]
    await update.message.reply_text("I tuoi veicoli:", reply_markup=vehicles_inline(items))

async def on_vehicle_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vid = int(query.data.split(":")[1])
    v = storage.get_vehicle(context.bot_data["db_path"], vid)
    if not v:
        await query.edit_message_text("Quel veicolo non esiste più.")
        return
    txt = f"**{v['alias'] or v['brand']+' '+v['model'] or v['plate'] or 'Veicolo'}**\n"
    txt += f"Targa: {v['plate'] or '-'}\nMarca/Modello: {v['brand'] or '-'} {v['model'] or ''}\n"
    txt += f"Anno: {v['year'] or '-'}\nKm attuali: {v['km_current']}"
    await query.edit_message_text(txt, reply_markup=vehicle_actions(vid), parse_mode="Markdown")

# Add vehicle flow
async def add_vehicle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ok! Come vuoi chiamare il veicolo? (alias, es. 'Panda Bianca')")
    return ASK_ALIAS

async def ask_plate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["alias"] = update.message.text.strip()
    await update.message.reply_text("Targa? (puoi lasciare vuoto con '-' se non vuoi metterla)")
    return ASK_PLATE

async def ask_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plate = update.message.text.strip()
    context.user_data["plate"] = None if plate == "-" else clean_plate(plate)
    await update.message.reply_text("Marca? (es. Fiat)")
    return ASK_BRAND

async def ask_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["brand"] = update.message.text.strip()
    await update.message.reply_text("Modello? (es. Panda)")
    return ASK_MODEL

async def ask_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["model"] = update.message.text.strip()
    await update.message.reply_text("Anno di immatricolazione? (es. 2015, oppure '-' per saltare)")
    return ASK_YEAR

async def ask_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    year_s = update.message.text.strip()
    context.user_data["year"] = None if year_s == "-" else int(year_s)
    await update.message.reply_text("Note aggiuntive? (oppure '-' per nessuna)")
    return ASK_NOTES

async def add_vehicle_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes_s = update.message.text.strip()
    context.user_data["notes"] = None if notes_s == "-" else notes_s
    chat_id = update.effective_chat.id
    vid = storage.add_vehicle(
        context.bot_data["db_path"],
        chat_id=chat_id,
        alias=context.user_data.get("alias"),
        plate=context.user_data.get("plate"),
        brand=context.user_data.get("brand"),
        model=context.user_data.get("model"),
        year=context.user_data.get("year"),
        notes=context.user_data.get("notes"),
    )
    context.user_data.clear()
    await update.message.reply_text(f"Veicolo aggiunto ✅ (ID {vid}).", reply_markup=main_menu())
    return ConversationHandler.END

# Update KM flow
async def update_km_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    vehicles = storage.list_vehicles(context.bot_data["db_path"], chat_id)
    if not vehicles:
        await update.message.reply_text("Prima aggiungi un veicolo con /add_vehicle.")
        return ConversationHandler.END
    context.user_data["km_choose_map"] = {str(v["id"]): v for v in vehicles}
    buttons = [[InlineKeyboardButton((v["alias"] or v["brand"] or '') + ' ' + (v["model"] or ''), callback_data=f"kmv:{v['id']}")] for v in vehicles]
    await update.message.reply_text("Seleziona veicolo:", reply_markup=InlineKeyboardMarkup(buttons))
    return ASK_KM_VEHICLE

async def update_km_from_vehicle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vid = int(query.data.split(":")[1])
    context.user_data["km_vehicle_id"] = vid
    await query.edit_message_text("Inserisci il nuovo chilometraggio (numero intero):")
    return ASK_KM_VALUE

async def update_km_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vid = int(query.data.split(":")[1])
    context.user_data["km_vehicle_id"] = vid
    await query.edit_message_text("Inserisci il nuovo chilometraggio (numero intero):")
    return ASK_KM_VALUE

async def update_km_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print ("update_km_save")
    km_s = update.message.text.strip().replace(".", "").replace(" ", "")
    if not km_s.isdigit():
        await update.message.reply_text("Formato non valido. Scrivi solo numeri (es. 123456).")
        return ASK_KM_VALUE
    vid = context.user_data.get("km_vehicle_id")
    storage.update_vehicle_km(context.bot_data["db_path"], vid, int(km_s))
    context.user_data.pop("km_vehicle_id", None)
    await update.message.reply_text("Chilometraggio aggiornato ✅")
    return ConversationHandler.END

async def delete_vehicle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vid = int(query.data.split(":")[1])
    storage.delete_vehicle(context.bot_data["db_path"], vid)
    await query.edit_message_text("Veicolo eliminato ✅")

def get_handlers():
    conv_add = ConversationHandler(
        entry_points=[CommandHandler("add_vehicle", add_vehicle_start),
                      MessageHandler(filters.Regex("^🚗 Veicoli$"), list_vehicles)],
        states={
            ASK_ALIAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_plate)],
            ASK_PLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_brand)],
            ASK_BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_model)],
            ASK_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_year)],
            ASK_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_notes)],
            ASK_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_vehicle_save)],
        },
        fallbacks=[],
        name="add_vehicle_conv",
        persistent=True,
    )
    conv_km = ConversationHandler(
        entry_points=[CommandHandler("update_km", update_km_start),
                      CallbackQueryHandler(update_km_from_vehicle, pattern="^vehkm:")],
        states={
            ASK_KM_VEHICLE: [CallbackQueryHandler(update_km_choose, pattern="^kmv:")],
            ASK_KM_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_km_save)]
        },
        fallbacks=[],
        name="update_km_conv",
        persistent=True,
    )
    return [
        CommandHandler("vehicles", list_vehicles),
        CallbackQueryHandler(on_vehicle_pressed, pattern="^veh:"),
        CallbackQueryHandler(delete_vehicle_cb, pattern="^vehdel:"),
        conv_add,
        conv_km,
    ]
