from flask import Flask, request, jsonify
import requests
import datetime
import os

app = Flask(__name__)

@app.route('/assistant', methods=['POST'])
def assistant():
    data = request.json or {}
    query = data.get('query', '').lower()
    
    classe = data.get('classe', '').strip().upper()
    scuola = data.get('scuola', '').strip().upper()
    user = data.get('user', '').strip()
    passwd = data.get('pass', '').strip()
    
    compiti_list = []
    debug_info = ""
    
    if any(k in query for k in ["compiti", "didup", "programmazione", "esercizi"]):
        if not scuola or not user or not passwd:
            reply = "Credenziali didUP non trovate. Inserisci Scuola, Utente e Password nel menu Impostazioni dell'app."
            return jsonify({'reply': reply, 'compiti': []})
            
        try:
            session = requests.Session()
            
            # Intestazioni specifiche emulate dall'app mobile DidUp
            headers = {
                'Content-Type': 'application/json',
                'X-Codice-Scuola': scuola,
                'User-Agent': 'DidUp/Family Android',
                'Accept': 'application/json, text/plain, */*',
                'X-App-Id': 'it.argo.didup'
            }
            
            # Endpoint mobile ufficiale di Argo per i token di accesso
            login_url = "https://www.portaleargo.it/auth/sso/api/login"
            
            login_res = session.post(
                login_url,
                headers=headers,
                json={
                    "codiceScuola": scuola,
                    "username": user,
                    "password": passwd,
                },
                timeout=15
            )
            
            if login_res.status_code == 200:
                login_data = login_res.json() if login_res.content else {}
                token = (
                    login_data.get('token') or 
                    login_data.get('tokenAuth') or 
                    login_data.get('accessToken') or 
                    login_data.get('tokenKey') or ''
                )
                
                auth_headers = {
                    'X-Codice-Scuola': scuola,
                    'Accept': 'application/json, text/plain, */*',
                    'User-Agent': 'DidUp/Family Android',
                }
                if token:
                    auth_headers['X-Auth-Token'] = token
                    auth_headers['Authorization'] = f'Bearer {token}'
                    
                now = datetime.date.today()
                past = now - datetime.timedelta(days=5)
                future = now + datetime.timedelta(days=15)
                
                compiti_res = session.get(
                    f"https://www.portaleargo.it/famiglia/api/rest/v2/compiti-assegnati?da={past.isoformat()}&a={future.isoformat()}",
                    headers=auth_headers,
                    timeout=15
                )
                
                if compiti_res.status_code == 200:
                    decoded = compiti_res.json()
                    items = []
                    if isinstance(decoded, dict):
                        items = decoded.get('dati', []) or decoded.get('compiti', []) or decoded.get('compitiAssegnati', [])
                    elif isinstance(decoded, list):
                        items = decoded
                        
                    for item in items:
                        compiti_list.append({
                            'data': item.get('datGiorno') or item.get('datCompito') or '',
                            'materia': item.get('desMateria') or item.get('materia') or 'Materia',
                            'descrizione': item.get('desCompito') or item.get('compito') or 'Compito',
                        })
                else:
                    debug_info = f"Errore recupero compiti (HTTP {compiti_res.status_code})"
            else:
                debug_info = f"Login mobile rifiutato (HTTP {login_res.status_code})"
                
        except Exception as e:
            debug_info = f"Errore: {str(e)}"

    if "compiti" in query or "didup" in query:
        if compiti_list:
            testo_compiti = ", ".join([f"{c['materia']}: {c['descrizione']}" for c in compiti_list[:3]])
            reply = f"Ho trovato {len(compiti_list)} compiti su didUP. Tra cui: {testo_compiti}"
        else:
            # Fallback temporaneo se il login mobile viene bloccato dal sistema SSO
            reply = f"Impossibile connettersi ad Argo ({debug_info}). Verifica le credenziali."
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
