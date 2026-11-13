#!/usr/bin/env python3

import base64
import binascii
import csv
import html
import io
import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date
from xml.sax.saxutils import escape
from urllib.parse import unquote

FITXER_XML = "incidencies.xml"
FITXER_JSON = "incidencies.json"
FITXER_REVISIO = "incidencies_revisio.json"
FITXER_DESCARTADES = "incidencies_descartades.json"
FITXER_ARBRE = "arbre_xml.svg"
ANYS_ANTIGA = 5    # més antiga que això (en anys) -> es guarda per revisar

CAMPS_OBLIGATORIS = ["tipus_equip", "equip", "prioritat", "estat"]       # si la columna existeix
CAMPS_TEXT_CRITICS = ["tipus_equip", "equip", "ubicacio", "departament"]  # il·legible -> es descarta la fila
CAMPS_TEXT_OPCIONALS = ["descripcio", "informador", "tecnic"]             # il·legible -> es buida el camp
CAMPS_UNIFICABLES = ["tipus_equip", "ubicacio", "departament", "informador", "tecnic",
                     "sistema_operatiu", "categoria"]
CAMPS_NOMS_PERSONA = ["informador", "tecnic"]                            # aquí només s'admet 1 lletra de diferència


# ======================================================================
#  Colors i presentació
# ======================================================================
class C:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
    BLUE = "\033[94m"; MAGENTA = "\033[95m"; CYAN = "\033[96m"; GREY = "\033[90m"
    ORANGE = "\033[38;5;208m"


def titol(text):
    linia = "═" * (len(text) + 4)
    print(f"\n{C.CYAN}{C.BOLD}╔{linia}╗\n║  {text}  ║\n╚{linia}╝{C.RESET}")


def subtitol(text):
    print(f"\n{C.BOLD}{C.BLUE}▌ {text}{C.RESET}")


def pas(num, text):
    print(f"\n{C.BOLD}{C.CYAN}[{num}]{C.RESET} {text}")


def error(text):
    sys.exit(f"\n{C.RED}{C.BOLD}Error:{C.RESET} {C.RED}{text}{C.RESET}")


def tallar(text, n=28):
    return text if len(text) <= n else text[:n - 3] + "..."


# ======================================================================
#  Utilitats de text
# ======================================================================
def sense_accents(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t))
                   if unicodedata.category(c) != "Mn")


def clau(t):
    """'Tipus d'Equip ' -> 'tipusdequip' (per comparar sense accents ni símbols)."""
    return re.sub(r"[^a-z0-9]", "", sense_accents(t).lower())


def distancia(a, b):
    """Distància d'edició: inserir, esborrar, canviar o intercanviar 2 lletres = 1 pas."""
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = a[i - 1] != b[j - 1]
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


def semblants(a, b, persona=False):
    """Són dues paraules la mateixa amb una falta d'ortografia?"""
    if min(len(a), len(b)) < 4:
        return a == b
    maxim = 1 if (persona or max(len(a), len(b)) < 8) else 2
    return distancia(a, b) <= maxim


# ======================================================================
#  Noms de columna alternatius -> nom canònic
# ======================================================================
ALIES = {
    "id": ["idincidencia", "incidencia", "numero", "num", "codi", "codigo",
           "ticket", "ref", "referencia", "identificador"],
    "data": ["fecha", "date", "dataincidencia", "fechaincidencia", "datacreacio",
             "fechacreacion", "dataalta", "datainici"],
    "hora": ["time", "horaincidencia"],
    "tipus_equip": ["tipoequipo", "tipus", "tipo", "type", "tipusdispositiu"],
    "equip": ["equipo", "dispositiu", "dispositivo", "device", "nomequip", "aparell"],
    "ubicacio": ["ubicacion", "aula", "lloc", "lugar", "sala", "location", "espai"],
    "departament": ["departamento", "area", "grup", "grupo", "curs", "seccio"],
    "informador": ["reportadopor", "usuari", "usuario", "persona", "reporter",
                   "informant", "comunicatper", "notificatper"],
    "descripcio": ["descripcion", "detall", "detalle", "problema", "description"],
    "prioritat": ["prioridad", "urgencia", "priority", "gravetat"],
    "estat": ["estado", "status", "state", "situacio"],
    "tecnic": ["tecnico", "assignat", "assignada", "asignado", "responsable", "assignatper"],
    "data_resolucio": ["dataresolta", "fecharesolucion", "datatancament", "fechacierre",
                       "dataresolucio", "datafinal", "datafi"],
    # camps que només s'afegeixen amb els formularis tipus Google Forms
    "correu": [], "marca_temps": ["marcatemps"], "sistema_operatiu": [], "categoria": [],
}
CANON = {}
for _camp, _llista in ALIES.items():
    for _alies in _llista + [_camp]:
        CANON[clau(_alies)] = _camp


# Capçaleres llargues tipus Google Forms ("Que tipo de equipo ha sido afectado?"):
# si el nom no és exacte, es busquen paraules clau. L'ordre importa (el primer que coincideix).
PISTES = [
    (("resol", "cierre", "tancament"), "data_resolucio", ("fecha", "data")),
    (("fecha",), "data", ()),
    (("nomdusuari", "correo", "correu", "email", "mail"), "correu", ()),
    (("marcadetemps", "marcatemporal", "timestamp", "sellodetiempo", "marcadetiempo"), "marca_temps", ()),
    (("lugar", "ubicac", "localitz", "aula", "lloc"), "ubicacio", ()),
    (("tipo", "tipus"), "tipus_equip", ("equip", "dispositiv", "aparell")),
    (("etiqueta", "inventari", "numerodeserie"), "equip", ()),
    (("sistemaoperativo", "sistemaoperatiu"), "sistema_operatiu", ()),
    (("categori",), "categoria", ()),
    (("describe", "descri", "problema"), "descripcio", ()),
    (("prioridad", "prioritat", "urgenc"), "prioritat", ()),
    (("estado", "estat"), "estat", ()),
    (("tecnico", "tecnic", "asignado", "assignat", "responsable"), "tecnic", ()),
    (("nombre", "apellid", "cognom", "nomi"), "informador", ()),
]


def camp_conegut(nom):
    """Nom canònic si la columna és reconeguda; sinó None."""
    k = clau(nom)
    if k in CANON:
        return CANON[k]
    k_data = k.startswith(("data", "date"))               # "Data i hora de la incidència"
    for paraules, camp, tambe in PISTES:
        if camp == "data_resolucio":
            if any(p in k for p in paraules) and (k_data or any(t in k for t in tambe)):
                return camp
        elif camp == "data":
            if k_data or any(p in k for p in paraules):
                return camp
        elif any(p in k for p in paraules) and (not tambe or any(t in k for t in tambe)):
            return camp
    return None


