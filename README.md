### ta04-g2-RuizdiazOver-MolinaJohnam-HussainMuhammad-ASIXcD

🚀 Automatització de Google Forms i Gestió d'Incidències

Eina d'automatització i gestió de dades desenvolupada amb Python. El projecte inclou dos programes principals: un sistema per generar respostes de prova a Google Forms i un gestor d'incidències que permet importar, netejar, reparar i classificar dades procedents de fitxers CSV i XML.

## 📦 1. Instal·lació de dependències

### Primer, clonem el repositori i accedim al directori del projecte:

```
git clone https://github.com/ITB2627-HussainAsfand/ta04-g2-RuizdiazOver-MolinaJohnam-HussainMuhammad-ASIXcD.git

cd ta04-g2-RuizdiazOver-MolinaJohnam-HussainMuhammad-ASIXcD/
```

### Creem i activem l'entorn virtual:

```
python3 -m venv .venv
source .venv/bin/activate
```

### Instal·lem les llibreries necessàries per a l'automatització de Google Forms i els components de Playwright i Chromium:

```
pip install faker requests beautifulsoup4 playwright

playwright install chromium
```

### Per al Gestor d'Incidències:

No és necessari instal·lar cap llibreria externa, ja que utilitza les llibreries estàndard de Python 3.

## ⚙️ 2. Execució dels programes

### 📝 Automatització de Google Forms

Un cop tenim totes les dependències instal·lades, accedim al directori del projecte:

```
cd "Python/Automatation Forms/"
```

Executem el programa amb la següent comanda:

```
.venv/bin/python forms.py "URL_DEL_FORMULARI" -n 10 -t 3
```

📝 **Paràmetres disponibles**

| Paràmetre | Descripció |
|---|---|
| URL | Adreça del formulari de Google Forms |
| -n | Nombre de respostes de prova (1-∞) |
| -t | Nivell de variació de les dades generades (1-3) |

💡 **Exemple d'execució:**

```
.venv/bin/python forms.py "URL_DEL_FORMULARI" -n 10 -t 3
```

### Aquesta comanda configura:

📊 10 respostes de prova.

⚙️ Nivell 3 de variació de les dades.

---

### 🖥️ Gestor d'Incidències

Accedim al directori del gestor:

```
cd Python/ScriptGestion/
```

Executem el programa sense especificar cap fitxer:

```
python3 gestor_incidencies.py
```

El programa permet seleccionar interactivament el fitxer CSV o XML que volem processar.

També podem indicar directament el fitxer d'entrada:

```
python3 gestor_incidencies.py incidencies.csv
```

O bé un fitxer XML:

```
python3 gestor_incidencies.py incidencies.xml
```

### 🔄 Funcionament del Gestor d'Incidències

**1. Importació i migració de dades**

📄 Llegeix fitxers CSV amb diferents separadors i codificacions.

🌳 Permet llegir fitxers XML directament.

🔄 Converteix automàticament els fitxers CSV a XML (`incidencies.xml`).

**2. Generació del diagrama XML**

🌳 Dibuixa l'estructura de l'arbre XML a la terminal.

📊 Genera un diagrama visual en format SVG (`arbre_xml.svg`).

**3. Neteja i reparació de dades**

🧹 Detecta i separa les files buides.

🔓 Descodifica continguts en binari, hexadecimal i Base64 quan és possible.

🔧 Repara text corrupte, caràcters mal codificats, entitats HTML i codificacions URL.

❌ Detecta textos sense sentit o il·legibles i buida o descarta els registres afectats.

✏️ Normalitza noms, aules, tipus d'equip i altres camps mal escrits.

📅 Interpreta diferents formats de dates.

⚙️ Unifica prioritats i estats mitjançant sinònims i correcció d'errors ortogràfics.

**4. Estadístiques i resultats**

📊 Mostra estadístiques de les incidències processades a la terminal.

🎨 Utilitza colors per diferenciar informació, correccions i errors.

📈 Mostra informació agrupada per tipus d'equip, prioritat, estat, departament, categoria, sistema operatiu i tècnic.

⏱️ Calcula temps mitjans de resolució i identifica incidències crítiques pendents.

**5. Emmagatzematge de dades**

El programa genera els següents fitxers:

| Fitxer | Descripció |
|---|---|
| `incidencies.xml` | Fitxer XML generat a partir del CSV original. |
| `arbre_xml.svg` | Diagrama visual de l'estructura XML. |
| `incidencies.json` | Incidències netes i normalitzades. |
| `incidencies_revisio.json` | Incidències amb dates futures o de fa més de 5 anys. |
| `incidencies_descartades.json` | Registres amb errors i files buides. |

## ⚠️ 3. Notes importants

### Automatització de Google Forms

- Comprova que l'entorn virtual estigui activat abans d'executar el projecte.
- Assegura't que Chromium estigui instal·lat correctament.
- Utilitza únicament formularis propis o entorns de proves amb autorització.
- Evita enviar respostes automatitzades a formularis de tercers sense permís.

### Gestor d'Incidències

- És necessari disposar de Python 3.
- Els fitxers d'entrada han de tenir format CSV o XML.
- Els fitxers CSV han de contenir una capçalera amb els noms de les columnes.
- El programa intenta detectar automàticament els separadors i les codificacions.
- Les incidències amb errors crítics poden ser descartades.
- Les incidències amb dates futures o anteriors a cinc anys es guarden separadament per revisar-les.
- Si ja existeix `incidencies.json`, es pot escollir entre sobreescriure les dades o afegir-hi noves incidències evitant duplicats.

## ⚙️ Desenvolupat amb

### Automatització de Google Forms

⚙️ Python

⚙️ Playwright

⚙️ Faker

⚙️ Requests

⚙️ BeautifulSoup4

### Gestor d'Incidències

⚙️ Python 3

⚙️ CSV

⚙️ XML (ElementTree)

⚙️ JSON

⚙️ SVG

⚙️ Regex (expressions regulars)

⚙️ Base64

⚙️ Datetime

# ⭐ Projecte desenvolupat amb finalitats educatives. ITB 26/27 MDS
