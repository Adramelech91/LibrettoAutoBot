
from telegram.ext import ApplicationBuilder, PicklePersistence
from telegram.ext import MessageHandler, filters
from telegram import Update
from app.config import config
from app import storage
from app.handlers import start as h_start
from app.handlers import vehicles as h_vehicles
from app.handlers import maintenance as h_maint
from app.handlers import reminders as h_rem
from app.handlers import export as h_export
from app.keyboards import main_menu
import pytz
from datetime import datetime

async def post_init(app):
    # Inizializza DB
    storage.init_db(config.db_path)
    app.bot_data["db_path"] = config.db_path
    app.bot_data["tz"] = config.tz
    # Ripianifica promemoria a data/ora esistenti
    rows = storage.list_active_time_reminders(config.db_path)
    for r in rows:
        # serve chat_id dall'utente
        import sqlite3
        conn = sqlite3.connect(config.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT chat_id FROM users WHERE id = (SELECT user_id FROM vehicles WHERE id = ?)", (r["vehicle_id"],))
            chat_id_row = cur.fetchone()
            if not chat_id_row:
                continue
            chat_id = chat_id_row[0]
        finally:
            conn.close()
        await h_rem.schedule_time_reminder_job(app, r["id"], r["vehicle_id"], r["due_at"], r["description"], chat_id)
    # Pianifica job giornaliero per km (alle 09:00 locali)
    tz = pytz.timezone(config.tz)
    now_local = datetime.now(tz)
    first_time = now_local.replace(hour=9, minute=0, second=0, microsecond=0)
    if first_time < now_local:
        from datetime import timedelta
        first_time += timedelta(days=1)
    app.job_queue.run_repeating(h_rem.km_checker_job, interval=86400, first=first_time, name="km_checker")

def main():
    persistence = PicklePersistence(filepath="bot-data.pickle")
    app = ApplicationBuilder().token(config.bot_token).persistence(persistence).post_init(post_init).build()

    # Handlers
    for h in h_start.get_handlers(): app.add_handler(h)
    for h in h_vehicles.get_handlers(): app.add_handler(h)
    for h in h_maint.get_handlers(): app.add_handler(h)
    for h in h_rem.get_handlers(): app.add_handler(h)
    for h in h_export.get_handlers(): app.add_handler(h)

    # Router per pulsanti menu testuali
    from app.handlers.vehicles import list_vehicles
    from app.handlers.maintenance import history
    app.add_handler(MessageHandler(filters.Regex("^🚗 Veicoli$"), list_vehicles))
    app.add_handler(MessageHandler(filters.Regex("^🛠️ Manutenzione$"), history))
    app.add_handler(MessageHandler(filters.Regex("^⏰ Promemoria$"), h_rem.set_time_reminder_start))
    app.add_handler(MessageHandler(filters.Regex("^ℹ️ Aiuto$"), h_start.help_cmd))

    print("Bot in esecuzione…")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