def camp_canonic(nom):
    return camp_conegut(nom) or clau(nom) or nom


# ======================================================================
#  Valors de prioritat / estat (sinònims en cat, cast, eng)
# ======================================================================
PRIORITATS_SIN = {
    "Crítica": ["critica", "urgent", "critical", "bloquejant", "moltalta", "muyalta"],
    "Alta": ["alta", "high"],
    "Mitjana": ["mitjana", "mitja", "media", "medio", "medium", "normal"],
    "Baixa": ["baixa", "baja", "low", "minima"],
}
ESTATS_SIN = {
    "Oberta": ["oberta", "abierta", "open", "nova", "nueva", "new", "pendent", "pendiente"],
    "En curs": ["encurs", "enproces", "enprogres", "enproceso", "enprogreso",
                "inprogress", "assignada", "asignada", "processant"],
    "Resolta": ["resolta", "resuelta", "resolved", "solucionada", "feta", "hecha"],
    "Tancada": ["tancada", "cerrada", "closed", "closa"],
}
PRIORITATS = list(PRIORITATS_SIN)
ESTATS = list(ESTATS_SIN)
LOOKUP_PRIORITAT = {clau(s): k for k, v in PRIORITATS_SIN.items() for s in v}
LOOKUP_ESTAT = {clau(s): k for k, v in ESTATS_SIN.items() for s in v}

COLOR_PRIORITAT = {"Crítica": C.RED, "Alta": C.MAGENTA, "Mitjana": C.YELLOW, "Baixa": C.GREEN}
COLOR_ESTAT = {"Oberta": C.RED, "En curs": C.YELLOW, "Resolta": C.GREEN, "Tancada": C.GREY}
DIES_SETMANA = ["Dilluns", "Dimarts", "Dimecres", "Dijous", "Divendres", "Dissabte", "Diumenge"]

VALORS_BUITS = {"", "-", "--", "na", "n/a", "nd", "null", "none", "nan", "pendent", "pendiente", "no"}
BUITS_TOTAL = {"", "na", "nd", "null", "none", "nan", "undefined", "buit", "vacio"}


# ======================================================================
#  Dates: acceptem pràcticament qualsevol format habitual
# ======================================================================
#   2025/03/05  2025-03-05  2025.03.05  20250305
#   05/03/2025  05-03-2025  05.03.2025  5/3/25  03/25/2025 (si el dia no hi cap)
#   5-març-2025  5/mar/25  5 de març de 2025  5 marzo 2025  March 5, 2025
#   5-març  5/març  (sense any: s'agafa l'any actual)
#   qualsevol d'aquestes amb hora darrere: 2025-03-05 14:30, 2025-03-05T14:30:00
MESOS = {"gen": 1, "ene": 1, "jan": 1, "feb": 2, "mar": 3, "abr": 4, "apr": 4,
         "mai": 5, "mag": 5, "may": 5, "jun": 6, "jul": 7, "ago": 8, "aug": 8,
         "set": 9, "sep": 9, "oct": 10, "nov": 11, "des": 12, "dec": 12, "dic": 12}


def any_curt(y):
    return 2000 + y if y < 70 else 1900 + y


def parse_data(text):
    """Converteix text en date. Llança ValueError si no ho aconsegueix."""
    t = sense_accents(str(text).strip().lower())
    t = re.sub(r"[t\s]+\d{1,2}[:.]\d{2}.*$", "", t)          # treu l'hora
    t = t.replace("d'", " ")
    t = re.sub(r"\b(de|del|el|dia)\b", " ", t)
    t = t.replace(",", " ")
    parts = [p for p in re.split(r"[\s/\-.]+", t) if p]
    nums = [p for p in parts if p.isdigit()]
    noms = [p for p in parts if p.isalpha()]
    if not parts or len(nums) + len(noms) != len(parts):
        raise ValueError("format desconegut")

    cands = []   # llista de (any, mes, dia); any=None -> any actual
    if noms:                                           # amb nom de mes
        if len(noms) != 1 or noms[0][:3] not in MESOS:
            raise ValueError("mes desconegut")
        mes = MESOS[noms[0][:3]]
        if len(nums) == 2:
            a, b = nums
            if len(a) == 4:
                cands = [(int(a), mes, int(b))]
            elif len(b) == 4:
                cands = [(int(b), mes, int(a))]
            else:
                cands = [(any_curt(int(b)), mes, int(a))]
        elif len(nums) == 1:
            cands = [(None, mes, int(nums[0]))]
    elif len(nums) == 3:                               # tot numèric
        a, b, c = nums
        if len(a) == 4:                                # AAAA/MM/DD
            cands = [(int(a), int(b), int(c)), (int(a), int(c), int(b))]
        elif len(c) in (2, 4):                         # DD/MM/AAAA (i si no, MM/DD/AAAA)
            y = int(c) if len(c) == 4 else any_curt(int(c))
            cands = [(y, int(b), int(a)), (y, int(a), int(b))]
    elif len(nums) == 2:                               # DD/MM sense any
        a, b = nums
        cands = [(None, int(b), int(a)), (None, int(a), int(b))]
    elif len(nums) == 1 and len(nums[0]) == 8:         # 20250305 o 05032025
        p = nums[0]
        cands = [(int(p[:4]), int(p[4:6]), int(p[6:])), (int(p[4:]), int(p[2:4]), int(p[:2]))]

    avui = date.today()
    for any_, mes, dia in cands:
        try:
            if any_ is None:
                d = date(avui.year, mes, dia)
                if d > avui:
                    d = date(avui.year - 1, mes, dia)
                return d
            return date(any_, mes, dia)
        except ValueError:
            continue
    raise ValueError("data impossible")


# ======================================================================
#  1. Triar fitxer
# ======================================================================
def neteja_ruta(r):
    return os.path.expanduser(r.strip().strip("'\""))


