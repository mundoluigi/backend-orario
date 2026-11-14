import os
import re
import glob
from io import BytesIO
import datetime
import pandas as pd
import pdfplumber
from flask import Flask, render_template_string, request, send_file, jsonify
from werkzeug.utils import secure_filename
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font

app = Flask(__name__)

# Forza l'abilitazione dei CORS su tutte le risposte
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

HTML_TEMPLATE = """
<!doctype html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Generatore Orario Scolastico</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 90vh; }
        .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
        h2 { color: #333; text-align: center; margin-bottom: 25px; }
        label { font-weight: bold; display: block; margin-top: 15px; color: #555; }
        input[type="file"], input[type="text"] { width: 100%; padding: 12px; margin-top: 5px; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
        button { background-color: #4CAF50; color: white; border: none; padding: 14px; width: 100%; margin-top: 25px; border-radius: 5px; font-size: 16px; cursor: pointer; font-weight: bold; }
        button:hover { background-color: #45a049; }
        .error { color: #d9534f; background: #f2dede; padding: 12px; border-radius: 5px; margin-bottom: 15px; text-align: center; font-size: 14px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Generatore Orario</h2>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST" enctype="multipart/form-data">
            <label for="file">File PDF Orario Docenti:</label>
            <input type="file" name="file" accept=".pdf" required>

            <label for="classe">Classe (es. 3C, 4A):</label>
            <input type="text" name="classe" required placeholder="Es. 3C">

            <button type="submit">Genera e Scarica Excel</button>
        </form>
    </div>
</body>
</html>
"""

GIORNI = {
    0: "LUNEDI",
    1: "MARTEDI",
    2: "MERCOLEDI",
    3: "GIOVEDI",
    4: "VENERDI",
    5: "SABATO",
    6: "DOMENICA"
}

