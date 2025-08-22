
# Bot Libretto Manutenzione Auto (PTB)

Bot Telegram per gestire veicoli, interventi di manutenzione, promemoria (tempo e km) ed export dei dati.

## Requisiti
- Python 3.10+
- Una API token di Telegram (crealo con @BotFather)

## Installazione
```bash
python -m venv librettoauto
source librettoauto/bin/activate  # su Windows: .librettoauto\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# poi apri .env e incolla il tuo BOT_TOKEN
```

## Avvio
```bash
python -m app.main
```

## Struttura
```
app/
  main.py               # bootstrap PTB, handlers, job queue
  config.py             # lettura env/config
  storage.py            # SQLite + CRUD
  keyboards.py          # tastiere/inline keyboards
  utils/
    __init__.py
    formatting.py       # helper formattazione/validazione
  handlers/
    start.py            # /start, /help, menu
    vehicles.py         # gestione veicoli + km
    maintenance.py      # registrazione interventi, storico
    reminders.py        # promemoria tempo e km, job queue
    export.py           # export CSV/XLSX
data/
  (db verrà creato al primo avvio)
```

## Note velocissime
- Promemoria **tempo**: usa JobQueue `run_once`. Alla partenza il bot ricarica e ripianifica i reminder futuri.
- Promemoria **km**: c'è un job giornaliero che controlla le soglie km vs chilometraggio attuale.
- Export: CSV sempre; XLSX opzionale (richiede `openpyxl`, già in requirements).

## Comandi principali
- `/start` — menu iniziale
- `/help` — guida rapida
- `/vehicles` — elenco veicoli e azioni
- `/add_vehicle` — procedura guidata per aggiungere veicolo
- `/update_km` — aggiorna chilometraggio del veicolo scelto
- `/add_maintenance` — aggiungi intervento (tagliando, olio, ecc.)
- `/history` — storico interventi
- `/set_time_reminder` — promemoria a data/ora
- `/set_km_reminder` — promemoria al raggiungimento km
- `/export` — esporta dati

---

Se vuoi rinominare cartelle o semplificare ulteriormente, puoi farlo: il codice è commentato.