def triar_fitxer():
    if len(sys.argv) > 1:
        ruta = neteja_ruta(" ".join(sys.argv[1:]))
        if not os.path.isfile(ruta):
            error(f"no trobo el fitxer '{ruta}'")
        return ruta

    trobats = sorted(f for f in os.listdir(".") if f.lower().endswith((".csv", ".xml")))
    print(f"\n{C.BOLD}Fitxers trobats en aquesta carpeta:{C.RESET}")
    if trobats:
        for n, f in enumerate(trobats, 1):
            print(f"  {C.YELLOW}{n}){C.RESET} {f}")
        print(f"  {C.DIM}(o escriu/arrossega aquí la ruta d'un altre fitxer){C.RESET}")
    else:
        print(f"  {C.DIM}(cap .csv ni .xml; escriu o arrossega la ruta del fitxer){C.RESET}")

    while True:
        resposta = input(f"\n{C.BOLD}Quin fitxer vols processar?{C.RESET} "
                         f"{'[Enter = 1] ' if trobats else ''}").strip()
        if not resposta and trobats:
            return trobats[0]
        if resposta.isdigit() and 1 <= int(resposta) <= len(trobats):
            return trobats[int(resposta) - 1]
        ruta = neteja_ruta(resposta)
        if os.path.isfile(ruta):
            return ruta
        print(f"  {C.RED}No trobo aquest fitxer, torna-ho a provar.{C.RESET}")


# ======================================================================
#  2. CSV -> XML
# ======================================================================
def llegir_csv(ruta):
    text = None
    for enc in ("utf-8-sig", "cp1252"):
        try:
            with open(ruta, encoding=enc, newline="") as f:
                text = f.read()
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        error("no puc llegir la codificació del CSV")
    try:
        dialecte = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialecte = csv.excel
    # Es guarden també les files "buides" (,,,,,) per poder-les comptar i apartar
    files = [f for f in csv.reader(io.StringIO(text, newline=""), dialecte) if f]
    if len(files) < 2:
        error("el CSV està buit o només té capçalera")
    return [h.strip() for h in files[0]], files[1:]


def xml_segur(s):
    """Treu els caràcters que l'XML no permet (p. ex. NUL), que trencarien el fitxer."""
    return re.sub("[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]", " ", s)


def nom_xml(nom, i):
    n = re.sub(r"[^\w.-]", "_", xml_segur(nom).strip())
    if not n:
        return f"camp{i}"
    return n if (n[0].isalpha() or n[0] == "_") else "_" + n


def csv_a_xml(ruta_csv, ruta_xml):
    capcaleres, files = llegir_csv(ruta_csv)
    noms, vistos = [], Counter()
    for i, h in enumerate(capcaleres, 1):
        n = camp_conegut(h) or nom_xml(h, i)[:40]          # data, ubicacio... (o el nom original)
        vistos[n] += 1
        noms.append(n if vistos[n] == 1 else f"{n}_{vistos[n]}")
    idx_id = next((i for i, h in enumerate(capcaleres) if camp_canonic(h) == "id"), None)

    arrel = ET.Element("incidencies")
    for n, fila in enumerate(files, 1):
        fila = (fila + [""] * len(noms))[:len(noms)]       # files curtes/llargues
        valor_id = xml_segur(fila[idx_id]).strip() if idx_id is not None else str(n)
        inc = ET.SubElement(arrel, "incidencia", id=valor_id)
        for i, (nom, valor) in enumerate(zip(noms, fila)):
            if i != idx_id:
                ET.SubElement(inc, nom).text = xml_segur(valor).strip()

    arbre = ET.ElementTree(arrel)
    ET.indent(arbre, space="  ")
    arbre.write(ruta_xml, encoding="utf-8", xml_declaration=True)
    return len(files)


# ======================================================================
#  2b. Diagrama de l'arbre XML (terminal + SVG)
# ======================================================================
class Node:
    def __init__(self, tag, n=1, tipus="element"):
        self.tag, self.n, self.tipus, self.fills = tag, n, tipus, []


def construeix(elems, tag):
    """Estructura de l'XML: un node per cada tipus d'etiqueta (sense repetir els germans)."""
    node = Node(tag, len(elems))
    atributs = []
    for e in elems:
        for a in e.attrib:
            if a not in atributs:
                atributs.append(a)
    node.fills = [Node("@" + a, tipus="atribut") for a in atributs]
    grups = {}
    for e in elems:
        for fill in e:
            grups.setdefault(fill.tag, []).append(fill)
    node.fills += [construeix(v, k) for k, v in grups.items()]
    return node


def arbre_de_xml(ruta_xml):
    try:
        arrel = ET.parse(ruta_xml).getroot()
    except (ET.ParseError, OSError):
        return None
    node = construeix([arrel], arrel.tag)
    node.tipus = "arrel"
    return node


def etiqueta_node(n):
    return n.tag + (f"  ×{n.n}" if n.fills and n.n > 1 else "")


def imprimeix_arbre(n, prefix="", ultim=True, arrel=True):
    color = C.BOLD + C.CYAN if arrel else (C.YELLOW if n.tipus == "atribut" else "")
    if arrel:
        print(f"  {color}{etiqueta_node(n)}{C.RESET}")
        nou = "  "
    else:
        print(f"{prefix}{C.GREY}{'└── ' if ultim else '├── '}{C.RESET}{color}{etiqueta_node(n)}{C.RESET}")
        nou = prefix + ("    " if ultim else f"{C.GREY}│{C.RESET}   ")
    for i, f in enumerate(n.fills):
        imprimeix_arbre(f, nou, i == len(n.fills) - 1, False)


BOX_H, V_GAP, H_GAP, MARGE = 46, 64, 16, 30


def mida_node(n):
    n.bw = max(84, len(n.tag) * 9.6 + 30)
    n.sub = max(n.bw + H_GAP, sum(mida_node(f) for f in n.fills))
    return n.sub


def posa_node(n, x0, nivell):
    n.x = x0 + n.sub / 2
    n.y = 70 + nivell * (BOX_H + V_GAP)
    cursor = x0 + (n.sub - sum(f.sub for f in n.fills)) / 2
    fondaria = nivell
    for f in n.fills:
        fondaria = max(fondaria, posa_node(f, cursor, nivell + 1))
        cursor += f.sub
    return fondaria


