from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import os

app = FastAPI(title="Wróbel Motors - System Warsztatowy 2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "warsztat.db"

# Hasła użytkowników
USERS = {
    "Kuba": "warsztat123",
    "Damian": "warsztat123"
}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zlecenia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_zlecenia TEXT UNIQUE,
            data_przyjecia TEXT,
            data_zakonczenia TEXT,
            mechanik TEXT,
            klient TEXT,
            telefon TEXT,
            pojazd TEXT,
            nr_rejestracyjny TEXT,
            stock_id TEXT,
            vin TEXT,
            opis_czesci TEXT,
            czesci_klienta INTEGER DEFAULT 0,
            olej_id INTEGER DEFAULT 0,
            olej_nazwa TEXT DEFAULT 'Brak',
            olej_ilosc REAL DEFAULT 0.0,
            plyn_hamulcowy INTEGER DEFAULT 0,
            plyn_chlodniczy INTEGER DEFAULT 0,
            koszt_czesci REAL DEFAULT 0.0,
            koszt_robocizny REAL DEFAULT 0.0,
            wplacono REAL DEFAULT 0.0,
            status_naprawy TEXT DEFAULT '🟡 Oczekuje na części',
            notatka TEXT DEFAULT ''
        )
    ''')
    
    nowe_kolumny = [
        ("czesci_klienta", "INTEGER DEFAULT 0"),
        ("olej_id", "INTEGER DEFAULT 0"),
        ("olej_nazwa", "TEXT DEFAULT 'Brak'"),
        ("olej_ilosc", "REAL DEFAULT 0.0"),
        ("plyn_hamulcowy", "INTEGER DEFAULT 0"),
        ("plyn_chlodniczy", "INTEGER DEFAULT 0")
    ]
    for col_name, col_type in nowe_kolumny:
        try:
            cursor.execute(f"ALTER TABLE zlecenia ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS magazyn (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazwa TEXT UNIQUE,
            kategoria TEXT,
            ilosc REAL,
            jednostka TEXT,
            cena_za_jedn REAL,
            minimum_alarm REAL
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM magazyn")
    if cursor.fetchone()[0] == 0:
        domyslny_magazyn = [
            ("Olej 5W30 Castrol/Motul", "Olej silnikowy", 60.0, "L", 45.0, 15.0),
            ("Olej 5W40 Syntetyk", "Olej silnikowy", 40.0, "L", 40.0, 10.0),
            ("Olej 0W20 PureTech/Nowe", "Olej silnikowy", 25.0, "L", 55.0, 10.0),
            ("Płyn hamulcowy DOT-4", "Płyn eksploatacyjny", 10.0, "L", 35.0, 3.0),
            ("Płyn chłodniczy G12+", "Płyn eksploatacyjny", 30.0, "L", 18.0, 10.0)
        ]
        cursor.executemany('''
            INSERT INTO magazyn (nazwa, kategoria, ilosc, jednostka, cena_za_jedn, minimum_alarm)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', domyslny_magazyn)

    conn.commit()
    conn.close()

init_db()

# --- MODELE DANYCH ---
class LoginSchema(BaseModel):
    uzytkownik: str
    haslo: str

class ZlecenieSchema(BaseModel):
    id_zlecenia: str
    data_przyjecia: str
    data_zakonczenia: str = ""
    mechanik: str
    klient: str
    telefon: str = ""
    pojazd: str
    nr_rejestracyjny: str = ""
    stock_id: str = ""
    vin: str = ""
    opis_czesci: str = ""
    czesci_klienta: int = 0
    olej_id: int = 0
    olej_nazwa: str = "Brak"
    olej_ilosc: float = 0.0
    plyn_hamulcowy: int = 0
    plyn_chlodniczy: int = 0
    koszt_czesci: float = 0.0
    koszt_robocizny: float = 0.0
    wplacono: float = 0.0
    status_naprawy: str = "🟡 Oczekuje na części"
    notatka: str = ""

class StatusSchema(BaseModel):
    status_naprawy: str

class MagazynSchema(BaseModel):
    nazwa: str
    kategoria: str = "Olej silnikowy"
    ilosc: float
    jednostka: str = "L"
    cena_za_jedn: float = 0.0
    minimum_alarm: float = 5.0

class MagazynIloscSchema(BaseModel):
    zmiana: float

# --- WYŚWIETLANIE APLIKACJI BEZPOŚREDNIO POD ADRESEM http://127.0.0.1:8000 ---
@app.get("/")
def serve_frontend():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "Serwer działa, ale nie znaleziono pliku index.html w tym folderze"}

