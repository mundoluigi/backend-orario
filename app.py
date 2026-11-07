from flask import Flask, request, jsonify, send_file
import os
import requests
import pandas as pd
import io

app = Flask(__name__)

@app.route('/', methods=['POST'])
def genera_orario():
    try:
        classe = request.form.get('classe', '').strip().upper()
        file = request.files.get('file')
        
        if not file or not classe:
            return jsonify({'error': 'File o classe mancanti'}), 400
            
        # Legge il PDF o elabora il file ricevuto
        # (Qui inserisci la logica di parsing del tuo generatore Excel esistente)
        
        # Esempio di generazione file Excel di risposta
        df = pd.DataFrame({
            'Classe': [classe],
            'Stato': ['Orario generato con successo via Render']
        })
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=f'Orario {classe}')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'Orario_Classe_{classe}.xlsx'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/assistant', methods=['POST'])
def assistant():
    data = request.json or {}
    query = data.get('query', '').lower()
    scuola = data.get('scuola', '').strip().upper()
    token = data.get('token', '').strip()
    
    compiti_list = []
    debug_info = ""
    
    if any(k in query for k in ["compiti", "didup", "programmazione", "esercizi"]):
        if not token:
            return jsonify({'reply': "Token di sessione DidUP mancante. Esegui il login nelle impostazioni.", 'compiti': []})
            
        try:
            session = requests.Session()
            clean_token = token.replace('Bearer', '').replace('bearer', '').strip()
            
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Authorization': f'Bearer {clean_token}',
                'x-auth-token': clean_token,
                'x-cod-min': scuola if scuola else 'SG18119',
                'os-type': 'WEB',
                'argo-client-version': '4.2.3',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            }
            
            res = session.get("https://didattica.portaleargo.it/famiglia/api/dashboard/dashboard", headers=headers, timeout=15)
            if res.status_code == 200:
                decoded = res.json()
                items = decoded.get('compitiAssegnati', []) or decoded.get('agenda', [])
                for item in items:
                    compiti_list.append({
                        'materia': item.get('desMateria', 'Materia'),
                        'descrizione': item.get('desCompito', 'Compito'),
                    })
            else:
                debug_info = f"HTTP {res.status_code}"
        except Exception as e:
            debug_info = str(e)

    if compiti_list:
        reply = f"Ho trovato {len(compiti_list)} compiti su didUP."
    else:
        reply = f"Nessun compito trovato o errore Argo ({debug_info})."

    return jsonify({'reply': reply, 'compiti': compiti_list})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