def dibuixa_node(n, linies, caixes):
    if n.fills:
        yb, ym = n.y + BOX_H, n.y + BOX_H + V_GAP / 2
        xs = [f.x for f in n.fills]
        linies.append(f'<path d="M{n.x:.1f},{yb} V{ym:.1f} M{min(xs):.1f},{ym:.1f} H{max(xs):.1f}'
                      + "".join(f" M{f.x:.1f},{ym:.1f} V{f.y:.1f}" for f in n.fills) + '"/>')
    estil = {"arrel": ("#5b2fc0", "#3b1d8a", "#ffffff", ""),
             "element": ("#f1ecff", "#5b2fc0", "#1f1147", ""),
             "atribut": ("#fff6dd", "#d19a00", "#4a3500", ' stroke-dasharray="6 4"')}[n.tipus]
    fons, vora, text, dash = estil
    x, y = n.x - n.bw / 2, n.y
    caixes.append(f'<rect x="{x:.1f}" y="{y}" width="{n.bw:.1f}" height="{BOX_H}" rx="7" fill="{fons}" '
                  f'stroke="{vora}" stroke-width="2"{dash}/>')
    if n.fills and n.n > 1:
        caixes.append(f'<text x="{n.x:.1f}" y="{y + 20}" fill="{text}" font-size="16" font-weight="bold" '
                      f'text-anchor="middle">{escape(n.tag)}</text>')
        caixes.append(f'<text x="{n.x:.1f}" y="{y + 37}" fill="{text}" font-size="12" '
                      f'text-anchor="middle">× {n.n} elements</text>')
    else:
        caixes.append(f'<text x="{n.x:.1f}" y="{y + 29}" fill="{text}" font-size="16" '
                      f'text-anchor="middle">{escape(n.tag)}</text>')
    for f in n.fills:
        dibuixa_node(f, linies, caixes)


def escriu_svg(arbre, ruta, titol_fitxer):
    mida_node(arbre)
    fondaria = posa_node(arbre, MARGE, 0)
    ample = arbre.sub + 2 * MARGE
    alt = 70 + (fondaria + 1) * (BOX_H + V_GAP) + 20
    linies, caixes = [], []
    dibuixa_node(arbre, linies, caixes)
    llegenda_x = MARGE
    llegenda = (
        f'<rect x="{llegenda_x}" y="{alt - 34}" width="22" height="16" rx="3" fill="#5b2fc0"/>'
        f'<text x="{llegenda_x + 30}" y="{alt - 21}" font-size="13" fill="#555">arrel</text>'
        f'<rect x="{llegenda_x + 90}" y="{alt - 34}" width="22" height="16" rx="3" fill="#f1ecff" stroke="#5b2fc0" stroke-width="2"/>'
        f'<text x="{llegenda_x + 120}" y="{alt - 21}" font-size="13" fill="#555">element</text>'
        f'<rect x="{llegenda_x + 205}" y="{alt - 34}" width="22" height="16" rx="3" fill="#fff6dd" stroke="#d19a00" stroke-width="2" stroke-dasharray="4 3"/>'
        f'<text x="{llegenda_x + 235}" y="{alt - 21}" font-size="13" fill="#555">atribut</text>')
    alt += 20
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ample:.0f} {alt}" '
           f'font-family="DejaVu Sans, Arial, sans-serif">\n'
           f'<rect width="100%" height="100%" fill="#ffffff"/>\n'
           f'<text x="{MARGE}" y="38" font-size="24" font-weight="bold" fill="#5b2fc0">'
           f'ESTRUCTURA: Arbre XML de {escape(titol_fitxer)}</text>\n'
           f'<g fill="none" stroke="#3b2a8c" stroke-width="2">{"".join(linies)}</g>\n'
           + "\n".join(caixes) + "\n" + llegenda + "\n</svg>\n")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(svg)


def mostrar_arbre(ruta_xml):
    arbre = arbre_de_xml(ruta_xml)
    if arbre is None:
        return
    subtitol(f"Arbre de {os.path.basename(ruta_xml)}")
    imprimeix_arbre(arbre)
    escriu_svg(arbre, FITXER_ARBRE, os.path.basename(ruta_xml))
    print(f"\n  {C.GREEN}Diagrama dibuixat a {C.BOLD}{FITXER_ARBRE}{C.RESET}"
          f"{C.GREEN} (obre'l amb Firefox/Chrome){C.RESET}")


# ======================================================================
#  3a. Llegir XML
# ======================================================================
def llegir_xml(ruta):
    try:
        arrel = ET.parse(ruta).getroot()
    except ET.ParseError as e:
        error(f"XML mal format: {e}")
    registres = []
    for n, elem in enumerate(arrel, 1):
        r = {camp_canonic(k): v.strip() for k, v in elem.attrib.items()}
        for fill in elem:
            r[camp_canonic(fill.tag)] = (fill.text or "").strip()
        r["_fila"] = n                                     # per poder dir "fila 57"
        registres.append(r)
    if not registres:
        error("l'XML no conté cap incidència")
    if not any("id" in r for r in registres):              # sense columna ID: numerem
        for r in registres:
            r["id"] = str(r["_fila"])
    return registres


# ======================================================================
#  3b. Reparar text: corrupte, binari, hexadecimal, base64
# ======================================================================
def anota(correccions, camp, abans, despres, motiu, trivial=None):
    """Apunta una correcció. 'trivial' = només canvia majúscules/espais/guions."""
    if trivial is None:
        trivial = clau(abans) == clau(despres) and clau(abans) != ""
    correccions.append((camp, abans, despres, motiu, trivial))


def repara_mojibake(s):
    """'InformÃ tica' -> 'Informàtica' (UTF-8 llegit com si fos Windows-1252/Latin-1)."""
    if not re.search(r"[ÃÂ][\u0080-\u00ff\u2018-\u203a]|â€", s):
        return s
    for enc in ("cp1252", "latin-1"):
        try:
            return s.encode(enc).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return s


def neteja_text(s):
    s = html.unescape(s)                                   # &amp; &#39;
    s = repara_mojibake(s)
    if re.search(r"%[0-9A-Fa-f]{2}", s):
        s = unquote(s)                                     # Aula%201
    s = unicodedata.normalize("NFC", s)
    s = "".join(" " if unicodedata.category(c) == "Cc" else c for c in s)   # \x00, tabuladors...
    s = "".join(c for c in s if unicodedata.category(c) not in ("Cf", "Co", "Cs"))
    return re.sub(r" {2,}", " ", s).strip()


def es_imprimible(t):
    if len(t) < 2 or not all(c.isprintable() for c in t):
        return False
    return sum(c.isalnum() or c in " -'.,/·:" for c in t) / len(t) >= 0.9


def octets_a_text(octets):
    try:
        return octets.decode("utf-8")
    except UnicodeDecodeError:
        return octets.decode("latin-1")


