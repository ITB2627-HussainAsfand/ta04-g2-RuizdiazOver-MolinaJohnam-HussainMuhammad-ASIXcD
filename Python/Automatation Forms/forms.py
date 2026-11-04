#!/usr/bin/env python3
"""
====================================================================
MÒDUL: Automatitzador d'Enviaments de Google Forms (gform_automatic.py)
--------------------------------------------------------------------
DESCRIPCIÓ:
    Envia respostes "coherents però trolls" a Google Forms.
    Mètode HÍBRID:
      1. Via ràpida: requests (HTTP POST).
      2. Fallback: Chromium headless (Playwright) si hi ha 401/403
         o no es pot extreure l'estructura del formulari.
    Pregunta per terminal: enllaços, nº de respostes i nivell de trolleig.

INSTAL·LACIÓ (Codespaces):
    sudo apt update && sudo apt install -y python3-venv && \
    python3 -m venv .venv && source .venv/bin/activate && \
    pip install faker requests beautifulsoup4 playwright && \
    playwright install-deps chromium && playwright install chromium

ÚS:
    .venv/bin/python gform_automatic.py                       # mode interactiu
    .venv/bin/python gform_automatic.py "https://forms.gle/x" # URL directa
    .venv/bin/python gform_automatic.py URL -n 10 -t 3        # sense preguntes
====================================================================
"""
import argparse
import json
import random
import re
import sys
import time
from datetime import date, timedelta
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from faker import Faker

# Formularis per defecte (opcional). També es poden enganxar per terminal
# amb el format  nom=url  o només la url.
FORMS = {
    # "joi": "https://forms.gle/xxxxxxxx",
}

# ----------------------------------------------------------------------
# COLORS / UI
# ----------------------------------------------------------------------
class C:
    R = "\033[0m"; B = "\033[1m"; D = "\033[2m"
    RED = "\033[91m"; GRN = "\033[92m"; YEL = "\033[93m"
    BLU = "\033[94m"; MAG = "\033[95m"; CYN = "\033[96m"; WHT = "\033[97m"

STUDENT_COLORS = [C.CYN, C.MAG, C.YEL, C.GRN, C.BLU, C.RED, C.WHT]
WIDTH = 72
LEVEL = 2  # nivell de trolleig (1 suau, 2 mitjà, 3 caos) -> es fixa a main()
LEVEL_NAMES = {1: "SUAVE", 2: "MEDIO", 3: "CAOS TOTAL"}
PERSONA_TROLL_PROB = {1: 0.05, 2: 0.30, 3: 0.60}


def banner():
    print(C.GRN + C.B + "=" * WIDTH)
    print("  GFORM AUTOMATIC  ::  troll edition".center(WIDTH))
    print("=" * WIDTH + C.R)


def student_header(name, color, idx, total, url):
    print()
    print(color + C.B + "╔" + "═" * (WIDTH - 2) + "╗")
    print("║" + f"  ALUMNE {idx}/{total}  ➜  {name.upper()}"[:WIDTH - 3].ljust(WIDTH - 2) + "║")
    print("╚" + "═" * (WIDTH - 2) + "╝" + C.R)
    print(C.D + f"  {url[:WIDTH - 4]}" + C.R)


def bar(done, total, color, size=24):
    filled = int(size * done / max(total, 1))
    return f"{color}[{'█' * filled}{'░' * (size - filled)}]{C.R} {done}/{total}"


def log(tag, msg, color=C.WHT):
    print(f"  {color}{tag:<8}{C.R} {msg}")


# ----------------------------------------------------------------------
# PREGUNTES PER TERMINAL
# ----------------------------------------------------------------------
def ask_int(prompt, default, lo, hi):
    while True:
        raw = input(f"{C.CYN}{C.B}? {prompt}{C.R} {C.D}[{default}]{C.R}: ").strip()
        if not raw:
            return default
        if raw.isdigit() and lo <= int(raw) <= hi:
            return int(raw)
        print(f"  {C.RED}Introduce un número entre {lo} y {hi}.{C.R}")


