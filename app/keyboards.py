
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Tuple

MAIN_BTNS = [
    [KeyboardButton("🚗 Veicoli"), KeyboardButton("🛠️ Manutenzione")],
    [KeyboardButton("⏰ Promemoria"), KeyboardButton("📤 Esporta")],
    [KeyboardButton("ℹ️ Aiuto")]
]

def main_menu():
    return ReplyKeyboardMarkup(MAIN_BTNS, resize_keyboard=True)

def vehicles_inline(vehicles: List[Tuple[int, str]]):
    rows = [[InlineKeyboardButton(f"{alias}", callback_data=f"veh:{vid}")] for vid, alias in vehicles]
    return InlineKeyboardMarkup(rows)

def vehicle_actions(vehicle_id: int):
    rows = [
        [InlineKeyboardButton("Aggiorna km", callback_data=f"vehkm:{vehicle_id}")],
        [InlineKeyboardButton("Storico interventi", callback_data=f"vehhist:{vehicle_id}")],
        [InlineKeyboardButton("Elimina veicolo", callback_data=f"vehdel:{vehicle_id}")]
    ]
    return InlineKeyboardMarkup(rows)
