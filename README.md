## Creat per ***Over, Johnam, Asfand***

🚀 Automatització de Google Forms

Eina d'automatització de formularis desenvolupada amb Python. Permet generar respostes de prova utilitzant diferents paràmetres de configuració.

# 📦 1. Instal·lació de dependències

### Primer, clonem el repositori i accedim al directori del projecte:
```
git clone https://github.com/ITB2627-HussainAsfand/ta04-g2-RuizdiazOver-MolinaJohnam-HussainMuhammad-ASIXcD.git
```
```

cd ta04-g2-RuizdiazOver-MolinaJohnam-HussainMuhammad-ASIXcD/Python/Automatation\ Forms/ && ls
```

### Creem i activem l'entorn virtual:
```
python3 -m venv .venv
```
```
source .venv/bin/activate
```

### Instal·lem les llibreries necessàries i components necessaris de Playwright i Chromium:
```
pip install faker requests beautifulsoup4 playwright
```
```
playwright install chromium
```
# ⚙️ 2. Execució del programa

### Un cop tenim totes les dependències instal·lades, podem executar el programa amb la següent comanda:

```
.venv/bin/python forms.py "URL_DEL_FORMULARI" -n 10 -t 3
```
### No fa falta executar aixo:
```
📝 Paràmetres disponibles
Paràmetre	Descripció
URL	Adreça del formulari de Google Forms
-n	Nombre de respostes de prova (1-∞), normalment google forms no permeteix moltes desde una mateixa
-t	Nivell de variació de les dades generades (1-3)

💡 Exemple d'execució:
.venv/bin/python forms.py "URL_DEL_FORMULARI" -n 10 -t 3
```

# Aquesta comanda configura:

📊 10 respostes de prova.

⚙️ Nivell 3 de variació de les dades.

⚠️ 3. Notes importants
Comprova que l'entorn virtual estigui activat abans d'executar el projecte.
Assegura't que Chromium estigui instal·lat correctament.
Utilitza únicament formularis propis o entorns de proves amb autorització.
Evita enviar respostes automatitzades a formularis de tercers sense permís.
⚙️ Desenvolupat amb

⚙️ Python

⚙️ Playwright

⚙️ Faker

⚙️ Requests

⚙️ BeautifulSoup4

---

# 🖥️ Gestor d'Incidències

Eina de gestió, migració i neteja de dades d'incidències desenvolupada amb Python. Permet llegir fitxers CSV i XML, detectar i reparar dades incorrectes, normalitzar informació i generar estadístiques sobre les incidències processades.

# 📦 4. Instal·lació

### Accedim al directori del projecte:
```
cd ../ScriptGestion/
```

### No és necessari instal·lar cap llibreria externa, ja que el programa utilitza les llibreries estàndard de Python 3.

# ⚙️ 5. Execució del programa

### Podem executar el programa sense indicar cap fitxer:
```
python3 gestor_incidencies.py
```

El programa permet seleccionar interactivament el fitxer CSV o XML que volem processar, posant la ruta directa o si esta en la mateixa carpeta...

### També podem indicar directament el fitxer d'entrada:
```
python3 gestor_incidencies.py incidencies.csv
```

O bé un fitxer XML:
```
python3 gestor_incidencies.py incidencies.xml
```

# 🔄 6. Funcionament del programa

### 📥 Importació i migració de dades

- Llegeix fitxers CSV amb diferents separadors i codificacions.
- Permet llegir fitxers XML directament.
- Converteix automàticament els fitxers CSV a XML (`incidencies.xml`).
- Normalitza els noms de les columnes.

### 🌳 Generació del diagrama XML

- Dibuixa l'estructura de l'arbre XML a la terminal.
- Genera un diagrama visual en format SVG (`arbre_xml.svg`).

### 🧹 Neteja i reparació de dades

- **Files buides:** les separa i les guarda per consultar-les posteriorment.
- **Text codificat:** descodifica continguts en binari, hexadecimal i Base64 quan és possible.
- **Text corrupte:** repara caràcters mal codificats, entitats HTML, codificacions URL i caràcters de control.
- **Text il·legible:** detecta continguts sense sentit i buida o descarta els registres afectats.
- **Noms mal escrits:** normalitza noms, aules, tipus d'equip i altres camps.
- **Prioritats i estats:** unifica sinònims, traduccions i faltes d'ortografia.
- **Dates:** interpreta diferents formats de data i hora.

### 📊 Estadístiques i resultats

- Mostra les correccions realitzades i els errors detectats.
- Genera estadístiques de les incidències processades a la terminal.
- Utilitza colors per diferenciar informació, correccions i errors.
- Mostra informació agrupada per tipus d'equip, prioritat, estat, departament, categoria, sistema operatiu i tècnic.
- Calcula temps mitjans de resolució.
- Identifica incidències crítiques pendents de resoldre.

### 💾 Emmagatzematge de dades

El programa genera els següents fitxers:

| Fitxer | Descripció |
|---|---|
| `incidencies.xml` | Fitxer XML generat a partir del CSV original. |
| `arbre_xml.svg` | Diagrama visual de l'estructura XML. |
| `incidencies.json` | Incidències netes i normalitzades. |
| `incidencies_revisio.json` | Incidències amb dates futures o de fa més de 5 anys. |
| `incidencies_descartades.json` | Registres amb errors i files buides. |

## ⚠️ 7. Notes importants

- És necessari disposar de Python 3.
- Els fitxers d'entrada han de tenir format CSV o XML.
- Els fitxers CSV han de contenir una capçalera amb els noms de les columnes.
- El programa intenta detectar automàticament els separadors i les codificacions.
- Les incidències amb errors crítics poden ser descartades.
- Les incidències amb dates futures o anteriors a cinc anys es guarden separadament per revisar-les.
- Si ja existeix `incidencies.json`, es pot escollir entre sobreescriure les dades o afegir-hi noves incidències evitant duplicats.

## ⚙️ Desenvolupat amb

⚙️ Python 3

⚙️ CSV

⚙️ XML (ElementTree)

⚙️ JSON

⚙️ SVG

⚙️ Regex (expressions regulars)

⚙️ Base64

⚙️ Datetime

## Star History

<a href="https://freesvg.org/img/Troll-Face.png">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=itb2627-hussainasfand/ta04-g2-ruizdiazover-molinajohnam-hussainmuhammad-asixcd&type=date&theme=dark&legend=bottom-right" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=itb2627-hussainasfand/ta04-g2-ruizdiazover-molinajohnam-hussainmuhammad-asixcd&type=date&legend=bottom-right" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=itb2627-hussainasfand/ta04-g2-ruizdiazover-molinajohnam-hussainmuhammad-asixcd&type=date&legend=bottom-right" />
 </picture>
</a>

# ⭐ Projecte desenvolupat amb finalitats educatives. ITB 26/27 MDS