@app.route('/assistant', methods=['POST', 'OPTIONS'])
def voice_assistant():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json(silent=True) or {}
    query = data.get('query', '').lower().strip()

    if not query:
        return jsonify({'reply': 'Non ho ricevuto alcun comando vocale.'})

    if "ciao orario studenti" in query or "ciao orario" in query:
        return jsonify({'reply': 'Ciao! Come posso aiutarti oggi con gli orari?'})

    oggi = datetime.datetime.now()
    target_day = None

    if "oggi" in query:
        target_day = GIORNI[oggi.weekday()]
    elif "domani" in query:
        domani = oggi + datetime.timedelta(days=1)
        target_day = GIORNI[domani.weekday()]
    else:
        mapping_parole = {
            "lunedì": "LUNEDI", "lunedi": "LUNEDI",
            "martedì": "MARTEDI", "martedi": "MARTEDI",
            "mercoledì": "MERCOLEDI", "mercoledi": "MERCOLEDI",
            "giovedì": "GIOVEDI", "giovedi": "GIOVEDI",
            "venerdì": "VENERDI", "venerdi": "VENERDI",
            "sabato": "SABATO", "domenica": "DOMENICA"
        }
        for parola, giorno_it in mapping_parole.items():
            if parola in query:
                target_day = giorno_it
                break

    if not target_day:
        domani = oggi + datetime.timedelta(days=1)
        target_day = GIORNI[domani.weekday()]

    if "orario" in query or "materia" in query or "lezioni" in query or "seconda" in query or "prima" in query or "terza" in query or "quarta" in query or "quinta" in query or "sesta" in query or "settima" in query:
        if target_day in ["SABATO", "DOMENICA"]:
            return jsonify({'reply': f"Il {target_day.lower()} non ci sono lezioni scolastiche!"})

        try:
            excel_files = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], "*.xlsx"))
            if not excel_files:
                excel_files = glob.glob(os.path.join(BASE_DIR, "*.xlsx"))

            if not excel_files:
                return jsonify({'reply': "Non ho trovato nessun file Excel recente sul server. Generane uno prima dall'app."})

            latest_file = max(excel_files, key=os.path.getctime)
            df = pd.read_excel(latest_file, index_col=0)

            orario_giorno = None
            for idx in df.index:
                idx_clean = str(idx).upper().replace('Ì', 'I').replace('È', 'E').replace('É', 'E').replace('Ò', 'O').replace('À', 'A').replace('Ù', 'U')
                if target_day in idx_clean:
                    orario_giorno = df.loc[idx]
                    break

            if orario_giorno is not None:
                ore_mappa = {
                    "1^ Ora": "prima ora",
                    "2^ Ora": "seconda ora",
                    "3^ Ora": "terza ora",
                    "4^ Ora": "quarta ora",
                    "5^ Ora": "quinta ora",
                    "6^ Ora": "sesta ora",
                    "7^ Ora": "settima ora"
                }

                correzioni_nomi = {
                    "LAGANA'": "Laganà", "LAGANA": "Laganà", "MANGLAVITI": "Manglaviti",
                    "ANTROPOLI": "Antropoli", "CORSETTI": "Corsetti", "FLAMINI": "Flamini",
                    "RIPANI": "Ripani", "SCARPA": "Scarpa", "PRANZETTI": "Pranzetti",
                    "RINALDI": "Rinaldi", "CIANTI": "Cianti", "MAROTTA": "Marotta",
                    "MANNA": "Manna", "MELI": "Meli", "FERRUCCI": "Ferrucci"
                }

                giorni_vocal_map = {
                    "LUNEDI": "lunedì", "MARTEDI": "martedì", "MERCOLEDI": "mercoledì",
                    "GIOVEDI": "giovedì", "VENERDI": "venerdì", "SABATO": "sabato", "DOMENICA": "domenica"
                }
                giorno_parlato = giorni_vocal_map.get(target_day, target_day.lower())

                ora_richiesta_chiave = None
                if "prima" in query or "1" in query: ora_richiesta_chiave = "1^ Ora"
                elif "seconda" in query or "2" in query: ora_richiesta_chiave = "2^ Ora"
                elif "terza" in query or "3" in query: ora_richiesta_chiave = "3^ Ora"
                elif "quarta" in query or "4" in query: ora_richiesta_chiave = "4^ Ora"
                elif "quinta" in query or "5" in query: ora_richiesta_chiave = "5^ Ora"
                elif "sesta" in query or "6" in query: ora_richiesta_chiave = "6^ Ora"
                elif "settima" in query or "7" in query: ora_richiesta_chiave = "7^ Ora"

                if ora_richiesta_chiave and ora_richiesta_chiave in orario_giorno:
                    materia = orario_giorno[ora_richiesta_chiave]
                    if pd.notna(materia) and str(materia).strip() != "":
                        materia_pulita = str(materia).replace('\n', ' con ')
                        materia_pulita = materia_pulita.replace("INFORMATIC A", "Informatica").replace("MATEMATIC A", "Matematica")
                        for err, cor in correzioni_nomi.items():
                            materia_pulita = materia_pulita.replace(err, cor).replace(err.lower(), cor)
                        
                        nome_ora_parlata = ore_mappa.get(ora_richiesta_chiave, ora_richiesta_chiave)
                        reply = f"Per la {nome_ora_parlata} di {giorno_parlato} c'è: {materia_pulita}."
                    else:
                        reply = f"Per la {ore_mappa.get(ora_richiesta_chiave, ora_richiesta_chiave)} di {giorno_parlato} non risultano lezioni."
                else:
                    frasi_ore = []
                    for ora, materia in orario_giorno.items():
                        if pd.notna(materia) and str(materia).strip() != "":
                            materia_pulita = str(materia).replace('\n', ' con ')
                            materia_pulita = materia_pulita.replace("INFORMATIC A", "Informatica").replace("MATEMATIC A", "Matematica")
                            for err, cor in correzioni_nomi.items():
                                materia_pulita = materia_pulita.replace(err, cor).replace(err.lower(), cor)
                            
                            nome_ora = ore_mappa.get(ora, ora)
                            frasi_ore.append(f"Per la {nome_ora}: {materia_pulita}")

                    if frasi_ore:
                        testo_orario = ". ".join(frasi_ore) + "."
                        reply = f"L'orario di {giorno_parlato} è questo. {testo_orario}"
                    else:
                        reply = f"Per il giorno {giorno_parlato} non risultano lezioni registrate."
            else:
                reply = f"Non ho trovato i dati per {giorno_parlato} nell'ultimo file Excel."

        except Exception as e:
            reply = f"Errore durante la lettura dell'Excel: {str(e)}"

        return jsonify({'reply': reply})

    return jsonify({
        'reply': f"Ho capito '{query}'. Puoi chiedermi l'orario di un giorno specifico!"
    })