def descodifica(s, camp=""):
    """Si el text és binari, hexadecimal o base64 d'un text, el converteix.
    Retorna (text, tipus) o None."""
    t = s.strip()
    if len(t) < 6:
        return None
    # binari: 01001000 01101111 ...
    b = re.sub(r"[\s,]", "", t)
    if re.fullmatch(r"[01]{16,}", b) and len(b) % 8 == 0:
        txt = octets_a_text(bytes(int(b[i:i + 8], 2) for i in range(0, len(b), 8)))
        if es_imprimible(txt):
            return txt, "binari"
    # hexadecimal: 48 6f 6c 61  /  0x48 0x6f  /  \x48\x6f  /  486f6c61
    h = re.sub(r"0x|\\x|[\s,:;-]", "", t, flags=re.I)
    grups = re.findall(r"[0-9a-fA-F]{2}(?=[\s,:;-]|$)", t) if re.search(r"[\s,:;-]", t) else []
    segur = (re.search(r"[a-fA-F]", h) or len(h) >= 12 or len(grups) >= 4
             or t.lower().startswith(("0x", "\\x")))
    if re.fullmatch(r"[0-9a-fA-F]{6,}", h) and len(h) % 2 == 0 and segur:
        txt = octets_a_text(bytes.fromhex(h))
        if es_imprimible(txt):
            return txt, "hexadecimal"
    # base64: SG9sYSBtb24=
    if (camp not in ("data", "data_resolucio", "hora") and len(t) >= 12
            and re.search(r"[A-Za-z]", t) and re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", t)
            and len(t) % 4 == 0):
        try:
            txt = octets_a_text(base64.b64decode(t, validate=True))
        except (binascii.Error, ValueError):
            return None
        if es_imprimible(txt):
            return txt, "base64"
    return None


TECLAT = ["asdf", "sdfg", "dfgh", "fghj", "ghjk", "hjkl", "qwer", "wert", "erty", "zxcv", "xcvb", "cvbn", "vbnm"]


def es_illegible(v, camp):
    """Detecta text sense sentit: símbols, repeticions, teclejat a l'atzar..."""
    if not v:
        return False
    if "\ufffd" in v:
        return True
    simbols = sum(not (c.isalnum() or c in " -_'.,/·()ºª&+:") for c in v)
    if simbols / len(v) > 0.3:
        return True
    if camp == "equip":                                    # codis tipus PC-01: no mirem més
        return len(v) > 30                                 # una etiqueta no té 300 xifres
    low = sense_accents(v).lower()
    if len(v) >= 5 and not any(c.isalpha() for c in v):    # només xifres
        return True
    if re.search(r"(.)\1{4,}", low):                       # xxxxx
        return True
    if len(low) >= 6 and re.fullmatch(r"(.{2,3})\1+", low):   # asdasd, hjhjhj
        return True
    if re.fullmatch(r"[0-9a-f]{6,}", low) and re.search(r"\d", low):   # 4a8f3c9d
        return True
    if any(p in low for p in TECLAT):                      # asdfgh
        return True
    return any(not re.search(r"[aeiouy]", w) for w in re.findall(r"[a-z]{5,}", low))


def reparar_registre(r, correccions):
    for camp in list(r):
        if camp.startswith("_") or camp == "id":
            continue
        original = r[camp]
        v = neteja_text(original)
        dec = descodifica(v, camp)
        if dec:
            v = neteja_text(dec[0])
            anota(correccions, camp, original, v, f"descodificat ({dec[1]})", trivial=False)
        elif re.sub(r"\s+", "", sense_accents(original)) != re.sub(r"\s+", "", sense_accents(v)):
            anota(correccions, camp, original, v, "text corrupte reparat", trivial=False)
        r[camp] = v
        if camp in CAMPS_TEXT_CRITICS + CAMPS_TEXT_OPCIONALS and es_illegible(v, camp):
            if camp in CAMPS_TEXT_CRITICS:
                r["_error"] = f"text il·legible a '{camp}' ({tallar(v, 20)})"
            else:
                anota(correccions, camp, v, "", "text il·legible eliminat", trivial=False)
                r[camp] = ""


# ======================================================================
#  3c. Unificar valors mal escrits (aules, noms, tipus d'equip...)
# ======================================================================
def forma(camp, v):
    """Si tot és MAJÚSCULES o minúscules, ho posa bé."""
    if camp == "equip":
        return v.upper()
    if v.isupper() or v.islower():
        return v.title() if camp in CAMPS_NOMS_PERSONA else v.capitalize()
    return v


def clau_difusa(v):
    """'Aula  1' -> ('aula', (1,));  'Aula 01' -> ('aula', (1,)).  Els números han de ser iguals."""
    s = sense_accents(v).lower()
    return re.sub(r"[^a-z]", "", s), tuple(int(x) for x in re.findall(r"\d+", s))


def unificar_camp(registres, camp, correccions):
    persona = camp in CAMPS_NOMS_PERSONA
    for r in registres:
        if r.get(camp):
            nou = forma(camp, r[camp])
            if nou != r[camp]:
                anota(correccions, camp, r[camp], nou, "majúscules", trivial=True)
                r[camp] = nou

    comptador = Counter(r[camp] for r in registres if r.get(camp) and "_error" not in r)
    canon, mapa = [], {}                     # canon: [(valor, lletres, números, vegades)]
    for valor, n in comptador.most_common():               # de més a menys freqüent
        alfa, nums = clau_difusa(valor)
        trobat = None
        for c_valor, c_alfa, c_nums, c_n in canon:
            if nums != c_nums:
                continue
            mateixa = alfa == c_alfa
            if mateixa or (camp != "equip" and c_n > n and semblants(alfa, c_alfa, persona)):
                trobat = c_valor
                break
        if trobat is None:
            canon.append((valor, alfa, nums, n))
            mapa[valor] = valor
        else:
            mapa[valor] = trobat

    for r in registres:
        v = r.get(camp)
        if v and mapa.get(v, v) != v:
            anota(correccions, camp, v, mapa[v], "unificat amb la forma més habitual")
            r[camp] = mapa[v]


def canonitza_enum(registres, camp, taula, correccions):
    """Prioritat / estat: sinònims, majúscules i petites faltes -> valor oficial."""
    claus = list(taula)
    for r in registres:
        v = r.get(camp)
        if not v or "_error" in r:
            continue
        k = clau(v)
        canon = taula.get(k)
        if canon is None and len(k) >= 4:
            propers = sorted((distancia(k, c), c) for c in claus if semblants(k, c))
            if propers and (len(propers) == 1 or propers[0][0] < propers[1][0]
                            or taula[propers[0][1]] == taula[propers[1][1]]):
                canon = taula[propers[0][1]]
        if canon and canon != v:
            anota(correccions, camp, v, canon, "valor oficial")
            r[camp] = canon


# ======================================================================
#  3d. Validar: errors, "per revisar" (dates sospitoses) i vàlides
# ======================================================================
def limit_antiguitat(avui):
    try:
        return avui.replace(year=avui.year - ANYS_ANTIGA)
    except ValueError:                      # 29 de febrer
        return avui.replace(year=avui.year - ANYS_ANTIGA, day=28)