def ask_level():
    print(f"\n  {C.GRN}1){C.R} Suave       {C.D}formal, fechas normales, casi nada de troll{C.R}")
    print(f"  {C.YEL}2){C.R} Medio       {C.D}formal + informal, fechas variadas, a veces catalán antiguo{C.R}")
    print(f"  {C.RED}3){C.R} Caos total  {C.D}absurdos, MAYÚSCULAS, emojis, catalán antiguo y binario{C.R}")
    return ask_int("¿Qué nivel de trolleo?", 2, 1, 3)


def ask_urls():
    print(f"{C.CYN}{C.B}? Pega los enlaces{C.R} {C.D}(uno por línea, 'nombre=url' o solo url; línea vacía para acabar){C.R}")
    targets = {}
    while True:
        line = input("  > ").strip()
        if not line:
            break
        name, _, url = line.partition("=") if "=" in line and not line.startswith("http") else ("", "", line)
        targets[name.strip() or f"form{len(targets) + 1}"] = url.strip()
    return targets


# ----------------------------------------------------------------------
# DADES: PERSONA, DATES, INCIDÈNCIES
# ----------------------------------------------------------------------
fake = Faker("es_ES")

TROLL_NICKS = [
    "Paco Pepe", "Batman", "Mr. Bean", "Chuck Norris", "Shrek", "Darth Vader", "Siri",
    "El Fary", "Mbappé Jr.", "Kratos", "Elon Musk", "Keanu Reeves", "Nicolas Cage",
    "Rick Astley", "Gordon Ramsay", "Bad Bunny", "Shakira Mebarak", "Rafa Nadal",
    "Cristiano Ronaldo", "Lionel Messi", "Ibai Llanos", "El Rubius", "AuronPlay",
    "Willyrex Pérez", "Vegetta777", "Spiderman", "Homer Simpson", "Bob Esponja",
    "Pikachu Ketchum", "Mario Bros", "Luigi Bros", "Sonic Hedgehog", "Goku Son",
    "Vegeta Saiyan", "Naruto Uzumaki", "Gandalf el Gris", "Harry Potter", "Jack Sparrow",
    "Tony Stark", "Thanos Titán", "Baby Yoda", "Obi-Wan Kenobi", "Walter White",
    "Jesse Pinkman", "Saul Goodman", "Joker Arthur", "Michael Scott", "Dwayne Johnson",
    "Will Smith", "Morgan Freeman", "Arnold Schwarzenegger", "Jackie Chan", "Bruce Lee",
    "Mark Zuckerberg", "Bill Gates", "Steve Jobs", "Pedro Sánchez Castejón", "Camilo Sesto",
    "Chiquito de la Calzada", "Torrente Marbella", "Paquirrín Jr.", "Jorge Javier Vázquez",
    "Gominolas Pérez", "Dr. Simi", "Peter Griffin", "Cartman Broflovski", "Sheldon Cooper",
    "Super Mario Gutiérrez", "Pablo Escobar", "Lalo Salamanca", "Doge Shiba",
]

