from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

@app.route('/assistant', methods=['POST'])
def assistant():
    data = request.json or {}
    query = data.get('query', '').lower()
    
    classe = data.get('classe', '').strip().upper()
    scuola = data.get('scuola', '').strip().upper()
    user = data.get('user', '').strip()
    pwd = data.get('pass', '').strip()
    token = data.get('token', '').strip()
    
    compiti_list = []
    debug_info = ""
    
    if any(k in query for k in ["compiti", "didup", "programmazione", "esercizi"]):
        try:
            session = requests.Session()
            
            # Se l'utente ha inserito un token manuale lo usiamo, altrimenti proviamo l'autenticazione via credenziali
            active_token = token
            if not active_token and user and pwd:
                # Tentativo di login automatico alle API di Argo
                login_res = session.post(
                    "https://didattica.portaleargo.it/grest/login",
                    json={"uid": user, "pwd": pwd, "scuola": scuola},
                    headers={"X-Codice-Scuola": scuola, "Content-Type": "application/json"}
                )
                if login_res.status_code == 200:
                    login_data = login_res.json()
                    active_token = login_data.get('token') or login_data.get('accessToken')
            
            if not active_token:
                reply = "Sessione Argo non valida o credenziali mancanti. Verifica i dati nelle impostazioni."
                return jsonify({'reply': reply, 'compiti': []})

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
                'Authorization': active_token if active_token.startswith('Bearer ') else f'Bearer {active_token}',
                'X-Auth-Token': active_token.replace('Bearer ', '').strip(),
                'X-Codice-Scuola': scuola,
                'Argo-Client-Version': '4.2.3',
                'Origin': 'https://www.portaleargo.it',
                'Referer': 'https://www.portaleargo.it/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
            
            dashboard_url = "https://didattica.portaleargo.it/famiglia/api/dashboard/dashboard"
            
            res = session.get(
                dashboard_url,
                headers=headers,
                timeout=15
            )
            
            if res.status_code == 200:
                decoded = res.json()
                items = []
                if isinstance(decoded, dict):
                    items = (
                        decoded.get('compitiAssegnati', []) or 
                        decoded.get('compiti', []) or 
                        decoded.get('dati', {}).get('compitiAssegnati', []) or
                        decoded.get('agenda', [])
                    )
                elif isinstance(decoded, list):
                    items = decoded
                    
                for item in items:
                    compiti_list.append({
                        'data': item.get('datGiorno') or item.get('datCompito') or item.get('data') or '',
                        'materia': item.get('desMateria') or item.get('materia') or 'Materia',
                        'descrizione': item.get('desCompito') or item.get('compito') or item.get('descrizione') or 'Compito',
                    })
            else:
                debug_info = f"HTTP {res.status_code}"
                
        except Exception as e:
            debug_info = f"Eccezione: {str(e)}"

    if "compiti" in query or "didup" in query:
        if compiti_list:
            testo_compiti = ", ".join([f"{c['materia']}: {c['descrizione']}" for c in compiti_list[:3]])
            reply = f"Ho trovato {len(compiti_list)} compiti su didUP. Tra cui: {testo_compiti}"
        else:
            reply = f"Nessun compito trovato. Errore API Argo ({debug_info})"
    else:
        info_classe = f" per la classe {classe}" if classe else ""
        reply = f"Comando ricevuto{info_classe}: {query}"

    return jsonify({
        'reply': reply,
        'compiti': compiti_list
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