def es_buida(r):
    # Google Forms sempre omple la marca de temps i el correu: no compten com a dades
    return all(clau(v) in BUITS_TOTAL for k, v in r.items()
               if k not in ("id", "_fila", "marca_temps", "correu"))


def normalitza(raw, columnes):
    """Retorna (registre, motiu_error, revisio).
    - error  -> la fila es descarta (motiu_error és el text)
    - revisio -> (tipus, explicació) si és vàlida però sospitosa; sinó None"""
    r = dict(raw)
    avui = date.today()
    sospites = []                                    # [(tipus, explicació)]
    if r.get("_error"):
        return None, r["_error"], None
    if not r.get("id"):
        return None, "sense ID", None
    for camp in CAMPS_OBLIGATORIS:
        if camp in columnes and not r.get(camp):
            return None, f"falta el camp '{camp}'", None

    try:
        d = parse_data(r.get("data", ""))
    except ValueError:
        return None, f"data il·legible ({r.get('data') or 'buida'})", None
    r["data"] = d.isoformat()
    if d > avui:
        sospites.append(("futura",
                         f"La data ({d.isoformat()}) és posterior a avui ({avui.isoformat()}): "
                         f"encara no ha passat, potser s'ha escrit malament."))
    elif d < limit_antiguitat(avui):
        anys = (avui - d).days // 365
        sospites.append(("antiga",
                         f"La incidència és de fa {anys} anys (el límit és {ANYS_ANTIGA}): "
                         f"és molt antiga i potser ja no té sentit."))

    for camp, taula in (("prioritat", LOOKUP_PRIORITAT), ("estat", LOOKUP_ESTAT)):
        if camp in columnes:
            valor = taula.get(clau(r[camp]))
            if not valor:
                return None, f"{camp} desconeguda ({tallar(r[camp], 25)})", None
            r[camp] = valor

    dr = r.get("data_resolucio", "")
    if clau(dr) in {clau(v) for v in VALORS_BUITS}:
        r["data_resolucio"] = ""
    else:
        try:
            dres = parse_data(dr)
        except ValueError:
            return None, f"data de resolució il·legible ({dr})", None
        if dres < d:
            return None, "resolta abans de ser creada", None
        if dres > avui:
            sospites.append(("futura",
                             f"La data de resolució ({dres.isoformat()}) és futura: "
                             f"una incidència no es pot resoldre en el futur."))
        r["data_resolucio"] = dres.isoformat()

    if sospites:
        tipus = "futura" if any(t == "futura" for t, _ in sospites) else "antiga"
        return r, None, (tipus, " ".join(text for _, text in sospites))
    return r, None, None


def netejar(registres):
    """Retorna (vàlides, per_revisar, descartades, buides, correccions, rars, columnes)."""
    columnes = set().union(*(r.keys() for r in registres)) - {"_fila"}
    buides = [r for r in registres if es_buida(r)]
    actius = [r for r in registres if not es_buida(r)]
    correccions = []

    for r in actius:
        reparar_registre(r, correccions)
    for camp in CAMPS_UNIFICABLES + ["equip"]:
        if camp in columnes:
            unificar_camp(actius, camp, correccions)
    canonitza_enum(actius, "prioritat", LOOKUP_PRIORITAT, correccions)
    canonitza_enum(actius, "estat", LOOKUP_ESTAT, correccions)

    rars = {}
    if len(actius) >= 30:                    # valors que només surten 1 vegada: sospitosos
        for camp in ("tipus_equip", "ubicacio", "departament"):
            c = Counter(r[camp] for r in actius if r.get(camp) and "_error" not in r)
            if len(c) > 3:
                rars[camp] = sorted(v for v, n in c.items() if n == 1)

    valides, revisio, descartades, ids = [], [], [], set()
    for raw in actius:
        r, motiu, rev = normalitza(raw, columnes)
        if r and r["id"] in ids:
            r, motiu = None, "ID duplicat"
        if not r:
            descartades.append((raw, motiu))
            continue
        ids.add(r["id"])
        fila = r.pop("_fila", None)
        r.pop("_error", None)
        if rev:
            r["data_original"] = raw.get("data", "")
            r["fila"] = fila
            r["tipus_revisio"], r["motiu_revisio"] = rev
            revisio.append(r)
        else:
            valides.append(r)
    return valides, revisio, descartades, buides, correccions, {k: v for k, v in rars.items() if v}, columnes


# ======================================================================
#  4. Informes per pantalla
# ======================================================================
def etiqueta(raw):
    if raw.get("id") and raw["id"] != str(raw.get("_fila")):
        return f"#{raw['id'][:8]} (fila {raw.get('_fila', '?')})"
    return f"fila {raw.get('_fila', '?')}"


def mostrar_correccions(correccions, rars):
    subtitol(f"Correccions automàtiques: {len(correccions)}")
    if not correccions:
        print(f"  {C.GREEN}Cap dada ha calgut arreglar.{C.RESET}")
    else:
        reals = [c for c in correccions if not c[4]]
        triv = len(correccions) - len(reals)
        print(f"  {C.DIM}{triv} valors només tenien majúscules/espais/guions diferents "
              f"(arreglats sense avisar).{C.RESET}")
        grups = Counter((camp, abans, despres, motiu) for camp, abans, despres, motiu, t in reals)
        for (camp, abans, despres, motiu), n in grups.most_common(40):
            destí = f"{C.GREEN}{tallar(despres)!r}{C.RESET}" if despres else f"{C.RED}(buit){C.RESET}"
            vegades = f" {n}×" if n > 1 else ""
            print(f"  {C.GREY}{camp:<12}{C.RESET} {C.YELLOW}{tallar(abans)!r}{C.RESET} → {destí} "
                  f"{C.DIM}[{motiu}]{vegades}{C.RESET}")
        if len(grups) > 40:
            print(f"  {C.DIM}... i {len(grups) - 40} correccions diferents més{C.RESET}")
    for camp, valors in rars.items():
        print(f"  {C.ORANGE}⚠ {camp}: valors que només surten 1 vegada (revisa'ls a mà):{C.RESET} "
              f"{C.DIM}{', '.join(tallar(v, 22) for v in valors[:10])}"
              f"{' ...' if len(valors) > 10 else ''}{C.RESET}")