# Nombres con doble sentido (juegos de palabras)
PUN_NAMES = [
    "Escroto Lamo", "Estes Ticulos", "Aitor Menta", "Alan Brito", "Armando Bronca",
    "Elsa Pato", "Susana Oria", "Dolores Delano", "Elba Lazo", "Aitor Tilla",
    "Pedro Medario", "Ester Colero", "Jordi Lleno", "Lola Mento", "Paco Germe",
    "Salvador Dalí Bueno", "Ramón Tón", "Mario Neta", "Armando Jaleo", "Rosa Melano",
    "Ana Conda", "Marcos Corrón", "Sara Pe", "Cristina Pocos", "Iván Mi Lluvia",
    "Fermín Tilla", "Domingo Festivo", "Aquiles Baeza", "Segismundo Pitado", "Benito Camelas",
    "Débora Dillo", "Quirino Cenaré", "Dimas Pierdo", "Lucas Marrón", "Jesús Mellado",
    "Ignacio Nada", "Moisés Tás", "Aurora Boreal Pérez", "Mohamed Cansado", "Pilar Mendoza",
]
TROLL_NICKS += PUN_NAMES
TROLL_SHORT = ["42", "depende", "pizza", "ni idea", "sí, pero no", "lo que diga el gato",
               "mañana", "bocata de calamares", "error 404", "porque sí", "marmota", "(⌐■_■)"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# (titulo corto, frase formal, frase informal)
PROBLEMS = [
    ("Sin luz en el aula", "se ha producido un corte de suministro eléctrico en el aula", "se ha estropeado la luz"),
    ("El ratón no funciona", "el ratón asignado a mi puesto no responde", "el ratón no ratonea"),
    ("Pantalla sin imagen", "la pantalla del equipo no muestra ninguna imagen", "la pantalla no se ve nada"),
    ("Sin conexión wifi", "el equipo no dispone de conexión a la red inalámbrica", "no tiene wifi y estoy sufriendo"),
    ("Teclado con teclas atascadas", "varias teclas del teclado no registran las pulsaciones", "el teclado no escribe la mitad de las letras"),
    ("El PC no arranca", "el ordenador no completa el proceso de arranque", "el pc no enciende ni a tiros"),
    ("Pantalla azul", "el sistema muestra un error crítico (pantalla azul) de forma recurrente", "me sale la pantalla azul otra vez"),
    ("Ordenador muy lento", "el rendimiento del equipo es muy inferior al esperable", "va lentísimo, tarda en abrir hasta el bloc de notas"),
    ("Proyector sin señal", "el proyector del aula no recibe señal de entrada", "el proyector dice 'sin señal' y ya"),
    ("Impresora atascada", "la impresora presenta un atasco de papel persistente", "la impresora se ha tragado el papel"),
    ("Enchufe quemado", "el enchufe del puesto presenta signos de sobrecalentamiento", "el enchufe huele a quemado"),
    ("Sin sonido", "el equipo no reproduce audio por los altavoces ni por los auriculares", "no se oye nada, ni los cascos"),
    ("Contraseña bloqueada", "mi cuenta de usuario ha quedado bloqueada tras varios intentos", "no me acuerdo de la contraseña y me ha bloqueado"),
    ("Silla rota", "la silla del puesto tiene el mecanismo de altura averiado", "la silla se hunde sola, voy bajando por clase"),
    ("Aire acondicionado averiado", "el aire acondicionado no funciona y la temperatura es elevada", "hace un calor que no veas, el aire no va"),
]
ABSURD = [
    ("El ratón se ha ido de vacaciones", "el ratón se ha ido de vacaciones y no ha dejado dirección"),
    ("El wifi me ha dejado en visto", "el wifi ve mis peticiones y no responde, estoy dolido"),
    ("Mi PC está en huelga", "mi ordenador ha convocado huelga indefinida y no hay servicios mínimos"),
    ("Pingüino en la pantalla", "aparece un pingüino en la pantalla y no se quiere ir"),
    ("La luz tiene miedo a la oscuridad", "se ha ido la luz y ahora tengo miedo"),
    ("El teclado escribe en élfico", "el teclado ahora escribe en élfico y no domino el idioma"),
]
OPENERS = ["Buenos días,", "Estimados compañeros,", "A quien corresponda,", "Muy buenas,", "Cordial saludo,"]
CLOSERS = ["Agradecería una solución lo antes posible.", "Quedo a la espera de su respuesta.",
           "Les agradezco de antemano su atención.", "Solicito su revisión con carácter urgente."]
INFORMAL_OPEN = ["ei", "buenas", "holaaa", "oye", "q tal"]
INFORMAL_END = ["¿alguien puede mirarlo?", "arreglad esto porfa", "gracias crack", "urgente!!", "pls 🙏", "xd"]


def messy(text):
    """Caos nivel 3: mayúsculas, letras repetidas y emojis."""
    words = text.split()
    out = []
    for w in words:
        r = random.random()
        if r < 0.12:
            w = w.upper()
        elif r < 0.18 and len(w) > 3:
            i = random.randint(1, len(w) - 2)
            w = w[:i] + w[i] * random.randint(2, 4) + w[i + 1:]
        out.append(w)
    return " ".join(out) + " " + random.choice(["😭", "💀", "🔥", "🤡", "😤", "🫠", "!!!"])


class Persona:
    """Identitat coherent: nom, correu, telèfon... lligats entre si."""
    def __init__(self):
        self.troll = random.random() < PERSONA_TROLL_PROB[LEVEL]
        self.name = random.choice(TROLL_NICKS) if self.troll else fake.name()
        first, *rest = self.name.split()
        self.first = first
        self.last = " ".join(rest) or fake.last_name()
        slug = re.sub(r"[^a-z0-9]", "", (first + self.last).lower()
                      .translate(str.maketrans("áéíóúñàèòç", "aeiounaeoc")))
        self.email = f"{slug}{random.randint(1, 99)}@{random.choice(['gmail.com', 'outlook.es', 'proton.me'])}"
        self.phone = fake.phone_number().replace(" ", "")
        self.age = random.randint(15, 45)
        self.city = fake.city()
        self.address = fake.address().replace("\n", ", ")
        self.problem = random.choice(PROBLEMS)
        self.absurd = LEVEL == 3 and random.random() < 0.4
        self.style = "formal" if LEVEL == 1 else random.choice(["formal", "informal"])
        self.pc = f"PC-{random.randint(1, 30):02d}"
        self.room = random.choice(["Aula 1", "Aula 2", "Aula 3", "Lab. Informática", "Sala B12", "Taller"])


def incident_short(p):
    if p.absurd:
        return random.choice(ABSURD)[0]
    short, _, informal = p.problem
    txt = short if p.style == "formal" else informal.capitalize()
    return messy(txt) if LEVEL == 3 and random.random() < 0.5 else txt


OLD_CAT_PROB = {1: 0.0, 2: 0.25, 3: 0.35}
BINARY_PROB = {1: 0.0, 2: 0.10, 3: 0.25}

# Català antic (estil medieval) per a algunes incidències concretes
OLD_CAT_SPECIFIC = {
    "Sin luz en el aula": "Sàpia vostra mercè que la lum és fallida en la sala e tot és en tenebres, ni hom hi veu res.",
    "El ratón no funciona": "Lo ratolí no vol obeir ma mà, e jo·l crit en va; faça·s lo que pusca per ell, que no·s mou.",
    "Pantalla sin imagen": "La pantalla és fosca com la nit e no mostra figura nenguna, ço és gran dampnatge.",
    "Sin conexión wifi": "La xarxa sens fil és fugida e no hi ha qui la hi torn; sens ella no puc cosa a fer.",
}
OLD_CAT_GENERIC = [
    "Sàpia vostra mercè que en {room} lo {pc} és affollat de mal: «{title}». Preg que hi sia posat remei prestament.",
    "Fem saber a tots los qui açò legiran que lo {pc} d'{room} ha pres gran dampnatge: «{title}». Déu vos guard.",
    "Hoïu, bons companyons: en {room} ha esdevengut cas de gran enuig: «{title}». Siau servits de socórrer-nos.",
    "En nom de Déu e de bona ventura, notifique a vostra senyoria que·l {pc} és trencat: «{title}». Sia fet lo que·s deu.",
]


def old_catalan(p):
    title = p.problem[0]
    base = OLD_CAT_SPECIFIC.get(title) or random.choice(OLD_CAT_GENERIC).format(
        room=p.room, pc=p.pc, title=title.lower())
    return f"{base} — {p.first}, a {date.today().day} de {MESES[date.today().month - 1]}"


def to_binary(text):
    return " ".join(f"{b:08b}" for b in text.encode("utf-8"))


def incident_long(p):
    r = random.random()
    if r < OLD_CAT_PROB[LEVEL]:
        return old_catalan(p)
    if r < OLD_CAT_PROB[LEVEL] + BINARY_PROB[LEVEL]:
        return to_binary(f"{p.problem[2]} en {p.room} ({p.pc})")
    if p.absurd:
        body = random.choice(ABSURD)[1]
        txt = f"{random.choice(INFORMAL_OPEN)}, {body} {random.choice(INFORMAL_END)}"
    elif p.style == "formal":
        txt = (f"{random.choice(OPENERS)} les informo de que {p.problem[1]} "
               f"({p.room}, {p.pc}). {random.choice(CLOSERS)} Atentamente, {p.name}.")
    else:
        txt = f"{random.choice(INFORMAL_OPEN)}, {p.problem[2]} en {p.room} ({p.pc}) {random.choice(INFORMAL_END)}"
    return messy(txt) if LEVEL == 3 else txt


def date_text(d):
    y, m, dd = d.year, d.month, d.day
    fmts = {
        1: [f"{dd:02d}/{m:02d}/{y}"],
        2: [f"{dd:02d}/{m:02d}/{y}", f"{y}/{m:02d}/{dd:02d}", f"{dd:02d}-{m:02d}-{y}",
            f"{m:02d}/{dd:02d}/{y}", f"{dd}.{m}.{y}"],
        3: [f"{dd:02d}/{m:02d}/{y}", f"{y}/{m:02d}/{dd:02d}", f"{m:02d}/{MESES[m - 1]}/{y}",
            f"{dd} de {MESES[m - 1]} de {y}", f"{MESES[m - 1]} {dd}, {y}", f"{dd}/{MESES[m - 1][:3]}/{y % 100}",
            f"{y}{m:02d}{dd:02d}", "ayer", "hoy", "el otro día", f"{MESES[m - 1]}/{dd}/{y}"],
    }
    return random.choice(fmts[LEVEL])


def time_text():
    h, mi = random.randint(8, 21), random.randint(0, 59)
    fmts = [f"{h:02d}:{mi:02d}"]
    if LEVEL >= 2:
        fmts += [f"{h % 12 or 12}:{mi:02d} {'am' if h < 12 else 'pm'}", f"{h}h {mi}min"]
    if LEVEL == 3:
        fmts += ["a la hora del bocata", "por la mañana", "justo antes de que se fuera la luz"]
    return random.choice(fmts)


def short_text(title, p):
    t = title.lower()
    if re.search(r"correu|correo|e-?mail|mail", t): return p.email
    if re.search(r"cognom|apellido|surname", t): return p.last
    if re.search(r"equip|ordinad|\bpc\b|puesto|lloc", t): return p.pc
    if re.search(r"aula|sala|ubicaci|lab", t): return p.room
    if re.search(r"data|fecha|date|dia\b|día", t):
        return date_text(date.today() - timedelta(days=random.randint(0, 60)))
    if re.search(r"hora|time", t): return time_text()
    if re.search(r"descri|detall|explic|comenta|observ|cu[eé]nta|conta", t): return incident_long(p)
    if re.search(r"incid|problema|averia|avería|fallo|motiu|motivo|assumpte|asunto|t[ií]tol|título", t):
        return incident_short(p)
    if re.search(r"nom|nombre|name|alumn|qui |quién|reporta", t): return p.name
    if re.search(r"tel|m[òo]bil|movil|phone", t): return p.phone
    if re.search(r"edat|edad|age|anys|años", t): return str(p.age)
    if re.search(r"ciutat|ciudad|poblaci|city", t): return p.city
    if re.search(r"adre[çc]a|direcci|address", t): return p.address
    if re.search(r"usuari|user|nick", t): return p.first.lower() + str(random.randint(1, 999))
    if re.search(r"curs|clase|grup|grupo", t): return random.choice(["1r DAM", "2n DAW", "1r ASIX", "2n SMX"])
    if re.search(r"num|n[úu]mero|quant|cuant", t): return str(random.randint(1, 100))
    if re.search(r"desc|detall|comenta|observ", t): return incident_long(p)
    return incident_short(p) if LEVEL < 3 or random.random() < 0.6 else random.choice(TROLL_SHORT)


def long_text(title, p):
    return incident_long(p)


# ----------------------------------------------------------------------
# PARSEIG DEL FORMULARI
# ----------------------------------------------------------------------
def parse_form(html):
    """Retorna (títol, preguntes, nº pàgines, fbzx) o None."""
    soup = BeautifulSoup(html, "html.parser")
    m = re.search(r"FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\])\s*;\s*</script>", html, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
        items = data[1][1] or []
        title = data[1][8] or data[3] or "(sin título)"
    except Exception:
        return None
    fbzx_tag = soup.find("input", {"name": "fbzx"})
    fbzx = fbzx_tag["value"] if fbzx_tag else ""

    questions, pages = [], 1
    for it in items:
        qtype = it[3]
        if qtype == 8:
            pages += 1
            continue
        if not it[4]:
            continue
        q = {"title": it[1] or "", "type": qtype, "subs": []}
        for sub in it[4]:
            opts = [o[0] for o in (sub[1] or []) if o[0] and not (len(o) > 4 and o[4] == 1)]
            q["subs"].append({"id": sub[0], "opts": opts})
        questions.append(q)
    return title, questions, pages, fbzx


def build_payload(questions, pages, fbzx, p):
    data, skipped = {}, []
    for q in questions:
        t, title = q["type"], q["title"]
        for s in q["subs"]:
            key = f"entry.{s['id']}"
            if t == 0:
                data[key] = short_text(title, p)
            elif t == 1:
                data[key] = long_text(title, p)
            elif t in (2, 3, 5, 7):
                if s["opts"]:
                    data[key] = random.choice(s["opts"])
            elif t == 4:
                if s["opts"]:
                    data[key] = random.sample(s["opts"], random.randint(1, min(3, len(s["opts"]))))
            elif t == 9:
                d = date.today() - timedelta(days=random.randint(0, 60))
                data[f"{key}_year"], data[f"{key}_month"], data[f"{key}_day"] = d.year, d.month, d.day
            elif t == 10:
                data[f"{key}_hour"], data[f"{key}_minute"] = random.randint(8, 21), random.randint(0, 59)
            else:
                skipped.append(title or f"tipo {t}")
    data["fvv"] = "1"
    data["pageHistory"] = ",".join(str(i) for i in range(pages))
    if fbzx:
        data["fbzx"] = fbzx
    return data, skipped


# ----------------------------------------------------------------------
# TRANSPORT: requests (ràpid) + Playwright (fallback)
# ----------------------------------------------------------------------
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Accept-Language": "ca,es;q=0.9,en;q=0.8"}


def action_url(final_url):
    return re.sub(r"/(viewform|prefill|edit).*$", "/formResponse", final_url.split("?")[0])


def needs_login(url):
    return "accounts.google.com" in url or "ServiceLogin" in url


class Browser:
    """Chromium headless; només s'arrenca si cal (fallback)."""
    def __init__(self):
        self.pw = self.br = self.ctx = None

    def start(self):
        if self.ctx:
            return
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        self.br = self.pw.chromium.launch(headless=True)
        self.ctx = self.br.new_context(user_agent=HEADERS["User-Agent"])

    def get(self, url):
        self.start()
        page = self.ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=45000)
        html, final = page.content(), page.url
        page.close()
        return html, final

    def post(self, url, payload):
        self.start()
        r = self.ctx.request.post(url, data=urlencode(payload, doseq=True),
                                  headers={"Content-Type": "application/x-www-form-urlencoded"})
        return r.status

    def close(self):
        if self.br:
            self.br.close()
            self.pw.stop()


def load_form(url, session, browser):
    """Devuelve (parsed|None, url_final, modo, motivo_error)."""
    try:
        r = session.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        if needs_login(r.url):
            return None, r.url, "requests", "login"
        if r.status_code in (401, 403):
            raise PermissionError(r.status_code)
        parsed = parse_form(r.text)
        if parsed:
            return parsed, r.url, "requests", None
        log("FALLBACK", "no se pudo extraer la estructura -> Chromium", C.YEL)
    except PermissionError as e:
        log("FALLBACK", f"HTTP {e} -> cambiando a Chromium", C.YEL)
    except requests.RequestException as e:
        log("FALLBACK", f"error de red ({e.__class__.__name__}) -> Chromium", C.YEL)
    html, final = browser.get(url)
    if needs_login(final):
        return None, final, "chromium", "login"
    parsed = parse_form(html)
    return parsed, final, "chromium", (None if parsed else "parse")


def submit(post_url, payload, session, browser, mode):
    if mode == "requests":
        r = session.post(post_url, data=payload, headers=HEADERS, timeout=20)
        if r.status_code in (401, 403):
            return browser.post(post_url, payload)
        return r.status_code
    return browser.post(post_url, payload)


# ----------------------------------------------------------------------
# EXECUCIÓ PER ALUMNE
# ----------------------------------------------------------------------
def run_student(name, url, count, delay, color, idx, total, browser):
    student_header(name, color, idx, total, url)
    session = requests.Session()
    parsed, final, mode, err = load_form(url, session, browser)
    if err == "login":
        log("ERROR", "este formulario pide iniciar sesión con Google -> no se puede rellenar", C.RED)
        return 0, 0, True
    if not parsed:
        log("ERROR", "no se pudo leer el formulario", C.RED)
        return 0, count, False
    title, questions, pages, fbzx = parsed
    log("FORM", f"{C.B}{title}{C.R}  ({len(questions)} preguntas, {pages} pág.)  vía {mode}", color)
    post_url = action_url(final)
    ok = fail = 0

    for i in range(1, count + 1):
        p = Persona()
        payload, skipped = build_payload(questions, pages, fbzx, p)
        try:
            status = submit(post_url, payload, session, browser, mode)
        except Exception as e:
            status = f"EXC:{e.__class__.__name__}"
        good = status == 200
        ok += good
        fail += not good
        mark = f"{C.GRN}✔ OK {C.R}" if good else f"{C.RED}✘ {status}{C.R}"
        log("SEND", f"{mark} {bar(i, count, color)}  {p.name}{' 🤡' if p.troll else ''}", C.WHT)
        if i == 1:
            log("MUESTRA", f"{C.D}{incident_long(p)[:WIDTH - 14]}{C.R}", C.D)
            if skipped:
                log("AVISO", f"preguntas no soportadas: {', '.join(skipped)[:48]}", C.YEL)
        time.sleep(delay * random.uniform(0.7, 1.4))
    return ok, fail, False


def main():
    global LEVEL
    ap = argparse.ArgumentParser(description="Automatitzador de Google Forms (troll edition)")
    ap.add_argument("urls", nargs="*", help="URLs directas")
    ap.add_argument("-n", "--count", type=int, help="respuestas por formulario")
    ap.add_argument("-t", "--troll", type=int, choices=[1, 2, 3], help="nivel de trolleo")
    ap.add_argument("-d", "--delay", type=float, default=1.0, help="pausa (s) entre envíos")
    args = ap.parse_args()

    banner()
    if args.urls:
        targets = {f"form{i + 1}": u for i, u in enumerate(args.urls)}
    else:
        targets = dict(FORMS) or ask_urls()
    if not targets:
        sys.exit(f"{C.RED}No hay enlaces.{C.R}")

    count = args.count or ask_int("¿Cuántas respuestas envío?", 5, 1, 500)
    LEVEL = args.troll or ask_level()
    print(f"\n  {C.B}Nivel:{C.R} {LEVEL_NAMES[LEVEL]}   {C.B}Respuestas/form:{C.R} {count}   "
          f"{C.B}Formularios:{C.R} {len(targets)}")

    browser = Browser()
    summary = []
    try:
        for idx, (name, url) in enumerate(targets.items(), 1):
            color = STUDENT_COLORS[(idx - 1) % len(STUDENT_COLORS)]
            ok, fail, login = run_student(name, url, count, args.delay, color, idx, len(targets), browser)
            summary.append((name, ok, fail, color, login))
    except KeyboardInterrupt:
        print(f"\n{C.YEL}Interrumpido por el usuario.{C.R}")
    finally:
        browser.close()

    print("\n" + C.GRN + C.B + "=" * WIDTH)
    print("  RESUMEN".center(WIDTH))
    print("=" * WIDTH + C.R)
    print(f"  {'ALUMNO':<16}{'OK':>6}{'ERR':>6}")
    for name, ok, fail, color, login in summary:
        extra = f"  {C.YEL}(pide login){C.R}" if login else ""
        print(f"  {color}{name:<16}{C.R}{C.GRN}{ok:>6}{C.R}{C.RED}{fail:>6}{C.R}{extra}")
    print(f"  {C.B}{'TOTAL':<16}{sum(s[1] for s in summary):>6}{sum(s[2] for s in summary):>6}{C.R}\n")


if __name__ == "__main__":
    main()