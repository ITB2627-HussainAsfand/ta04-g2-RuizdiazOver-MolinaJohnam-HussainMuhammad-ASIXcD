### ta04-g2-RuizdiazOver-MolinaJohnam-HussainMuhammad-ASIXcD

🚀 Automatització de Google Forms

Eina d'automatització de formularis desenvolupada amb Python. Permet generar respostes de prova utilitzant diferents paràmetres de configuració.

## 📦 1. Instal·lació de dependències

### Primer, clonem el repositori i accedim al directori del projecte:
```
git clone https://github.com/ITB2627-HussainAsfand/ta04-g2-RuizdiazOver-MolinaJohnam-HussainMuhammad-ASIXcD.git

cd ta04-g2-RuizdiazOver-MolinaJohnam-HussainMuhammad-ASIXcD/Python/Automatation\ Forms/ && ls
```

### Creem i activem l'entorn virtual:
```
python3 -m venv .venv
source .venv/bin/activate
```

### Instal·lem les llibreries necessàries i components necessaris de Playwright i Chromium:
```
pip install faker requests beautifulsoup4 playwright

playwright install chromium
```
### ⚙️ 2. Execució del programa

### Un cop tenim totes les dependències instal·lades, podem executar el programa amb la següent comanda:

```
.venv/bin/python forms.py "URL_DEL_FORMULARI" -n 10 -t 3

📝 Paràmetres disponibles
Paràmetre	Descripció
URL	Adreça del formulari de Google Forms
-n	Nombre de respostes de prova (1-∞), normalment google forms no permeteix moltes desde una mateixa
-t	Nivell de variació de les dades generades (1-3)

💡 Exemple d'execució:
.venv/bin/python forms.py "URL_DEL_FORMULARI" -n 10 -t 3
```

## Aquesta comanda configura:

📊 10 respostes de prova.
⚙️ Nivell 3 de variació de les dades.
⚠️ 3. Notes importants
Comprova que l'entorn virtual estigui activat abans d'executar el projecte.
Assegura't que Chromium estigui instal·lat correctament.
Utilitza únicament formularis propis o entorns de proves amb autorització.
Evita enviar respostes automatitzades a formularis de tercers sense permís.
👨‍💻 Desenvolupat amb
🐍 Python
🎭 Playwright
🎲 Faker
🌐 Requests
🍜 BeautifulSoup4

# ⭐ Projecte desenvolupat amb finalitats educatives. ITB 26/27 MDS