def mostrar_descartades(descartades):
    subtitol(f"Dades descartades (errors): {len(descartades)}")
    if not descartades:
        print(f"  {C.GREEN}Cap incidència errònia.{C.RESET}")
        return
    for raw, motiu in descartades[:20]:
        print(f"  {C.GREY}{etiqueta(raw):<22}{C.RESET} {C.RED}{motiu}{C.RESET}")
    if len(descartades) > 20:
        print(f"  {C.DIM}... i {len(descartades) - 20} més (totes són al fitxer){C.RESET}")


COLOR_REVISIO = {"futura": C.MAGENTA, "antiga": C.ORANGE}
ETIQUETA_REVISIO = {"futura": "DATA FUTURA", "antiga": "MOLT ANTIGA"}


def mostrar_revisio(revisio):
    subtitol(f"Per revisar: {len(revisio)}")
    if not revisio:
        print(f"  {C.GREEN}Cap incidència sospitosa (ni futures ni de fa més de "
              f"{ANYS_ANTIGA} anys).{C.RESET}")
        return
    print(f"  {C.DIM}Això no són errors segurs, però són estranyes. NO entren a les "
          f"estadístiques\n  ni a {FITXER_JSON}: es guarden a part a {FITXER_REVISIO} "
          f"perquè algú les repassi.{C.RESET}")
    print(f"  Llegenda: {C.MAGENTA}■ data futura{C.RESET}    "
          f"{C.ORANGE}■ de fa més de {ANYS_ANTIGA} anys{C.RESET}")
    for tipus in ("futura", "antiga"):
        grup = [r for r in revisio if r["tipus_revisio"] == tipus]
        color = COLOR_REVISIO[tipus]
        for r in grup[:8]:
            print(f"\n  {color}{C.BOLD}▌ #{r['id'][:8]:<8} {ETIQUETA_REVISIO[tipus]}{C.RESET}  "
                  f"{r['data_original']:<14} {C.DIM}{r.get('equip', '')} · "
                  f"{r.get('ubicacio', '')}{C.RESET}")
            print(f"    {color}↳ {r['motiu_revisio']}{C.RESET}")
        if len(grup) > 8:
            print(f"\n  {C.DIM}... i {len(grup) - 8} més del mateix tipus "
                  f"(tots són al fitxer){C.RESET}")


def mostrar_buides(buides):
    titol("FILES BUIDES (apartades al final)")
    if not buides:
        print(f"\n  {C.GREEN}Cap fila buida.{C.RESET}")
        return
    files = [str(b["_fila"]) for b in buides]
    print(f"\n  {C.GREY}{len(buides)} files sense cap dada (només tenien l'ID o res). "
          f"No s'han tingut en compte.{C.RESET}")
    print(f"  {C.GREY}Files: {', '.join(files[:40])}{' ...' if len(files) > 40 else ''}{C.RESET}")


def mostrar_resum(total, valides, revisio, descartades, buides, correccions):
    titol("RESUM FINAL")
    reals = sum(1 for c in correccions if not c[4])
    print(f"""
  Files llegides ........... {C.BOLD}{total}{C.RESET}
  {C.GREEN}✔ Vàlides{C.RESET} ................. {C.BOLD}{len(valides)}{C.RESET}   {C.DIM}→ {FITXER_JSON}{C.RESET}
  {C.ORANGE}⚠ Per revisar{C.RESET} ............ {C.BOLD}{len(revisio)}{C.RESET}   {C.DIM}→ {FITXER_REVISIO}{C.RESET}
  {C.RED}✖ Descartades{C.RESET} ........... {C.BOLD}{len(descartades)}{C.RESET}   {C.DIM}→ {FITXER_DESCARTADES}{C.RESET}
  {C.GREY}○ Buides{C.RESET} ................. {C.BOLD}{len(buides)}{C.RESET}   {C.DIM}→ {FITXER_DESCARTADES}{C.RESET}
  {C.YELLOW}✎ Dades reparades{C.RESET} ....... {C.BOLD}{reals}{C.RESET}   {C.DIM}(+ {len(correccions) - reals} de format){C.RESET}""")


# ======================================================================
#  5. Estadístiques
# ======================================================================
def barres(comptador, colors=None, ordre=None, amplada=30):
    total = sum(comptador.values())
    if not total:
        return
    claus = ordre or [k for k, _ in comptador.most_common()]
    maxim = max(comptador.values())
    ample = max(len(str(k)) for k in claus)
    for k in claus:
        n = comptador.get(k, 0)
        color = (colors or {}).get(k, C.CYAN)
        print(f"  {str(k):<{ample}} {color}{'█' * round(n / maxim * amplada)}{C.RESET} "
              f"{C.BOLD}{n}{C.RESET} {C.DIM}({n / total * 100:.1f}%){C.RESET}")


def seccio(incs, camp, text, colors=None, ordre=None, top=None):
    valors = [i[camp] for i in incs if i.get(camp)]
    if not valors:
        return
    subtitol(text)
    c = Counter(valors)
    if top:
        c = Counter(dict(c.most_common(top)))
    barres(c, colors, ordre)


def dies_resolucio(i):
    if i.get("data_resolucio"):
        return (date.fromisoformat(i["data_resolucio"]) - date.fromisoformat(i["data"])).days
    return None


