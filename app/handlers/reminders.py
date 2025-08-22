
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler,
                          ConversationHandler, filters)
from app import storage
from app.utils.formatting import parse_datetime
from datetime import datetime, timedelta
from app.keyboards import cancel
import pytz

ASK_VEH_TIME, ASK_DT, ASK_DESC = range(3)
ASK_VEH_KM, ASK_KM, ASK_DESC_KM = range(3,6)

async def set_time_reminder_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    vehicles = storage.list_vehicles(context.bot_data["db_path"], chat_id)
    if not vehicles:
        await update.message.reply_text("Prima aggiungi un veicolo con /add_vehicle.")
        return ConversationHandler.END
    buttons = [[InlineKeyboardButton((v["alias"] or v["brand"] or '') + ' ' + (v["model"] or ''), callback_data=f"rtv:{v['id']}")] for v in vehicles]
    await update.message.reply_text("Per quale veicolo?", reply_markup=InlineKeyboardMarkup(buttons))
    return ASK_VEH_TIME

async def set_time_reminder_dt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["r_vehicle_id"] = int(query.data.split(":")[1])
    tzname = context.bot_data.get("tz", "Europe/Rome")
    now_local = datetime.now(pytz.timezone(tzname)).replace(second=0, microsecond=0)
    default = now_local + timedelta(days=7)
    await query.edit_message_text(f"Quando vuoi il promemoria? (formato YYYY-MM-DD HH:MM o DD/MM/YYYY HH:MM — default {default.strftime('%Y-%m-%d %H:%M')})")
    return ASK_DT

async def set_time_reminder_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dt_s = update.message.text.strip()
    if dt_s == "":
        tzname = context.bot_data.get("tz", "Europe/Rome")
        default = datetime.now(pytz.timezone(tzname)).replace(second=0, microsecond=0) + timedelta(days=7)
        dt_iso = default.strftime("%Y-%m-%d %H:%M")
    else:
        dt_iso = parse_datetime(dt_s)
        if not dt_iso:
            await update.message.reply_text("Formato non valido. Prova con 'YYYY-MM-DD HH:MM' o 'DD/MM/YYYY HH:MM'")
            return ASK_DT
    context.user_data["r_when"] = dt_iso
    await update.message.reply_text("Descrizione breve? (es. Revisione, Bollo, Tagliando)")
    return ASK_DESC

async def set_time_reminder_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    vid = context.user_data["r_vehicle_id"]
    rem_id = storage.add_time_reminder(context.bot_data["db_path"], vid, context.user_data["r_when"], desc)
    # schedule job
    await schedule_time_reminder_job(context, rem_id, vid, context.user_data["r_when"], desc, chat_id=update.effective_chat.id)
    context.user_data.clear()
    await update.message.reply_text("Promemoria a data/ora impostato ✅")
    return ConversationHandler.END

async def schedule_time_reminder_job(context: ContextTypes.DEFAULT_TYPE, reminder_id: int, vehicle_id: int, due_at_iso: str, description: str, chat_id: int):
    tzname = context.bot_data.get("tz", "Europe/Rome")
    tz = pytz.timezone(tzname)
    dt = datetime.fromisoformat(due_at_iso)
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    async def callback(ctx: ContextTypes.DEFAULT_TYPE):
        await ctx.bot.send_message(chat_id=chat_id, text=f"⏰ Promemoria: {description} (veicolo ID {vehicle_id})")
        storage.deactivate_reminder(ctx.bot_data["db_path"], reminder_id)
    context.job_queue.run_once(
        callback,
        when=dt,
        name=f"rem_time_{reminder_id}",
        data={"reminder_id": reminder_id, "vehicle_id": vehicle_id, "chat_id": chat_id, "description": description}
    )

# KM Reminder
async def set_km_reminder_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    vehicles = storage.list_vehicles(context.bot_data["db_path"], chat_id)
    if not vehicles:
        await update.message.reply_text("Prima aggiungi un veicolo con /add_vehicle.")
        return ConversationHandler.END
    buttons = [[InlineKeyboardButton((v["alias"] or v["brand"] or '') + ' ' + (v["model"] or ''), callback_data=f"rkv:{v['id']}")] for v in vehicles]
    await update.message.reply_text("Per quale veicolo?", reply_markup=InlineKeyboardMarkup(buttons))
    return ASK_VEH_KM

async def set_km_reminder_km(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["rk_vehicle_id"] = int(query.data.split(":")[1])
    await query.edit_message_text("A quanti km vuoi essere avvisato? (numero intero)")
    return ASK_KM

async def set_km_reminder_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    km_s = update.message.text.strip().replace(".", "").replace(" ", "")
    if not km_s.isdigit():
        await update.message.reply_text("Scrivi solo numeri (es. 10000).")
        return ASK_KM
    context.user_data["rk_km"] = int(km_s)
    await update.message.reply_text("Descrizione breve? (es. Cambio olio a 10000 km)")
    return ASK_DESC_KM

async def set_km_reminder_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    vid = context.user_data["rk_vehicle_id"]
    km_thr = context.user_data["rk_km"]
    rem_id = storage.add_km_reminder(context.bot_data["db_path"], vid, km_thr, desc)
    context.user_data.clear()
    await update.message.reply_text("Promemoria km impostato ✅. Sarai avvisato quando superi la soglia.")
    return ConversationHandler.END

# Daily checker for KM reminders
async def km_checker_job(context: ContextTypes.DEFAULT_TYPE):
    rows = storage.list_active_km_reminders(context.bot_data["db_path"])
    for r in rows:
        if r["km_threshold"] is not None and r["km_current"] is not None and r["km_current"] >= r["km_threshold"]:
            # fetch chat id via vehicle->user_id->users.chat_id
            # quick join to get chat
            # For simplicity we added user_id above in query; now we need chat_id:
            # We'll query users by id
            import sqlite3
            conn = sqlite3.connect(context.bot_data["db_path"])
            try:
                cur = conn.cursor()
                cur.execute("SELECT chat_id FROM users WHERE id = ?", (r["user_id"],))
                chat_id = cur.fetchone()[0]
            finally:
                conn.close()
            await context.bot.send_message(chat_id=chat_id, text=f"⏰ Promemoria km: {r['description']} (veicolo {r['alias']}) - soglia {r['km_threshold']} km raggiunta/superata.")
            storage.deactivate_reminder(context.bot_data["db_path"], r["id"])

def get_handlers():
    conv_time = ConversationHandler(
        entry_points=[CommandHandler("set_time_reminder", set_time_reminder_start)],
        states={
            ASK_VEH_TIME: [CallbackQueryHandler(set_time_reminder_dt, pattern="^rtv:")],
            ASK_DT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_time_reminder_desc)],
            ASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_time_reminder_save)],
        },
        fallbacks=[],
        name="set_time_reminder_conv",
        persistent=True,
    )
    conv_km = ConversationHandler(
        entry_points=[CommandHandler("set_km_reminder", set_km_reminder_start)],
        states={
            ASK_VEH_KM: [CallbackQueryHandler(set_km_reminder_km, pattern="^rkv:")],
            ASK_KM: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_km_reminder_desc)],
            ASK_DESC_KM: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_km_reminder_save)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="set_km_reminder_conv",
        persistent=True,
    )
    return [
        conv_time,
        conv_km,
    ]
