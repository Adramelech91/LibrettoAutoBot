
from telegram import Update, InputFile
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from app.storage import fetch_user_export
import csv, io, pandas as pd

async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = fetch_user_export(context.bot_data["db_path"], chat_id)
    # CSV zip in memoria
    memzip = io.BytesIO()
    import zipfile
    with zipfile.ZipFile(memzip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # vehicles.csv
        v_csv = io.StringIO()
        v_writer = csv.DictWriter(v_csv, fieldnames=["id","alias","plate","brand","model","year","notes","km_current","created_at","user_id"])
        v_writer.writeheader()
        for v in data["vehicles"]:
            v_writer.writerow(v)
        zf.writestr("vehicles.csv", v_csv.getvalue())
        # maintenance.csv
        m_csv = io.StringIO()
        m_writer = csv.DictWriter(m_csv, fieldnames=["id","vehicle_id","date","km","type","notes","cost","created_at","alias"])
        m_writer.writeheader()
        for m in data["maintenance"]:
            m_writer.writerow(m)
        zf.writestr("maintenance.csv", m_csv.getvalue())
        # reminders.csv
        r_csv = io.StringIO()
        r_writer = csv.DictWriter(r_csv, fieldnames=["id","vehicle_id","kind","due_at","km_threshold","description","active","created_at","alias"])
        r_writer.writeheader()
        for r in data["reminders"]:
            r_writer.writerow(r)
        zf.writestr("reminders.csv", r_csv.getvalue())
        # Excel unico
        with pd.ExcelWriter("export.xlsx") as writer:
            pd.DataFrame(data["vehicles"]).to_excel(writer, sheet_name="vehicles", index=False)
            pd.DataFrame(data["maintenance"]).to_excel(writer, sheet_name="maintenance", index=False)
            pd.DataFrame(data["reminders"]).to_excel(writer, sheet_name="reminders", index=False)
        with open("export.xlsx","rb") as f:
            zf.writestr("export.xlsx", f.read())
    memzip.seek(0)
    await update.message.reply_document(document=InputFile(memzip, filename="export.zip"), caption="Ecco l'export CSV + Excel")

def get_handlers():
    return [CommandHandler("export", export_cmd),
            MessageHandler(filters.Regex("^📤 Esporta$"), export_cmd)]