def mostrar_estadistiques(incs):
    titol("ESTADÍSTIQUES")
    dates = sorted(i["data"] for i in incs)
    print(f"\n  Incidències vàlides: {C.BOLD}{C.GREEN}{len(incs)}{C.RESET}"
          f"   Període: {C.BOLD}{dates[0]}{C.RESET} → {C.BOLD}{dates[-1]}{C.RESET}")

    seccio(incs, "tipus_equip", "Per tipus d'equip")
    seccio(incs, "prioritat", "Per prioritat", COLOR_PRIORITAT, PRIORITATS)
    seccio(incs, "estat", "Per estat", COLOR_ESTAT, ESTATS)
    seccio(incs, "departament", "Per departament")
    seccio(incs, "categoria", "Per categoria")
    seccio(incs, "sistema_operatiu", "Per sistema operatiu")
    seccio(incs, "ubicacio", "Per ubicació (top 8)", top=8)
    seccio(incs, "equip", "Els 5 equips amb més incidències", top=5)
    seccio(incs, "tecnic", "Per tècnic")

    subtitol("Incidències per mes")
    per_mes = Counter(i["data"][:7] for i in incs)
    barres(per_mes, ordre=sorted(per_mes))

    subtitol("Incidències per dia de la setmana")
    per_dia = Counter(DIES_SETMANA[date.fromisoformat(i["data"]).weekday()] for i in incs)
    barres(per_dia, ordre=DIES_SETMANA)

    subtitol("Temps mitjà de resolució (dies)")
    temps = defaultdict(list)
    for i in incs:
        d = dies_resolucio(i)
        if d is not None:
            temps[i.get("tipus_equip") or "Global"].append(d)
    if temps:
        tots = [d for llista in temps.values() for d in llista]
        print(f"  {'Global':<20} {C.BOLD}{sum(tots) / len(tots):5.1f}{C.RESET} dies "
              f"{C.DIM}({len(tots)} resoltes){C.RESET}")
        if len(temps) > 1:
            for tipus, llista in sorted(temps.items(), key=lambda x: sum(x[1]) / len(x[1])):
                print(f"  {tipus:<20} {C.BOLD}{sum(llista) / len(llista):5.1f}{C.RESET} dies "
                      f"{C.DIM}({len(llista)}){C.RESET}")
    else:
        print(f"  {C.DIM}(cap incidència amb data de resolució){C.RESET}")

    if "prioritat" in incs[0] and "estat" in incs[0]:
        subtitol("Incidències crítiques encara obertes")
        obertes = sorted((i for i in incs if i["prioritat"] == "Crítica"
                          and i["estat"] in ("Oberta", "En curs")), key=lambda i: i["data"])
        if not obertes:
            print(f"  {C.GREEN}Cap. Tot sota control.{C.RESET}")
        for i in obertes[:10]:
            print(f"  {C.RED}{i['id'][:8]:<8}{C.RESET}{i['data']}  "
                  f"{i.get('equip', '')[:22]:<22}  {i.get('ubicacio', '')[:18]:<18}  "
                  f"{COLOR_ESTAT[i['estat']]}{i['estat']}{C.RESET}")
        if len(obertes) > 10:
            print(f"  {C.DIM}... i {len(obertes) - 10} més{C.RESET}")


# ======================================================================
#  6. Desar JSON
# ======================================================================
def escriure_json(dades, fitxer=FITXER_JSON):
    with open(fitxer, "w", encoding="utf-8") as f:
        json.dump(dades, f, ensure_ascii=False, indent=2)


def desar_json(incs):
    titol("DESAR A incidencies.json")
    if not os.path.exists(FITXER_JSON):
        escriure_json(incs)
        print(f"\n  {C.GREEN}Fitxer creat amb {len(incs)} incidències.{C.RESET}")
        return

    print(f"\n  {C.YELLOW}El fitxer {FITXER_JSON} ja existeix.{C.RESET}")
    print("    1) Sobreescriure'l (esborra el contingut anterior)")
    print("    2) Afegir només les incidències noves (sense duplicar IDs)")
    while True:
        opcio = input(f"\n  {C.BOLD}Què vols fer? [1/2]: {C.RESET}").strip()
        if opcio in ("1", "2"):
            break
        print(f"  {C.RED}Opció no vàlida.{C.RESET}")

    if opcio == "1":
        escriure_json(incs)
        print(f"\n  {C.GREEN}Sobreescrit amb {len(incs)} incidències.{C.RESET}")
        return

    try:
        with open(FITXER_JSON, encoding="utf-8") as f:
            existents = json.load(f)
    except (json.JSONDecodeError, OSError):
        print(f"  {C.RED}El JSON existent no es pot llegir; es sobreescriu.{C.RESET}")
        existents = []
    ids = {str(e.get("id")) for e in existents}
    noves = [i for i in incs if i["id"] not in ids]
    escriure_json(existents + noves)
    print(f"\n  {C.GREEN}{len(noves)} incidències noves afegides{C.RESET} "
          f"{C.DIM}({len(incs) - len(noves)} ja existien; total: "
          f"{len(existents) + len(noves)}){C.RESET}")


def desar_revisio(revisio):
    if not revisio:
        return
    escriure_json(revisio, FITXER_REVISIO)
    print(f"\n  {C.YELLOW}{len(revisio)} incidències per revisar guardades a part a "
          f"{C.BOLD}{FITXER_REVISIO}{C.RESET}")


def desar_descartades(descartades, buides):
    files = [(raw, motiu) for raw, motiu in descartades] + [(b, "fila buida") for b in buides]
    if not files:
        return
    files.sort(key=lambda x: x[0].get("_fila", 0))
    escriure_json([{"fila": raw.get("_fila"), "motiu": motiu,
                    "dades": {k: v for k, v in raw.items() if not k.startswith("_")}}
                   for raw, motiu in files], FITXER_DESCARTADES)
    print(f"\n  {C.RED}{len(files)} files descartades (errors + buides) guardades a "
          f"{C.BOLD}{FITXER_DESCARTADES}{C.RESET}")


# ======================================================================
#  Programa principal
# ======================================================================
def main():
    titol("GESTOR D'INCIDÈNCIES")
    ruta = triar_fitxer()
    ext = os.path.splitext(ruta)[1].lower()

    if ext == ".csv":
        pas("1/5", f"Migrant {C.BOLD}{ruta}{C.RESET} → {C.BOLD}{FITXER_XML}{C.RESET}")
        n = csv_a_xml(ruta, FITXER_XML)
        print(f"  {C.GREEN}{n} files convertides.{C.RESET}")
        ruta_xml = FITXER_XML
    elif ext == ".xml":
        pas("1/5", f"Fitxer XML: {C.BOLD}{ruta}{C.RESET}")
        ruta_xml = ruta
    else:
        error("només puc llegir fitxers .csv o .xml")
    mostrar_arbre(ruta_xml)

    pas("2/5", "Llegint l'XML, reparant i netejant les dades")
    registres = llegir_xml(ruta_xml)
    valides, revisio, descartades, buides, correccions, rars, columnes = netejar(registres)
    print(f"  Columnes detectades: {C.DIM}{', '.join(sorted(columnes))}{C.RESET}")
    if "data" not in columnes:
        error("no he trobat cap columna de data (data / fecha / date...)")
    mostrar_correccions(correccions, rars)
    mostrar_descartades(descartades)
    mostrar_revisio(revisio)

    if not valides:
        desar_revisio(revisio)
        desar_descartades(descartades, buides)
        mostrar_buides(buides)
        error("no queda cap incidència vàlida per a les estadístiques")

    pas("3/5", "Estadístiques")
    mostrar_estadistiques(valides)

    pas("4/5", "Guardant resultats")
    desar_json(valides)
    desar_revisio(revisio)
    desar_descartades(descartades, buides)

    pas("5/5", "Resum")
    mostrar_resum(len(registres), valides, revisio, descartades, buides, correccions)
    mostrar_buides(buides)                                   # al final de tot
    print(f"\n{C.GREEN}{C.BOLD}Fet!{C.RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{C.YELLOW}Cancel·lat.{C.RESET}")