# --- ENDPOINTY LOGOWANIA ---
@app.post("/api/login")
def login(dane: LoginSchema):
    user_clean = dane.uzytkownik.strip()
    pass_clean = dane.haslo.strip()
    if user_clean in USERS and USERS[user_clean] == pass_clean:
        return {"sukces": True, "uzytkownik": user_clean}
    raise HTTPException(status_code=401, detail="Nieprawidłowe hasło!")

# --- ENDPOINTY ZLECEŃ ---
@app.get("/api/zlecenia")
def pobierz_zlecenia():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM zlecenia ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/zlecenia")
def dodaj_zlecenie(z: ZlecenieSchema):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO zlecenia (
                id_zlecenia, data_przyjecia, data_zakonczenia, mechanik, klient, telefon,
                pojazd, nr_rejestracyjny, stock_id, vin, opis_czesci, czesci_klienta,
                olej_id, olej_nazwa, olej_ilosc, plyn_hamulcowy, plyn_chlodniczy,
                koszt_czesci, koszt_robocizny, wplacono, status_naprawy, notatka
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            z.id_zlecenia, z.data_przyjecia, z.data_zakonczenia, z.mechanik, z.klient, z.telefon,
            z.pojazd, z.nr_rejestracyjny, z.stock_id, z.vin, z.opis_czesci, z.czesci_klienta,
            z.olej_id, z.olej_nazwa, z.olej_ilosc, z.plyn_hamulcowy, z.plyn_chlodniczy,
            z.koszt_czesci, z.koszt_robocizny, z.wplacono, z.status_naprawy, z.notatka
        ))
        
        if z.olej_id > 0 and z.olej_ilosc > 0:
            cursor.execute("UPDATE magazyn SET ilosc = MAX(0, ilosc - ?) WHERE id = ?", (z.olej_ilosc, z.olej_id))
        if z.plyn_hamulcowy == 1:
            cursor.execute("UPDATE magazyn SET ilosc = MAX(0, ilosc - 1.0) WHERE nazwa LIKE '%hamulcowy%'")
        if z.plyn_chlodniczy == 1:
            cursor.execute("UPDATE magazyn SET ilosc = MAX(0, ilosc - 5.0) WHERE nazwa LIKE '%chłodniczy%'")

        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    conn.close()
    return {"sukces": True}

@app.put("/api/zlecenia/{id}")
def edytuj_zlecenie(id: int, z: ZlecenieSchema):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE zlecenia SET
                id_zlecenia=?, data_przyjecia=?, data_zakonczenia=?, mechanik=?, klient=?, telefon=?,
                pojazd=?, nr_rejestracyjny=?, stock_id=?, vin=?, opis_czesci=?, czesci_klienta=?,
                olej_id=?, olej_nazwa=?, olej_ilosc=?, plyn_hamulcowy=?, plyn_chlodniczy=?,
                koszt_czesci=?, koszt_robocizny=?, wplacono=?, status_naprawy=?, notatka=?
            WHERE id=?
        ''', (
            z.id_zlecenia, z.data_przyjecia, z.data_zakonczenia, z.mechanik, z.klient, z.telefon,
            z.pojazd, z.nr_rejestracyjny, z.stock_id, z.vin, z.opis_czesci, z.czesci_klienta,
            z.olej_id, z.olej_nazwa, z.olej_ilosc, z.plyn_hamulcowy, z.plyn_chlodniczy,
            z.koszt_czesci, z.koszt_robocizny, z.wplacono, z.status_naprawy, z.notatka, id
        ))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    conn.close()
    return {"sukces": True}

@app.patch("/api/zlecenia/{id}/status")
def zmien_status_zlecenia(id: int, dane: StatusSchema):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE zlecenia SET status_naprawy = ? WHERE id = ?", (dane.status_naprawy, id))
    conn.commit()
    conn.close()
    return {"sukces": True}

@app.delete("/api/zlecenia/{id}")
def usun_zlecenie(id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM zlecenia WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"sukces": True}

# --- ENDPOINTY MAGAZYNU ---
@app.get("/api/magazyn")
def pobierz_magazyn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM magazyn ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/magazyn")
def dodaj_magazyn(item: MagazynSchema):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO magazyn (nazwa, kategoria, ilosc, jednostka, cena_za_jedn, minimum_alarm)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (item.nazwa, item.kategoria, item.ilosc, item.jednostka, item.cena_za_jedn, item.minimum_alarm))
    conn.commit()
    conn.close()
    return {"sukces": True}

@app.patch("/api/magazyn/{id}")
def zmien_ilosc_magazyn(id: int, dane: MagazynIloscSchema):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE magazyn SET ilosc = MAX(0, ilosc + ?) WHERE id = ?", (dane.zmiana, id))
    conn.commit()
    conn.close()
    return {"sukces": True}

@app.delete("/api/magazyn/{id}")
def usun_magazyn(id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM magazyn WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"sukces": True}