@app.route('/', methods=['GET', 'POST', 'OPTIONS'])
def index():
    if request.method == 'OPTIONS':
        return '', 200

    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template_string(HTML_TEMPLATE, error="Nessun file selezionato")

        file = request.files['file']
        classe_target = request.form.get('classe', '').strip().upper()

        if file.filename == '':
            return render_template_string(HTML_TEMPLATE, error="Seleziona un file PDF valido")

        if file and classe_target:
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(pdf_path)

            try:
                all_rows = []
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        table = page.extract_table()
                        if table:
                            all_rows.extend(table)
                        else:
                            extracted = page.extract_tables()
                            for t in extracted:
                                all_rows.extend(t)

                if not all_rows:
                    return render_template_string(HTML_TEMPLATE, error="Impossibile estrarre tabelle dal PDF.")

                df = pd.DataFrame(all_rows)

                giorni_cols = {
                    "LUNEDI": [2, 3, 4, 5, 6, 7, 8],
                    "MARTEDI": [10, 11, 12, 13, 14, 15, 16],
                    "MERCOLEDI": [18, 19, 20, 21, 22, 23, 24],
                    "GIOVEDI": [26, 27, 28, 29, 30, 31, 32],
                    "VENERDI": [34, 35, 36, 37, 38, 39, 40, 41]
                }
                ore_nomi = ["1^ Ora", "2^ Ora", "3^ Ora", "4^ Ora", "5^ Ora", "6^ Ora", "7^ Ora"]

                tabella_orario = {giorno: {ora: [] for ora in ore_nomi} for giorno in giorni_cols}
                current_materia = ""
                current_cognome = ""

                for r in range(0, len(df)):
                    disc_val = df.iat[r, 0] if df.shape[1] > 0 else None
                    doc_val = df.iat[r, 1] if df.shape[1] > 1 else None

                    if pd.notna(disc_val) and str(disc_val).strip() != "" and str(disc_val).strip().upper() != "DISCIPLINA":
                        current_materia = str(disc_val).replace('\n', ' ').strip()

                    if pd.notna(doc_val) and str(doc_val).strip() != "":
                        doc_str = str(doc_val).strip()
                        primo_pezzo = doc_str.split('\n')[0].strip()
                        current_cognome = primo_pezzo.split()[0] if primo_pezzo else ""

                    if "SOSTEGNO" in current_materia.upper():
                        continue

                    for giorno, cols in giorni_cols.items():
                        for idx, col in enumerate(cols):
                            if idx < len(ore_nomi) and col < df.shape[1]:
                                valore_cella = df.iat[r, col]
                                if pd.notna(valore_cella):
                                    cella_val = str(valore_cella).strip().upper()
                                    if classe_target in cella_val or re.search(r'\b' + re.escape(classe_target) + r'\b', cella_val):
                                        ora_nome = ore_nomi[idx]
                                        if current_materia:
                                            voce_completa = f"{current_materia}\n({current_cognome})" if current_cognome else current_materia
                                            if voce_completa not in tabella_orario[giorno][ora_nome]:
                                                tabella_orario[giorno][ora_nome].append(voce_completa)

                tabella_pulita = {}
                for giorno, ore_dict in tabella_orario.items():
                    tabella_pulita[giorno] = {}
                    for ora, lista_voci in ore_dict.items():
                        tabella_pulita[giorno][ora] = " / ".join(lista_voci) if lista_voci else ""

                df_finale = pd.DataFrame.from_dict(tabella_pulita, orient='index')
                df_finale.index.name = "Giorni / Ore"

                nome_file = f"Orario_Classe_{classe_target}.xlsx"
                excel_save_path = os.path.join(app.config['UPLOAD_FOLDER'], nome_file)

                df_finale.to_excel(excel_save_path, sheet_name=f'Classe {classe_target}')

                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_finale.to_excel(writer, sheet_name=f'Classe {classe_target}')
                    worksheet = writer.sheets[f'Classe {classe_target}']

                    for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row, min_col=2, max_col=worksheet.max_column):
                        for cell in row:
                            cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")

                    for col in range(1, worksheet.max_column + 1):
                        cell = worksheet.cell(row=1, column=col)
                        cell.font = Font(bold=True)
                        cell.alignment = Alignment(horizontal="center", vertical="center")

                    for row in range(1, worksheet.max_row + 1):
                        cell = worksheet.cell(row=row, column=1)
                        cell.font = Font(bold=True)
                        cell.alignment = Alignment(horizontal="center", vertical="center")

                    for col in worksheet.columns:
                        max_len = 0
                        col_letter = get_column_letter(col[0].column)
                        for cell in col:
                            if cell.value:
                                lines = str(cell.value).split('\n')
                                longest_line = max(lines, key=len)
                                max_len = max(max_len, len(longest_line))
                        worksheet.column_dimensions[col_letter].width = max(max_len + 5, 22)

                output.seek(0)
                return send_file(
                    output,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name=nome_file
                )

            except Exception as e:
                return render_template_string(HTML_TEMPLATE, error=f"Errore: {str(e)}")

    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
